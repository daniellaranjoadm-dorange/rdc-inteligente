"""Avanço físico: previsto (cronograma) x realizado (quantidades lançadas nos RDCs).

- Previsto de cada atividade na data D: linear entre data_inicio e data_fim (0% antes, 100% depois).
- Realizado: soma das quantidades executadas nos RDCs até D, dividida pelo escopo (teto de 100%).
- Agregação ponderada pelo campo "peso" (HH orçado). Sem peso cadastrado, todas valem igual.
"""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from planejamento.models import AtividadeCronograma
from rdc.models import RDCAtividade

TOLERANCIA_PP = 5.0  # pontos percentuais para considerar "no prazo"


def fracao_prevista(inicio, fim, data):
    if data < inicio:
        return 0.0
    if data >= fim:
        return 1.0
    total = (fim - inicio).days + 1
    return ((data - inicio).days + 1) / total


def situacao(previsto, realizado):
    if realizado >= 99.95:
        return "concluido", "Concluído"
    if previsto <= 0 and realizado <= 0:
        return "nao_iniciado", "Não iniciado"
    desvio = realizado - previsto
    if desvio < -TOLERANCIA_PP:
        return "atrasado", "Atrasado"
    if desvio > TOLERANCIA_PP:
        return "adiantado", "Adiantado"
    return "no_prazo", "No prazo"


def _pesos(atividades):
    positivos = [float(a.peso) for a in atividades if a.peso and a.peso > 0]
    media = sum(positivos) / len(positivos) if positivos else 1.0
    return {a.pk: (float(a.peso) if a.peso and a.peso > 0 else media) for a in atividades}, bool(positivos)


def _execucoes(atividades, data_corte):
    """{atividade_cronograma_id: [(data, qtd), ...]} só com lançamentos até a data de corte."""
    por_id = {a.pk: a for a in atividades}
    por_chave = {(a.projeto_id, a.area_local_id, a.disciplina_id, a.codigo_atividade): a.pk for a in atividades}
    projetos = {a.projeto_id for a in atividades}
    linhas = (
        RDCAtividade.objects.filter(rdc__projeto_id__in=projetos, rdc__data__lte=data_corte, qtd_executada__gt=0)
        .values_list("atividade_cronograma_id", "rdc__projeto_id", "rdc__area_local_id", "rdc__disciplina_id",
                     "codigo_atividade", "rdc__data", "qtd_executada")
    )
    resultado = defaultdict(list)
    for crono_id, proj, area, disc, codigo, dia, qtd in linhas:
        alvo = crono_id if crono_id in por_id else por_chave.get((proj, area, disc, codigo))
        if alvo:
            resultado[alvo].append((dia, qtd))
    return resultado


def _linha(nome, itens, pesos, extra=None):
    peso_total = sum(pesos[i["id"]] for i in itens) or 1.0
    previsto = sum(pesos[i["id"]] * i["previsto"] for i in itens) / peso_total
    realizado = sum(pesos[i["id"]] * i["realizado"] for i in itens) / peso_total
    codigo, rotulo = situacao(previsto, realizado)
    linha = {
        "nome": nome,
        "atividades": len(itens),
        "previsto": round(previsto, 1),
        "realizado": round(realizado, 1),
        "desvio": round(realizado - previsto, 1),
        "spi": round(realizado / previsto, 2) if previsto > 0 else None,
        "situacao": codigo,
        "situacao_label": rotulo,
        "atrasadas": sum(1 for i in itens if i["situacao"] == "atrasado"),
    }
    linha.update(extra or {})
    return linha


def _curva_s(atividades, pesos, execucoes, data_corte):
    inicio = min(a.data_inicio for a in atividades)
    fim = max(a.data_fim for a in atividades)
    passo = 7 if (fim - inicio).days > 90 else 1
    if (fim - inicio).days / passo > 160:
        passo = 30
    datas, d = [], inicio
    while d < fim:
        datas.append(d)
        d += timedelta(days=passo)
    datas.append(fim)
    if inicio <= data_corte <= fim and data_corte not in datas:
        datas.append(data_corte)
        datas.sort()

    peso_total = sum(pesos.values()) or 1.0
    pontos = []
    for dia in datas:
        prev = sum(pesos[a.pk] * fracao_prevista(a.data_inicio, a.data_fim, dia) for a in atividades)
        real = None
        if dia <= data_corte:
            real = 0.0
            for a in atividades:
                if a.qtd_escopo and a.qtd_escopo > 0:
                    feito = sum((q for (data_exec, q) in execucoes.get(a.pk, ()) if data_exec <= dia), Decimal("0"))
                    real += pesos[a.pk] * min(float(feito / a.qtd_escopo), 1.0)
            real = round(real / peso_total * 100, 1)
        pontos.append({"data": dia, "previsto": round(prev / peso_total * 100, 1), "realizado": real})
    return pontos


def montar_avanco(data_corte, projeto_id=None, casco="", area_id=None):
    qs = AtividadeCronograma.objects.select_related("projeto", "area_local", "disciplina")
    if projeto_id:
        qs = qs.filter(projeto_id=projeto_id)
    if casco:
        qs = qs.filter(area_local__casco=casco)
    atividades = list(qs)
    vazio = {"tem_dados": False, "data_corte": data_corte, "total": None, "por_area": [], "por_disciplina": [],
             "por_unidade": [], "curva": [], "detalhe": None, "usa_peso": False, "sem_escopo": 0}
    if not atividades:
        return vazio

    pesos, usa_peso = _pesos(atividades)
    execucoes = _execucoes(atividades, data_corte)

    itens, sem_escopo = [], 0
    for a in atividades:
        executado = sum((q for _, q in execucoes.get(a.pk, ())), Decimal("0"))
        if a.qtd_escopo and a.qtd_escopo > 0:
            realizado = min(float(executado / a.qtd_escopo), 1.0) * 100
        else:
            realizado = 0.0
            sem_escopo += 1
        previsto = fracao_prevista(a.data_inicio, a.data_fim, data_corte) * 100
        codigo, rotulo = situacao(previsto, realizado)
        itens.append({
            "id": a.pk, "obj": a, "previsto": round(previsto, 1), "realizado": round(realizado, 1),
            "desvio": round(realizado - previsto, 1), "executado": executado, "situacao": codigo,
            "situacao_label": rotulo,
        })

    por_area, por_disc, por_unid = defaultdict(list), defaultdict(list), defaultdict(lambda: [Decimal("0"), Decimal("0")])
    for item in itens:
        a = item["obj"]
        por_area[a.area_local].append(item)
        por_disc[a.disciplina].append(item)
        unidade = (a.unidade or "UN").strip().upper()
        por_unid[unidade][0] += a.qtd_escopo or 0
        por_unid[unidade][1] += item["executado"]

    linhas_area = sorted(
        (_linha(area.descricao, lista, pesos, {"area": area, "codigo": area.codigo}) for area, lista in por_area.items()),
        key=lambda l: (l["desvio"], l["nome"]),
    )
    linhas_disc = sorted(
        (_linha(disc.nome, lista, pesos) for disc, lista in por_disc.items()), key=lambda l: (l["desvio"], l["nome"]),
    )
    unidades = [
        {"unidade": u, "escopo": esc, "executado": exe,
         "percentual": round(float(min(exe / esc, 1)) * 100, 1) if esc else None}
        for u, (esc, exe) in sorted(por_unid.items())
    ]

    detalhe = None
    if area_id:
        lista = [i for i in itens if str(i["obj"].area_local_id) == str(area_id)]
        if lista:
            detalhe = {"area": lista[0]["obj"].area_local,
                       "itens": sorted(lista, key=lambda i: (i["obj"].data_inicio, i["obj"].codigo_atividade))}

    return {
        "tem_dados": True,
        "data_corte": data_corte,
        "total": _linha("Total", itens, pesos),
        "por_area": linhas_area,
        "por_disciplina": linhas_disc,
        "por_unidade": unidades,
        "curva": _curva_s(atividades, pesos, execucoes, data_corte),
        "detalhe": detalhe,
        "usa_peso": usa_peso,
        "sem_escopo": sem_escopo,
        "inicio": min(a.data_inicio for a in atividades),
        "fim": max(a.data_fim for a in atividades),
    }


def svg_curva(pontos, largura=760, altura=240, margem=34):
    """Coordenadas prontas para o template desenhar a curva S em SVG (sem biblioteca externa)."""
    if not pontos:
        return None
    n = len(pontos)
    util_w, util_h = largura - margem - 10, altura - margem - 10

    def x(i):
        return margem + (util_w * i / (n - 1) if n > 1 else util_w / 2)

    def y(v):
        return 10 + util_h * (1 - v / 100)

    prev = " ".join(f"{x(i):.1f},{y(p['previsto']):.1f}" for i, p in enumerate(pontos))
    real = " ".join(f"{x(i):.1f},{y(p['realizado']):.1f}" for i, p in enumerate(pontos) if p["realizado"] is not None)
    passo = max(1, n // 6)

    def f(v):  # ponto decimal fixo: o template em pt-BR trocaria por virgula e quebraria o SVG
        return f"{v:.1f}"

    rotulos = [{"x": f(x(i)), "texto": p["data"].strftime("%d/%m/%y")} for i, p in enumerate(pontos) if i % passo == 0]
    grade = [{"y": f(y(v)), "ty": f(y(v) + 4), "v": v} for v in (0, 25, 50, 75, 100)]
    marcadores = [{"x": f(x(i)), "rx": f(x(i) - 6),
                   "yr": f(y(p["realizado"])) if p["realizado"] is not None else None,
                   "titulo": f"{p['data']:%d/%m/%Y} · previsto {p['previsto']}%"
                             + (f" · realizado {p['realizado']}%" if p["realizado"] is not None else "")}
                  for i, p in enumerate(pontos)]
    return {"largura": largura, "altura": altura, "prev": prev, "real": real, "rotulos": rotulos, "grade": grade,
            "base_y": f(y(0)), "margem": margem, "tx": margem - 6, "ty_rot": altura - 6, "fim_x": largura - 10,
            "marcadores": marcadores}
