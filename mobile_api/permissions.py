from rest_framework.permissions import IsAuthenticated


class MobileApiPermission(IsAuthenticated):
    """
    Ponto central para futuras regras de permissão do app mobile.
    """
    pass

