from django.shortcuts import redirect


def home_login(request):
    """Raiz do site: logado vai para o app; visitante vai para a tela de login unica."""
    if request.user.is_authenticated:
        return redirect("/m/")
    return redirect("/accounts/login/?next=/m/")
