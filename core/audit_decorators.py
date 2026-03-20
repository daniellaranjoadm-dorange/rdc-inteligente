from functools import wraps
from core.audit import registrar_auditoria


def audit_action(action, target_model="RDC", get_target_id=None, detail_func=None):
    """
    Decorator para registrar auditoria automaticamente.

    - action: nome da ação (string)
    - get_target_id: função que recebe (self, request, *args, **kwargs)
                     e retorna o id do objeto
    - detail_func: função que retorna texto detalhado
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            response = func(self, request, *args, **kwargs)

            try:
                target_id = None
                if get_target_id:
                    target_id = get_target_id(self, request, *args, **kwargs)

                detail = ""
                if detail_func:
                    detail = detail_func(self, request, *args, **kwargs)

                registrar_auditoria(
                    user=request.user,
                    action=action,
                    target_model=target_model,
                    target_id=target_id,
                    detail=detail,
                )
            except Exception:
                # nunca quebrar fluxo por auditoria
                pass

            return response

        return wrapper

    return decorator
