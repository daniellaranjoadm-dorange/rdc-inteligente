"""Painel de HH: horas-homem trabalhadas e perdidas por bloco, disciplina, navio e etapa."""
from collections import OrderedDict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum

from core.choices import EtapaConstrucaoNavalChoices, TipoAreaNavalChoices
from rdc.models import RDC, RDCFuncionario, RDCParalisacao

ZERO = Decimal("0.00")
MAX_DIAS = 366
_ETAPAS = dict(EtapaConstrucaoNavalChoices.CHOICES)
_TIPOS = dict(TipoAreaNavalChoices.CHOICES)

# Cada agrupamento: campos do RDC usados como chave e como montar o rotulo.
AGRUPAMENTOS = {
    "area": {
        "campos": ("rdc__area_local_id", "rdc__area_local__descricao", "rdc__area_local__tipo", "rdc__projeto__codigo"),
        "rotulo": lambda r: r["rdc__area_local__descricao"] or "Sem área",
        "detalhe": lambda r: " · ".join(
            p for p in (r["rdc__projeto__codigo"], _TIPOS.get(r["rdc__area_local__tipo"] or "", "")) if p
        ),
    },
    "disciplina": {
        "campos": ("rdc__disciplina__nome",),
        "rotulo": lambda r: r["rdc__disciplina__nome"] or "Sem disciplina",
        "detalhe": lambda r: "",
    },
    "casco": {
        "campos": ("rdc__area_local__casco",),
        "rotulo": lambda r: r["rdc__area_local__casco"] or "Casco não informado",
        "detalhe": lambda r: "",
    },
    "etapa": {
        "campos": ("rdc__area_local__etapa",),
        "rotulo": lambda r: _ETAPAS.get(r["rdc__area_local__etapa"] or "", "Etapa não informada"),
        "detalhe": lambda r: "",
    },
}


def _dec(valor):
    return Decimal(valor or 0).quantize(Decimal("0.01"))


def _percentual(perdido, trabalhado):
    disponivel = trabalhado + perdido
    if trabalhado <= 0 or disponivel <= 0:
        return None
    return (perdido / disponivel * 100).quantize(Decimal("0.1"))


def periodo_padrao(hoje=None):
    """Semana atual (segunda ate hoje)."""
    hoje = hoje or date.today()
    return hoje - timedelta(days=hoje.weekday()), hoje


def normalizar_periodo(inicio, fim, hoje=None):
    """Garante inicio <= fim e no maximo MAX_DIAS dias, para a consulta nao ficar pesada."""
    padrao_inicio, padrao_fim = periodo_padrao(hoje)
    inicio = inicio or padrao_inicio
    fim = fim or padrao_fim
    if inicio > fim:
        inicio, fim = fim, inicio
    if (fim - inicio).days >= MAX_DIAS:
        inicio = fim - timedelta(days=MAX_DIAS - 1)
    return inicio, fim


def _agrupar(funcionarios, paralisacoes, chave):
    cfg = AGRUPAMENTOS[chave]
    campos = cfg["campos"]
    linhas = OrderedDict()

    for r in funcionarios.values(*campos).annotate(hh=Sum("hh_total"), efetivo=Count("id"), rdcs=Count("rdc", distinct=True)):
        k = tuple(r[c] for c in campos)
        linhas[k] = {
            "rotulo": cfg["rotulo"](r), "detalhe": cfg["detalhe"](r),
            "hh_trabalhado": _dec(r["hh"]), "hh_perdido": ZERO, "efetivo": r["efetivo"], "rdcs": r["rdcs"],
        }
    for r in paralisacoes.values(*campos).annotate(hh=Sum("hh_perdido")):
        k = tuple(r[c] for c in campos)
        linha = linhas.setdefault(k, {
            "rotulo": cfg["rotulo"](r), "detalhe": cfg["detalhe"](r),
            "hh_trabalhado": ZERO, "hh_perdido": ZERO, "efetivo": 0, "rdcs": 0,
        })
        linha["hh_perdido"] = _dec(r["hh"])

    resultado = sorted(linhas.values(), key=lambda l: (l["hh_trabalhado"] + l["hh_perdido"]), reverse=True)
    maior = max((l["hh_trabalhado"] + l["hh_perdido"] for l in resultado), default=ZERO)
    for l in resultado:
        l["percentual_perdido"] = _percentual(l["hh_perdido"], l["hh_trabalhado"])
        total = l["hh_trabalhado"] + l["hh_perdido"]
        # Larguras das barras (em %) relativas ao maior grupo.
        l["barra_trabalhado"] = float(l["hh_trabalhado"] / maior * 100) if maior else 0
        l["barra_perdido"] = float(l["hh_perdido"] / maior * 100) if maior else 0
        l["hh_total"] = total
    return resultado


def _evolucao(funcionarios, paralisacoes, inicio, fim):
    """Serie por dia; acima de 62 dias agrupa por semana (segunda-feira)."""
    por_semana = (fim - inicio).days > 62

    def balde(d):
        return d - timedelta(days=d.weekday()) if por_semana else d

    pontos = OrderedDict()
    d = balde(inicio)
    passo = timedelta(days=7 if por_semana else 1)
    while d <= fim:
        pontos[d] = {"data": d, "hh_trabalhado": ZERO, "hh_perdido": ZERO}
        d += passo

    for r in funcionarios.values("rdc__data").annotate(hh=Sum("hh_total")):
        pontos.setdefault(balde(r["rdc__data"]), {"data": balde(r["rdc__data"]), "hh_trabalhado": ZERO, "hh_perdido": ZERO})
        pontos[balde(r["rdc__data"])]["hh_trabalhado"] += _dec(r["hh"])
    for r in paralisacoes.values("rdc__data").annotate(hh=Sum("hh_perdido")):
        pontos.setdefault(balde(r["rdc__data"]), {"data": balde(r["rdc__data"]), "hh_trabalhado": ZERO, "hh_perdido": ZERO})
        pontos[balde(r["rdc__data"])]["hh_perdido"] += _dec(r["hh"])

    serie = list(pontos.values())
    maior = max((p["hh_trabalhado"] + p["hh_perdido"] for p in serie), default=ZERO)
    for p in serie:
        p["altura_trabalhado"] = float(p["hh_trabalhado"] / maior * 100) if maior else 0
        p["altura_perdido"] = float(p["hh_perdido"] / maior * 100) if maior else 0
    return {"por_semana": por_semana, "pontos": serie}


def montar_painel_hh(inicio, fim, projeto_id=None):
    funcionarios = RDCFuncionario.objects.filter(rdc__data__gte=inicio, rdc__data__lte=fim)
    paralisacoes = RDCParalisacao.objects.filter(rdc__data__gte=inicio, rdc__data__lte=fim)
    rdcs = RDC.objects.filter(data__gte=inicio, data__lte=fim)
    if projeto_id:
        funcionarios = funcionarios.filter(rdc__projeto_id=projeto_id)
        paralisacoes = paralisacoes.filter(rdc__projeto_id=projeto_id)
        rdcs = rdcs.filter(projeto_id=projeto_id)

    hh_trabalhado = _dec(funcionarios.aggregate(t=Sum("hh_total"))["t"])
    hh_perdido = _dec(paralisacoes.aggregate(t=Sum("hh_perdido"))["t"])

    return {
        "totais": {
            "hh_trabalhado": hh_trabalhado,
            "hh_perdido": hh_perdido,
            "percentual_perdido": _percentual(hh_perdido, hh_trabalhado),
            "rdcs": rdcs.count(),
            "dias_com_rdc": rdcs.values("data").distinct().count(),
            "paralisacoes": paralisacoes.count(),
        },
        "por_area": _agrupar(funcionarios, paralisacoes, "area"),
        "por_disciplina": _agrupar(funcionarios, paralisacoes, "disciplina"),
        "por_casco": _agrupar(funcionarios, paralisacoes, "casco"),
        "por_etapa": _agrupar(funcionarios, paralisacoes, "etapa"),
        "evolucao": _evolucao(funcionarios, paralisacoes, inicio, fim),
    }
