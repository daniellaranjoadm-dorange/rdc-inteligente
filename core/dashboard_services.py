from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from importacoes.models import ImportacaoArquivo
from rdc.models import RDC, RDCApontamento, RDCFuncionario, RDCValidacao


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
        return cls(
            hoje=hoje,
            inicio_semana=inicio_semana,
            inicio_mes=inicio_mes,
        )


class HomeDashboardService:
    def __init__(self, period: DashboardPeriod | None = None) -> None:
        self.period = period or DashboardPeriod.current()

    def build(self) -> dict[str, Any]:
        hoje = self.period.hoje

        rdcs = RDC.objects.select_related(
            "projeto",
            "disciplina",
            "area_local",
        )

        rdcs_hoje = rdcs.filter(data=hoje)
        rdcs_semana = rdcs.filter(
            data__gte=self.period.inicio_semana,
            data__lte=hoje,
        )
        rdcs_mes = rdcs.filter(
            data__gte=self.period.inicio_mes,
            data__lte=hoje,
        )

        rdcs_por_status = list(
            rdcs.values("status").annotate(total=Count("id")).order_by("status")
        )

        ultimos_rdcs = list(
            rdcs.order_by("-data", "-id")[:10]
        )

        importacoes_recentes = list(
            ImportacaoArquivo.objects.order_by("-created_at")[:8]
        )

        importacoes_com_erro = ImportacaoArquivo.objects.filter(
            status__in=["erro", "concluido_com_erros"]
        ).count()

        funcionarios_hoje = RDCFuncionario.objects.filter(rdc__data=hoje)
        apontamentos_hoje = RDCApontamento.objects.filter(rdc__data=hoje)
        validacoes_hoje = RDCValidacao.objects.filter(rdc__data=hoje)

        hh_hoje = funcionarios_hoje.aggregate(total=Sum("hh_total"))["total"] or Decimal("0.00")
        efetivo_hoje = funcionarios_hoje.count()
        presentes_hoje = funcionarios_hoje.filter(presente_catraca=True).count()
        bloqueados_hoje = funcionarios_hoje.filter(elegivel=False).count()

        rdcs_criticos_hoje = validacoes_hoje.filter(status="bloqueio").values("rdc_id").distinct().count()
        rdcs_alerta_hoje = validacoes_hoje.filter(
            status__in=["alerta", "pendencia", "info"]
        ).values("rdc_id").distinct().count()

        total_rdcs_hoje = rdcs_hoje.count()
        rdcs_saudaveis_hoje = max(total_rdcs_hoje - rdcs_criticos_hoje - rdcs_alerta_hoje, 0)

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

        return {
            "hoje": hoje,
            "total_rdcs": rdcs.count(),
            "total_rdcs_hoje": total_rdcs_hoje,
            "total_rdcs_semana": rdcs_semana.count(),
            "total_rdcs_mes": rdcs_mes.count(),
            "rdcs_por_status": rdcs_por_status,
            "ultimos_rdcs": ultimos_rdcs,
            "importacoes_recentes": importacoes_recentes,
            "importacoes_com_erro": importacoes_com_erro,
            "hh_hoje": hh_hoje,
            "efetivo_hoje": efetivo_hoje,
            "presentes_hoje": presentes_hoje,
            "bloqueados_hoje": bloqueados_hoje,
            "rdcs_criticos_hoje": rdcs_criticos_hoje,
            "rdcs_alerta_hoje": rdcs_alerta_hoje,
            "rdcs_saudaveis_hoje": rdcs_saudaveis_hoje,
            "projeto_stats": projeto_stats,
            "disciplina_stats": disciplina_stats,
            "quick_actions": [
                {"label": "Novo RDC", "url": "/rdc/novo/"},
                {"label": "Dashboard RDC", "url": "/rdc/dashboard/"},
                {"label": "Lista RDC", "url": "/rdc/"},
            ],
            "status_cards": [],
            "fila_atencao": [],
            "agenda_hoje": [],
            "delta_hh": Decimal("0.00"),
            "atividades_execucao_hoje": apontamentos_hoje.values("rdc_atividade_id").distinct().count(),
            "apontamentos_hoje": apontamentos_hoje.count(),
            "apontamentos_obs_hoje": apontamentos_hoje.exclude(observacao="").count(),
            "top_alertas": [],
        }
