from rest_framework.permissions import BasePermission


class PerfilRolePermission(BasePermission):
    """
    Exige usuário autenticado + PerfilAcesso.
    Se a view definir:
      - allowed_roles = [...]
      - allowed_roles_by_method = {"GET": [...], "POST": [...]}
    a permissão será aplicada por papel.
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True

        perfil = getattr(user, "perfil_acesso", None)
        if not perfil:
            return False

        roles_map = getattr(view, "allowed_roles_by_method", None) or {}
        allowed_roles = roles_map.get(request.method) or roles_map.get("*")

        if allowed_roles is None:
            allowed_roles = getattr(view, "allowed_roles", None)

        if not allowed_roles:
            return True

        return perfil.role in allowed_roles


class MobileApiPermission(PerfilRolePermission):
    pass


