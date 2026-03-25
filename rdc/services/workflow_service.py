
from __future__ import annotations

from typing import Any

from django.db import connection, transaction
from django.utils import timezone

from rdc.models import RDC


def _audit_schema_ok() -> bool:
    try:
        return "rdc_rdcauditoria" in connection.introspection.table_names()
    except Exception:
        return False


def _registrar_auditoria(rdc, user, acao: str, resumo: str, detalhe: str = "", secao: str = "workflow") -> None:
    if not _audit_schema_ok():
        return
    try:
        from rdc.models import RDCAuditoria

        RDCAuditoria.objects.create(
            rdc=rdc,
            usuario=user if getattr(user, "is_authenticated", False) else None,
            acao=acao,
            secao=secao,
            resumo=resumo[:255],
            detalhe=detalhe or "",
        )
    except Exception:
        return


def process_rdc_workflow_action(rdc: RDC, *, action: str, user=None, observacao: str = "") -> dict[str, Any]:
    action = (action or "").strip().lower()
    observacao = (observacao or "").strip()

    with transaction.atomic():
        if action == "enviar_revisao":
            if not rdc.usuario_pode_enviar_revisao(user):
                return {"ok": False, "level": "warning", "message": "RDC não pode ser enviado para revisão no status atual."}
            rdc.status = "em_revisao"
            rdc.save(update_fields=["status", "updated_at", "sync_updated_at"])
            _registrar_auditoria(rdc, user, "enviar_revisao", "RDC enviado para revisão.", observacao)

        elif action == "aprovar":
            if not rdc.usuario_pode_aprovar(user):
                return {"ok": False, "level": "warning", "message": "Usuário sem permissão para aprovar este RDC."}
            rdc.status = "aprovado"
            rdc.save(update_fields=["status", "updated_at", "sync_updated_at"])
            _registrar_auditoria(rdc, user, "aprovar", "RDC aprovado.", observacao)

        elif action == "devolver":
            if not rdc.usuario_pode_devolver(user):
                return {"ok": False, "level": "warning", "message": "Usuário sem permissão para devolver este RDC."}
            rdc.status = "rascunho"
            if hasattr(rdc, "fechado_em"):
                rdc.fechado_em = None
            if hasattr(rdc, "fechado_por"):
                rdc.fechado_por = None
            rdc.save()
            _registrar_auditoria(rdc, user, "devolver", "RDC devolvido para elaborAção.", observacao)

        elif action == "reabrir":
            if not rdc.usuario_pode_reabrir(user):
                return {"ok": False, "level": "warning", "message": "Usuário sem permissão para reabrir este RDC."}
            rdc.status = "rascunho"
            if hasattr(rdc, "fechado_em"):
                rdc.fechado_em = None
            if hasattr(rdc, "fechado_por"):
                rdc.fechado_por = None
            rdc.save()
            _registrar_auditoria(rdc, user, "reabrir", "RDC reaberto.", observacao)

        elif action == "fechar":
            if not rdc.usuario_pode_fechar(user):
                return {"ok": False, "level": "warning", "message": "Usu?rio sem permiss?o para fechar este RDC."}

            bloqueios = rdc.validacoes.filter(status="bloqueio").count()
            if bloqueios and not rdc.usuario_pode_forcar_fechamento(user):
                return {"ok": False, "level": "warning", "message": "Existem bloqueios ativos. Somente usu?rio autorizado pode for?ar o fechamento."}

            rdc.status = "fechado"
            if hasattr(rdc, "fechado_em"):
                rdc.fechado_em = timezone.now()
            if hasattr(rdc, "fechado_por") and getattr(user, "is_authenticated", False):
                rdc.fechado_por = user
            rdc.save()
            _registrar_auditoria(rdc, user, "fechar", "RDC fechado.", observacao)

        else:
            return {"ok": False, "level": "warning", "message": "Ação de workflow inválida."}

    messages = {
        "enviar_revisao": "RDC enviado para revisão.",
        "aprovar": "RDC aprovado com sucesso.",
        "devolver": "RDC devolvido para elaborAção.",
        "reabrir": "RDC reaberto com sucesso.",
        "fechar": "RDC fechado com sucesso.",
    }
    return {"ok": True, "level": "success", "message": messages[action]}


