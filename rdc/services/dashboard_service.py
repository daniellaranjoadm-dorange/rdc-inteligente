from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import connection
from django.db.models import Count, Q, Sum
from django.utils import timezone

from rdc.models import RDC, RDCAtividade, RDCApontamento, RDCFuncionario, RDCValidacao


STATUS_KEYS = ["rascunho", "pre_preenchido", "em_revisao", "aprovado", "fechado"]


def _safe_decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value or "0"))


def _audit_schema_ok() -> bool:
    try:
        return "rdc_rdcauditoria" in connection.introspection.table_names()
    except Exception:
        return False


def _status_summary(queryset) -> dict[str, int]:
    counts = {item["status"]: item["total"] for item in queryset.values("status").annotate(total=Count("id"))}
    return {key: counts.get(key, 0) for key in STATUS_KEYS}


def build_rdc_dashboard_home_context() -> dict[str, Any]:
    hoje = timezone.localdate()
    ontem = hoje - timezone.timedelta(days=1)
    inicio_semana = hoje - timezone.timedelta(days=hoje.weekday())

    rdcs_base = RDC.objects.select_related("projeto", "disciplina", "area_local")
    rdcs_hoje = rdcs_base.filter(data=hoje).order_by("-id")
    rdcs_semana = rdcs_base.filter(data__gte=inicio_semana, data__lte=hoje)

    funcionarios_hoje = RDCFuncionario.objects.filter(rdc__data=hoje).select_related("rdc", "rdc__disciplina")
    funcionarios_ontem = RDCFuncionario.objects.filter(rdc__data=ontem)
    atividades_hoje = RDCAtividade.objects.filter(rdc__data=hoje).select_related("rdc", "rdc__disciplina")
    apontamentos_hoje_qs = RDCApontamento.objects.filter(rdc__data=hoje)
    validacoes_hoje = RDCValidacao.objects.filter(rdc__data=hoje)

    hh_hoje = _safe_decimal(funcionarios_hoje.aggregate(total=Sum("hh_total"))["total"])
    hh_ontem = _safe_decimal(funcionarios_ontem.aggregate(total=Sum("hh_total"))["total"])
    delta_hh = hh_hoje - hh_ontem

    criticos_ids = set(validacoes_hoje.filter(status="bloqueio").values_list("rdc_id", flat=True).distinct())
    alerta_ids = set(
        validacoes_hoje.filter(status__in=["alerta", "info", "pendencia"])
        .exclude(rdc_id__in=criticos_ids)
        .values_list("rdc_id", flat=True)
        .distinct()
    )
    total_rdcs_hoje = rdcs_hoje.count()

    fila_atencao = list(
        rdcs_hoje.annotate(
            bloqueios=Count("validacoes", filter=Q(validacoes__status="bloqueio"), distinct=True),
            alertas=Count("validacoes", filter=Q(validacoes__status__in=["alerta", "info", "pendencia"]), distinct=True),
        ).order_by("-bloqueios", "-alertas", "-id")[:10]
    )

    top_alertas = list(
        validacoes_hoje.values("tipo")
        .annotate(total=Count("id"))
        .order_by("-total", "tipo")[:6]
    )
    for item in top_alertas:
        item["label"] = str(item.get("tipo") or "Sem tipo").replace("_", " ").title()

    status_summary = _status_summary(rdcs_semana)

    return {
        "hoje": hoje,
        "data_hoje": hoje,
        "quick_actions": [
            {"label": "Novo RDC", "url": "/rdc/novo/", "style": "light"},
            {"label": "Painel consolidado", "url": "/rdc/consolidado/", "style": "outline-light"},
            {"label": "RDO gerencial", "url": "/rdc/rdo/", "style": "outline-light"},
        ],
        "rdcs_hoje": rdcs_hoje,
        "total_rdcs": rdcs_base.count(),
        "total_rdcs_hoje": total_rdcs_hoje,
        "total_rdcs_semana": rdcs_semana.count(),
        "rdcs_fechados_hoje": rdcs_hoje.filter(status="fechado").count(),
        "hh_hoje": hh_hoje,
        "delta_hh": delta_hh,
        "efetivo_hoje": funcionarios_hoje.count(),
        "presentes_hoje": funcionarios_hoje.filter(presente_catraca=True).count(),
        "bloqueados_hoje": funcionarios_hoje.filter(elegivel=False).count(),
        "atividades_execucao_hoje": atividades_hoje.filter(qtd_executada__gt=0).count(),
        "apontamentos_hoje": apontamentos_hoje_qs.count(),
        "apontamentos_obs_hoje": apontamentos_hoje_qs.exclude(observacao__isnull=True).exclude(observacao__exact="").count(),
        "ultimos_rdcs": list(rdcs_base.order_by("-data", "-id")[:8]),
        "fila_atencao": fila_atencao,
        "rdcs_criticos_hoje": len(criticos_ids),
        "rdcs_alerta_hoje": len(alerta_ids),
        "rdcs_saudaveis_hoje": max(total_rdcs_hoje - len(criticos_ids) - len(alerta_ids), 0),
        "agenda_hoje": list(rdcs_hoje[:6]),
        "top_alertas": top_alertas,
        "desvios_tipos": top_alertas,
        "projeto_stats": list(
            rdcs_semana.values("projeto__codigo", "projeto__nome")
            .annotate(total=Count("id"))
            .order_by("-total", "projeto__codigo")[:6]
        ),
        "disciplina_hh": list(
            RDCFuncionario.objects.filter(rdc__data__gte=inicio_semana, rdc__data__lte=hoje)
            .values("rdc__disciplina__nome")
            .annotate(total=Sum("hh_total"))
            .order_by("-total", "rdc__disciplina__nome")[:6]
        ),
        "status_summary": status_summary,
    }


def build_rdc_detail_context(rdc, *, user=None) -> dict[str, Any]:
    funcionarios_qs = rdc.funcionarios.select_related("equipe", "funcao", "funcionario")
    atividades_qs = rdc.atividades.all()
    apontamentos_qs = rdc.apontamentos.select_related("rdc_funcionario", "rdc_atividade")
    validacoes_qs = rdc.validacoes.all()

    hh_total = _safe_decimal(funcionarios_qs.aggregate(total=Sum("hh_total"))["total"])
    alertas = validacoes_qs.filter(status="alerta").count()
    bloqueios = validacoes_qs.filter(status="bloqueio").count()
    infos = validacoes_qs.filter(status="info").count()

    if bloqueios:
        nivel = "danger"
        rotulo = "Crítico"
    elif alertas:
        nivel = "warning"
        rotulo = "Atenção"
    else:
        nivel = "success"
        rotulo = "Pronto"

    schema_auditoria_ok = _audit_schema_ok()
    auditorias = []
    auditorias_recent = []
    if schema_auditoria_ok:
        try:
            auditorias = list(rdc.auditorias.select_related("usuario").all()[:12])
            auditorias_recent = auditorias[:5]
        except Exception:
            schema_auditoria_ok = False
            auditorias = []
            auditorias_recent = []

    return {
        "dashboard": {
            "total_atividades": atividades_qs.count(),
            "total_funcionarios": funcionarios_qs.count(),
            "total_apontamentos": apontamentos_qs.count(),
            "hh_total": hh_total,
            "alertas": alertas,
            "bloqueios": bloqueios,
            "infos": infos,
            "nivel": nivel,
            "rotulo": rotulo,
            "funcionarios_bloqueados": funcionarios_qs.filter(elegivel=False).count(),
            "funcionarios_presentes": funcionarios_qs.filter(presente_catraca=True).count(),
            "atividades_com_execucao": atividades_qs.filter(qtd_executada__gt=0).count(),
        },
        "fechamento_resumo": {
            "bloqueios": bloqueios,
            "alertas": alertas,
            "funcionarios": funcionarios_qs.count(),
            "hh_total": hh_total,
        },
        "status_badge": getattr(rdc, "workflow_badge", "secondary"),
        "can_edit_rdc": rdc.usuario_pode_editar(user),
        "can_force_close": rdc.usuario_pode_forcar_fechamento(user),
        "can_reopen_rdc": rdc.usuario_pode_reabrir(user),
        "can_send_review": getattr(rdc, "usuario_pode_enviar_revisao", lambda u: False)(user),
        "can_approve_rdc": getattr(rdc, "usuario_pode_aprovar", lambda u: False)(user),
        "can_return_rdc": getattr(rdc, "usuario_pode_devolver", lambda u: False)(user),
        "schema_auditoria_ok": schema_auditoria_ok,
        "auditorias": auditorias,
        "auditorias_recent": auditorias_recent,
    }

