import logging

from django.shortcuts import render


logger = logging.getLogger(__name__)


FORBIDDEN_MESSAGES = {
    "missing_profile": {
        "titulo": "Perfil operacional não configurado",
        "mensagem": "Seu usuário ainda não possui perfil operacional ativo para executar esta ação.",
        "acao": "Solicite ao administrador a configuração do seu acesso.",
    },
    "insufficient_role": {
        "titulo": "Permissão insuficiente",
        "mensagem": "Seu perfil não possui permissão para acessar esta funcionalidade.",
        "acao": "Caso precise desse acesso, fale com o administrador do sistema.",
    },
    "permission_denied": {
        "titulo": "Permissão específica ausente",
        "mensagem": "Seu perfil não possui a permissão necessária para executar esta ação.",
        "acao": "Caso precise dessa permissão, solicite ajuste ao administrador do sistema.",
    },
    "rdc_closed": {
        "titulo": "RDC fechado",
        "mensagem": "Este RDC está fechado e não aceita novas alterações.",
        "acao": "Consulte um responsável caso seja necessário reabrir o fluxo.",
    },
    "forbidden": {
        "titulo": "Acesso negado",
        "mensagem": "Você não tem permissão para acessar esta área.",
        "acao": "Se isso parece incorreto, fale com o administrador do sistema.",
    },
}


def erro_403(request, exception=None):
    code = getattr(exception, "code", "forbidden")

    user = getattr(request, "user", None)
    user_id = getattr(user, "id", None)
    username = getattr(user, "username", None)

    logger.warning(
        "access_denied",
        extra={
            "event": "access_denied",
            "code": code,
            "path": request.path,
            "method": request.method,
            "user_id": user_id,
            "username": username,
        },
    )

    contexto = FORBIDDEN_MESSAGES.get(code, FORBIDDEN_MESSAGES["forbidden"]).copy()
    contexto["code"] = code
    return render(request, "403.html", contexto, status=403)


