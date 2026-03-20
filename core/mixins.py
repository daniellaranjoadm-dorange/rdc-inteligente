from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class AuthenticatedTemplateMixin(LoginRequiredMixin):
    login_url = "/accounts/login/"
    redirect_field_name = "next"


class RoleRequiredMixin:
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        perfil = getattr(request.user, "perfil_acesso", None)

        if not perfil:
            raise PermissionDenied("Usuário sem perfil de acesso definido.")

        if self.allowed_roles and perfil.role not in self.allowed_roles:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")

        return super().dispatch(request, *args, **kwargs)