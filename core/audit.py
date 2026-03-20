from accounts.models import AuditLog


def registrar_auditoria(user, action, target_model="", target_id="", detail=""):
    AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        target_model=target_model or "",
        target_id=str(target_id or ""),
        detail=detail or "",
    )
