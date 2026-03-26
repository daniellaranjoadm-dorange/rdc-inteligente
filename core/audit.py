from accounts.models import AuditLog


def registrar_auditoria(user, action, target_model="", target_id="", detail=""):
    AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        target_model=target_model or "",
        target_id=str(target_id or ""),
        detail=detail or "",
    )


def traduzir_acao_auditoria(action):
    mapa = {
        "exportar_rdc_modelo": "Exportou modelo Excel",
        "workflow_rdc": "Alterou workflow do RDC",
        "delete_rdc": "Excluiu RDC",
        "update_rdc": "Atualizou RDC",
        "create_rdc": "Criou RDC",
    }
    return mapa.get(action, str(action or "").replace("_", " ").title())


def cor_acao_auditoria(action):
    mapa = {
        "exportar_rdc_modelo": "secondary",
        "workflow_rdc": "primary",
        "delete_rdc": "danger",
        "update_rdc": "warning",
        "create_rdc": "success",
    }
    return mapa.get(action, "light")


