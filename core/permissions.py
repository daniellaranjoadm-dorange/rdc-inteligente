from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionCode:
    code: str
    description: str


PERMISSION_CODES = {
    "forbidden": PermissionCode(
        code="forbidden",
        description="Acesso negado genérico.",
    ),
    "missing_profile": PermissionCode(
        code="missing_profile",
        description="Usuário sem perfil operacional configurado.",
    ),
    "insufficient_role": PermissionCode(
        code="insufficient_role",
        description="Usuário com papel insuficiente para a ação.",
    ),
    "rdc_closed": PermissionCode(
        code="rdc_closed",
        description="Tentativa de alteração em RDC fechado.",
    ),
    "permission_denied": PermissionCode(
        code="permission_denied",
        description="Usuário sem a permissão específica exigida.",
    ),
}
