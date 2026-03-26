from django.core.exceptions import PermissionDenied


class ContextualPermissionDenied(PermissionDenied):
    """
    Exceção de permissão com contexto estruturado.
    Usada para alimentar o handler 403 com mensagens inteligentes.
    """

    def __init__(self, code="forbidden", message="Acesso negado."):
        self.code = code
        super().__init__(message)

