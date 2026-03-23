
from django.core.exceptions import PermissionDenied
from accounts.models import PerfilAcesso


class RDCMutationGuardMixin:
    allowed_roles = {"supervisor"}

    def get_rdc(self):
        raise NotImplementedError("A view precisa implementar get_rdc()")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied

        try:
            perfil = PerfilAcesso.objects.get(user=request.user)
        except PerfilAcesso.DoesNotExist:
            raise PermissionDenied

        if perfil.role not in self.allowed_roles:
            raise PermissionDenied

        rdc = self.get_rdc()
        if rdc.status == "fechado":
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)
