"""Demonstração pública do RDC Inteligente.

- Na instância de demonstração (DJANGO_DEMO=1): /demo/entrar/ abre o sistema sem senha com o usuário
  "visitante"; tudo é somente leitura (nenhum POST/PUT/DELETE grava) e o admin fica fechado.
- Na instância principal: /demo/ só redireciona para o endereço da demonstração (DEMO_URL).
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render

USUARIO_DEMO = "visitante"
LIBERADOS = ("/accounts/login/", "/accounts/logout/", "/demo/entrar/")


def demo_ativo():
    return getattr(settings, "DEMO_MODE", False)


def contexto_demo(request):
    return {"DEMO_MODE": demo_ativo()}


class DemoSomenteLeituraMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not demo_ativo():
            return self.get_response(request)
        caminho = request.path
        if caminho.startswith("/admin/"):
            return redirect("/rdc/blocos/")
        if request.method not in ("GET", "HEAD", "OPTIONS") and not caminho.startswith(LIBERADOS):
            mensagem = "Esta é uma demonstração somente leitura: nada é gravado. Fale com a D'OR@NGE para ter o seu ambiente."
            if caminho.startswith("/api/") or request.headers.get("X-Envio-Offline"):
                return JsonResponse({"ok": False, "erro": mensagem}, status=403)
            messages.info(request, mensagem)
            return HttpResponseRedirect(request.META.get("HTTP_REFERER") or "/rdc/blocos/")
        return self.get_response(request)


def entrar_demo(request):
    """Só existe na instância de demonstração: entra sem senha como visitante (somente leitura)."""
    if not demo_ativo():
        raise Http404
    User = get_user_model()
    usuario, criado = User.objects.get_or_create(username=USUARIO_DEMO, defaults={
        "first_name": "Visitante", "is_staff": False, "is_superuser": True})
    if criado:
        usuario.set_unusable_password()
        usuario.save()
    login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
    return redirect(request.GET.get("next") if (request.GET.get("next") or "").startswith("/") else "/rdc/blocos/")


def ir_para_demo(request):
    """Na instância principal: endereço fixo divulgado no site, que leva à demonstração."""
    if demo_ativo():
        return redirect("/demo/entrar/")
    destino = getattr(settings, "DEMO_URL", "")
    if destino:
        return HttpResponseRedirect(destino.rstrip("/") + "/demo/entrar/")
    return render(request, "demo_indisponivel.html", status=503)
