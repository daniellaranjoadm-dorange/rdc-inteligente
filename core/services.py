from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, Sum
from django.utils import timezone

from importacoes.models import ImportacaoArquivo
from rdc.models import RDC, RDCApontamento, RDCFuncionario, RDCValidacao


STATUS_LABELS = {
    "rascunho": "Rascunho",
    "pre_preenchido": "Pré-preenchido",
    "em_revisao": "Em revisão",
    "aprovado": "Aprovado",
    "fechado": "Fechado",
}

STATUS_BADGES = {
    "rascunho": "secondary",
    "pre_preenchido": "info",
    "em_revisao": "warning",
    "aprovado": "primary",
    "fechado": "success",
}


@dataclass(frozen=True)
class DashboardPeriod:
    hoje: Any
    inicio_semana: Any
    inicio_mes: Any

    @classmethod
    def current(cls) -> "DashboardPeriod":
        hoje = timezone.localdate()
        inicio_semana = hoje - timezone.timedelta(days=hoje.weekday())
        inicio_mes = hoje.replace(day=1)
        return cls(hoje=hoje, inicio_semana=inicio_semana, inicio_mes=inicio_mes)


class HomeDashboardService:
    """Consolida indicadores da home sem deixar a view carregar regra de negócio."""

    def __init__(self, *, period: DashboardPeriod | None = None) -> None:
        self.period = period or DashboardPeriod.current()

    def build(self) -> dict[str, Any]:
        hoje = self.period.hoje
        base_rdcs = RDC.objects.select_related("projeto", "disciplina", "area_local", "criado_por")
        rdcs_hoje = base_rdcs.filter(data=hoje)
        rdcs_semana = base_rdcs.filter(data__gte=self.period.inicio_semana, data__lte=hoje)
        rdcs_mes = base_rdcs.filter(data__gte=self.period.inicio_mes, data__lte=hoje)

        funcionarios_hoje = RDCFuncionario.objects.filter(rdc__data=hoje)
        apontamentos_hoje = RDCApontamento.objects.filter(rdc__data=hoje).select_related(
            "rdc", "rdc_funcionario", "rdc_atividade"
        )
        validacoes_hoje = RDCValidacao.objects.filter(rdc__data=hoje)

        hh_hoje = funcionarios_hoje.aggregate(total=Sum("hh_total"))["total"] or Decimal("0.00")
        presentes_hoje = funcionarios_hoje.filter(presente_catraca=True).count()
        bloqueados_hoje = funcionarios_hoje.filter(elegivel=False).count()
        efetivo_hoje = funcionarios_hoje.count()

        atividades_execucao_hoje = (
            apontamentos_hoje.values("rdc_atividade_id").distinct().count()
        )
        apontamentos_obs_hoje = apontamentos_hoje.exclude(observacao="").count()

        status_rows = list(
            base_rdcs.values("status").annotate(total=Count("id")).order_by("status")
        )
        status_counter = {row["status"]: row["total"] for row in status_rows}

        criticos = validacoes_hoje.filter(status="bloqueio").values("rdc_id").distinct().count()
        alertas = validacoes_hoje.filter(status__in=["alerta", "pendencia", "info"]).values("rdc_id").distinct().count()
        saudaveis = max(rdcs_hoje.count() - criticos - alertas, 0)

        projeto_stats = list(
            rdcs_mes.values("projeto__codigo", "projeto__nome")
            .annotate(total=Count("id"))
            .order_by("-total", "projeto__codigo")[:6]
        )
        disciplina_stats = list(
            rdcs_mes.values("disciplina__nome")
            .annotate(total=Count("id"))
            .order_by("-total", "disciplina__nome")[:6]
        )
        status_cards = self._build_status_cards(status_counter)
        quick_actions = self._build_quick_actions(rdcs_hoje.count(), criticos)

        importacoes_recentes = list(
            ImportacaoArquivo.objects.select_related("criado_por").order_by("-created_at")[:8]
        )
        importacoes_com_erro = ImportacaoArquivo.objects.filter(
            status__in=["erro", "concluido_com_erros"]
        ).count()

        top_alertas = self._build_top_alertas(validacoes_hoje)
        agenda_hoje = list(rdcs_hoje.order_by("projeto__codigo", "disciplina__nome", "turno", "id")[:8])
        ultimos_rdcs = list(base_rdcs.order_by("-data", "-created_at")[:10])
        fila_atencao = list(
            rdcs_hoje.annotate(
                bloqueios=Count(
                    "validacoes",
                    filter=Q(validacoes__status="bloqueio"),
                    distinct=True,
                ),
                alertas=Count(
                    "validacoes",
                    filter=Q(validacoes__status__in=["alerta", "pendencia"]),
                    distinct=True,
                ),
            )
            .order_by("-bloqueios", "-alertas", "projeto__codigo", "disciplina__nome")[:10]
        )

        return {
            "hoje": hoje,
            "total_rdcs": base_rdcs.count(),
            "total_rdcs_hoje": rdcs_hoje.count(),
            "total_rdcs_semana": rdcs_semana.count(),
            "total_rdcs_mes": rdcs_mes.count(),
            "rdcs_por_status": status_rows,
            "status_cards": status_cards,
            "ultimos_rdcs": ultimos_rdcs,
            "fila_atencao": fila_atencao,
            "agenda_hoje": agenda_hoje,
            "quick_actions": quick_actions,
            "hh_hoje": hh_hoje,
            "delta_hh": Decimal("0.00"),
            "presentes_hoje": presentes_hoje,
            "bloqueados_hoje": bloqueados_hoje,
            "efetivo_hoje": efetivo_hoje,
            "atividades_execucao_hoje": atividades_execucao_hoje,
            "apontamentos_hoje": apontamentos_hoje.count(),
            "apontamentos_obs_hoje": apontamentos_obs_hoje,
            "rdcs_criticos_hoje": criticos,
            "rdcs_alerta_hoje": alertas,
            "rdcs_saudaveis_hoje": saudaveis,
            "top_alertas": top_alertas,
            "projeto_stats": projeto_stats,
            "disciplina_stats": disciplina_stats,
            "importacoes_recentes": importacoes_recentes,
            "importacoes_com_erro": importacoes_com_erro,
        }

    def _build_status_cards(self, status_counter: dict[str, int]) -> list[dict[str, Any]]:
        ordered_keys = [
            "rascunho",
            "pre_preenchido",
            "em_revisao",
            "aprovado",
            "fechado",
        ]
        cards: list[dict[str, Any]] = []
        for key in ordered_keys:
            cards.append(
                {
                    "key": key,
                    "label": STATUS_LABELS[key],
                    "total": status_counter.get(key, 0),
                    "badge": STATUS_BADGES[key],
                }
            )
        return cards

    def _build_quick_actions(self, total_hoje: int, criticos: int) -> list[dict[str, str]]:
        actions = [
            {
                "label": "Novo RDC",
                "url": "/rdc/novo/",
                "variant": "light",
                "icon": "plus-circle",
            },
            {
                "label": "Painel RDC",
                "url": "/rdc/consolidado/",
                "variant": "outline-light",
                "icon": "bar-chart",
            },
            {
                "label": "RDO gerencial",
                "url": "/rdc/rdo/",
                "variant": "outline-light",
                "icon": "clipboard-data",
            },
        ]
        if total_hoje == 0:
            actions[0]["label"] = "Criar primeiro RDC do dia"
        if criticos > 0:
            actions.insert(
                1,
                {
                    "label": "Tratar pendências",
                    "url": "/rdc/dashboard/",
                    "variant": "warning",
                    "icon": "exclamation-triangle",
                },
            )
        return actions

    def _build_top_alertas(self, validacoes_hoje):
        grouped = list(
            validacoes_hoje.values("tipo", "status")
            .annotate(total=Count("id"))
            .order_by("-total", "tipo")[:6]
        )
        for row in grouped:
            row["label"] = row["tipo"].replace("_", " ").title()
        return grouped

