from django.shortcuts import render


def erro_403(request, exception):
    mensagem = str(exception) if exception else "Você não tem permissão para acessar esta área."

    contexto = {
        "mensagem": mensagem,
    }

    return render(request, "403.html", contexto, status=403)

