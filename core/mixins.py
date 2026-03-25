from django.contrib.auth.mixins import LoginRequiredMixin

from core.exceptions import ContextualPermissionDenied


class AuthenticatedTemplateMixin(LoginRequiredMixin):
    raise_exception = True
    login_url = "/accounts/login/"
    redirect_field_name = "next"


class RoleRequiredMixin:
    allowed_roles = []
    required_permission = None

    def _get_profile_permissions(self, perfil):
        permissions = getattr(perfil, "permissions", None)
        if permissions is None:
            permissions = getattr(perfil, "permissoes", None)

        if permissions is None:
            return set()

        if isinstance(permissions, str):
            return {permissions}

        try:
            return set(permissions)
        except TypeError:
            return set()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        perfil = getattr(request.user, "perfil_acesso", None)

        if not perfil:
            raise ContextualPermissionDenied(
                code="missing_profile",
                message="Usuário sem perfil operacional definido.",
            )

        if self.allowed_roles and perfil.role not in self.allowed_roles:
            raise ContextualPermissionDenied(
                code="insufficient_role",
                message="Você não tem permissão para acessar esta funcionalidade.",
            )

        if self.required_permission:
            permissions = self._get_profile_permissions(perfil)
            if self.required_permission not in permissions:
                raise ContextualPermissionDenied(
                    code="permission_denied",
                    message="Seu perfil não possui a permissão necessária para executar esta ação.",
                )

        return super().dispatch(request, *args, **kwargs)


class RDCEditableMixin:
    """
    Bloqueia alterações se o RDC estiver fechado.
    Prioridade:
    1. self.rdc
    2. self.get_object()
    3. obj.rdc
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        rdc = getattr(self, "rdc", None)
        obj = None

        if not rdc and hasattr(self, "get_object"):
            try:
                obj = self.get_object()
            except Exception:
                obj = None

            if obj is not None:
                if getattr(obj, "is_fechado", False):
                    rdc = obj
                elif hasattr(obj, "rdc"):
                    rdc = getattr(obj, "rdc", None)

        if rdc and getattr(rdc, "is_fechado", False):
            raise ContextualPermissionDenied(
                code="rdc_closed",
                message="RDC está fechado e não pode ser alterado.",
            )

        return super().dispatch(request, *args, **kwargs)


    def handle_no_permission(self):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
