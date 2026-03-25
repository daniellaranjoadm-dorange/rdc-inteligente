from django.shortcuts import render


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
    contexto = FORBIDDEN_MESSAGES.get(code, FORBIDDEN_MESSAGES["forbidden"]).copy()
    contexto["code"] = code
    return render(request, "403.html", contexto, status=403)
