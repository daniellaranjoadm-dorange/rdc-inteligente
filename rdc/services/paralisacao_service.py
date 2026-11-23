"""Resumo das paralisacoes e do HH perdido, usado na tela do RDC, no painel e no Excel."""
from decimal import Decimal

from django.db.models import Count, Sum

from core.choices import MotivoParalisacaoChoices, ResponsabilidadeParalisacaoChoices

ZERO = Decimal("0.00")
_MOTIVOS = dict(MotivoParalisacaoChoices.CHOICES)
_RESPONSABILIDADES = dict(ResponsabilidadeParalisacaoChoices.CHOICES)


def _dec(valor):
    return Decimal(valor or 0).quantize(Decimal("0.01"))


def resumir_paralisacoes(queryset, hh_trabalhado=None):
    """Totais de um conjunto de paralisacoes (de um RDC ou de varios).

    hh_trabalhado, quando informado, permite calcular o % do HH disponivel que foi perdido.
    """
    totais = queryset.aggregate(qtd=Count("id"), horas=Sum("horas"), hh=Sum("hh_perdido"))
    hh_perdido = _dec(totais["hh"])

    por_motivo = [
        {
            "codigo": linha["motivo"],
            "rotulo": _MOTIVOS.get(linha["motivo"], linha["motivo"]),
            "qtd": linha["qtd"],
            "hh": _dec(linha["hh"]),
            "climatico": linha["motivo"] in MotivoParalisacaoChoices.CLIMATICOS,
        }
        for linha in queryset.values("motivo").annotate(qtd=Count("id"), hh=Sum("hh_perdido")).order_by("-hh")
    ]
    por_responsabilidade = [
        {
            "codigo": linha["responsabilidade"],
            "rotulo": _RESPONSABILIDADES.get(linha["responsabilidade"], linha["responsabilidade"] or "-"),
            "hh": _dec(linha["hh"]),
        }
        for linha in queryset.values("responsabilidade").annotate(hh=Sum("hh_perdido")).order_by("-hh")
    ]

    # Sem HH trabalhado lancado, o percentual daria sempre 100% e enganaria: fica sem valor.
    percentual = None
    if hh_trabalhado is not None and _dec(hh_trabalhado) > 0:
        disponivel = _dec(hh_trabalhado) + hh_perdido
        percentual = (hh_perdido / disponivel * 100).quantize(Decimal("0.1"))

    return {
        "qtd": totais["qtd"] or 0,
        "horas": _dec(totais["horas"]),
        "hh_perdido": hh_perdido,
        "por_motivo": por_motivo,
        "por_responsabilidade": por_responsabilidade,
        "percentual_perdido": percentual,
    }


def texto_paralisacoes_excel(rdc):
    """Linha curta para o rodape do RDC exportado em Excel."""
    resumo = resumir_paralisacoes(rdc.paralisacoes.all())
    if not resumo["qtd"]:
        return "Paralisações: nenhuma registrada"
    def br(valor):
        return f"{valor:.2f}".replace(".", ",")

    partes = [f"{m['rotulo']} {br(m['hh'])} HH" for m in resumo["por_motivo"]]
    return (
        f"Paralisações: {resumo['qtd']} | {br(resumo['horas'])} h paradas | "
        f"HH perdido {br(resumo['hh_perdido'])} ({'; '.join(partes)})"
    )
