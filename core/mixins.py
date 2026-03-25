from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class AuthenticatedTemplateMixin(LoginRequiredMixin):
    login_url = "/accounts/login/"
    redirect_field_name = "next"


class RoleRequiredMixin:
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        perfil = getattr(request.user, "perfil_acesso", None)

        if not perfil:
            raise PermissionDenied("Usuário sem perfil operacional definido.")

        if self.allowed_roles and perfil.role not in self.allowed_roles:
            raise PermissionDenied("Você não tem permissão para acessar esta funcionalidade.")

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
            raise PermissionDenied("RDC está fechado e não pode ser alterado.")

        return super().dispatch(request, *args, **kwargs)




