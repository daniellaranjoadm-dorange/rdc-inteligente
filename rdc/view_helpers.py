from decimal import Decimal
import csv

from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone


def _safe_decimal(valor):
    return valor if isinstance(valor, Decimal) else Decimal(str(valor or "0"))


def _apply_text_filter(queryset, termo, campos):
    termo = (termo or "").strip()
    if not termo:
        return queryset

    filtros = Q()
    for campo in campos:
        filtros |= Q(**{f"{campo}__icontains": termo})
    return queryset.filter(filtros)


def _apply_bool_filter(queryset, valor, campo):
    valor = (valor or "").strip().lower()
    if not valor:
        return queryset
    if valor in {"1", "true", "sim", "yes"}:
        return queryset.filter(**{campo: True})
    if valor in {"0", "false", "nao", "não", "no"}:
        return queryset.filter(**{campo: False})
    return queryset


def _apply_exact_filter(queryset, valor, campo):
    valor = (valor or "").strip()
    if not valor:
        return queryset
    return queryset.filter(**{campo: valor})


def _make_csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    return response


def _resumo_validacoes(rdc):
    validacoes = rdc.validacoes.all()
    alertas = validacoes.filter(status__iexact="alerta").count()
    bloqueios = validacoes.filter(status__iexact="bloqueio").count()
    infos = validacoes.filter(status__iexact="info").count()

    if bloqueios:
        nivel = "danger"
        rotulo = "Crítico"
    elif alertas:
        nivel = "warning"
        rotulo = "Atenção"
    else:
        nivel = "success"
        rotulo = "Pronto"

    return {
        "alertas": alertas,
        "bloqueios": bloqueios,
        "infos": infos,
        "nivel": nivel,
        "rotulo": rotulo,
    }


def _status_summary_for_queryset(queryset):
    base = queryset.values("status").annotate(total=Count("id"))
    counts = {item["status"]: item["total"] for item in base}

    return {
        "rascunho": counts.get("rascunho", 0),
        "pre_preenchido": counts.get("pre_preenchido", 0),
        "em_revisao": counts.get("em_revisao", 0),
        "aprovado": counts.get("aprovado", 0),
        "fechado": counts.get("fechado", 0),
        "total": queryset.count(),
    }


def _list_kpis_for_queryset(queryset, page_qs=None):
    status = _status_summary_for_queryset(queryset)
    hoje = timezone.localdate()

    return {
        "total": status["total"],
        "em_revisao": status["em_revisao"],
        "fechados": status["fechado"],
        "pre_preenchidos": status["pre_preenchido"],
        "aprovados": status["aprovado"],
        "rascunhos": status["rascunho"],
        "hoje": queryset.filter(data=hoje).count(),
        "pagina": len(page_qs) if page_qs is not None else 0,
    }


def _quick_filters():
    hoje = timezone.localdate()
    ontem = hoje - timezone.timedelta(days=1)
    inicio_mes = hoje.replace(day=1)
    return {
        "hoje": {"data_ini": hoje.isoformat(), "data_fim": hoje.isoformat()},
        "ontem": {"data_ini": ontem.isoformat(), "data_fim": ontem.isoformat()},
        "ultimos_7_dias": {
            "data_ini": (hoje - timezone.timedelta(days=6)).isoformat(),
            "data_fim": hoje.isoformat(),
        },
        "mes_atual": {"data_ini": inicio_mes.isoformat(), "data_fim": hoje.isoformat()},
    }


def _format_export_value(value):
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%d/%m/%Y")
        except Exception:
            return str(value)
    return str(value)


def _resumo_montagem_detalhe(rdc):
    atividades_planejamento = rdc.atividades.filter(origem__iexact="planejamento").count()
    atividades_cronograma = rdc.atividades.filter(origem__iexact="cronograma").count()
    atividades_total = rdc.atividades.count()

    funcionarios_total = rdc.funcionarios.count()
    funcionarios_com_catraca = rdc.funcionarios.filter(presente_catraca=True).count()
    funcionarios_sem_catraca = rdc.funcionarios.filter(presente_catraca=False).count()
    funcionarios_nao_elegiveis = rdc.funcionarios.filter(elegivel=False).count()

    validacoes = rdc.validacoes.all()
    alertas = validacoes.filter(status__iexact="alerta").count()
    bloqueios = validacoes.filter(status__iexact="bloqueio").count()
    infos = validacoes.filter(status__iexact="info").count()

    status_geral = "ok"
    if bloqueios > 0:
        status_geral = "critico"
    elif alertas > 0:
        status_geral = "atencao"

    return {
        "atividades_planejamento": atividades_planejamento,
        "atividades_cronograma": atividades_cronograma,
        "atividades_total": atividades_total,
        "funcionarios_total": funcionarios_total,
        "funcionarios_com_catraca": funcionarios_com_catraca,
        "funcionarios_sem_catraca": funcionarios_sem_catraca,
        "funcionarios_nao_elegiveis": funcionarios_nao_elegiveis,
        "alertas": alertas,
        "bloqueios": bloqueios,
        "infos": infos,
        "status_geral": status_geral,
    }


def _date_shortcuts_for_reference(data_ref):
    return [
        {
            "label": "Ontem",
            "value": (data_ref - timezone.timedelta(days=1)).isoformat(),
            "active": False,
        },
        {
            "label": "Hoje",
            "value": timezone.localdate().isoformat(),
            "active": data_ref == timezone.localdate(),
        },
        {
            "label": "Amanhã",
            "value": (data_ref + timezone.timedelta(days=1)).isoformat(),
            "active": False,
        },
    ]


def _montagem_health(contexto, resumo):
    contexto = contexto or {}
    resumo = resumo or {}

    tem_contexto_minimo = bool(contexto.get("tem_contexto_minimo", False))
    atividades_sugeridas = contexto.get("atividades_sugeridas") or []
    total_atividades_sugeridas = len(atividades_sugeridas)

    perfil_ok = bool(contexto.get("perfil"))
    equipe_ok = bool(resumo.get("equipe")) and str(resumo.get("equipe")).strip() not in {"-", "N/D", "None"}
    area_ok = bool(resumo.get("area_local")) and str(resumo.get("area_local")).strip() not in {"-", "N/D", "None"}
    semana_ok = bool(contexto.get("semana"))

    colaboradores = resumo.get("colaboradores") or 0
    try:
        colaboradores = int(colaboradores)
    except Exception:
        colaboradores = 0

    score = 0
    if tem_contexto_minimo:
        score += 1
    if total_atividades_sugeridas > 0:
        score += 1
    if equipe_ok and colaboradores > 0:
        score += 1
    if semana_ok and perfil_ok:
        score += 1

    alertas = []

    if not tem_contexto_minimo:
        alertas.append("Faltam dados mínimos para uma montagem guiada confiável.")
    if total_atividades_sugeridas == 0:
        alertas.append("Nenhuma atividade sugerida foi encontrada para a referência informada.")
    if not semana_ok:
        alertas.append("Semana de planejamento não identificada para a data informada.")
    if not perfil_ok:
        alertas.append("Perfil operacional do usuário não está configurado.")
    if not equipe_ok:
        alertas.append("Equipe sugerida não foi identificada automaticamente.")
    if not area_ok:
        alertas.append("Área operacional não foi identificada automaticamente.")
    if colaboradores <= 0:
        alertas.append("Nenhum colaborador válido foi encontrado para o dia.")

    if score <= 1:
        nivel = "danger"
        rotulo = "Contexto insuficiente"
        mensagem = "Montagem não recomendada"
    elif score <= 3:
        nivel = "warning"
        rotulo = "Atenção"
        mensagem = "Montagem possível com ajustes"
    else:
        nivel = "success"
        rotulo = "Pronto"
        mensagem = "Pronto para montagem"

    return {
        "score": score,
        "nivel": nivel,
        "rotulo": rotulo,
        "mensagem": mensagem,
        "alertas": alertas,
        "tem_contexto_minimo": tem_contexto_minimo,
        "total_atividades_sugeridas": total_atividades_sugeridas,
        "perfil_ok": perfil_ok,
        "equipe_ok": equipe_ok,
        "area_ok": area_ok,
        "semana_ok": semana_ok,
        "resumo": resumo,
    }


