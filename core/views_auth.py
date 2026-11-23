"""Login com bloqueio temporario apos varias senhas erradas."""
import hashlib

from django.contrib.auth import views as auth_views
from django.core.cache import cache

MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 15 * 60


def _ip(request):
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (encaminhado.split(",")[0].strip() if encaminhado else request.META.get("REMOTE_ADDR")) or "?"


def _chave(request):
    usuario = (request.POST.get("username") or "").strip().lower()
    bruto = f"{_ip(request)}|{usuario}".encode("utf-8")
    return "login_falhas:" + hashlib.sha256(bruto).hexdigest()


class LoginComBloqueioView(auth_views.LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        if cache.get(_chave(request), 0) >= MAX_TENTATIVAS:
            form = self.get_form()
            form.is_bound = True
            contexto = self.get_context_data(form=form, bloqueado=True)
            return self.render_to_response(contexto, status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        chave = _chave(self.request)
        tentativas = cache.get(chave, 0) + 1
        cache.set(chave, tentativas, BLOQUEIO_SEGUNDOS)
        return self.render_to_response(self.get_context_data(
            form=form, bloqueado=tentativas >= MAX_TENTATIVAS, restantes=max(MAX_TENTATIVAS - tentativas, 0),
        ))

    def form_valid(self, form):
        cache.delete(_chave(self.request))
        return super().form_valid(form)
