
from django.http import HttpResponse
import json
from django.conf import settings
from pathlib import Path

def manifest_view(request):
    from django.conf import settings
    from pathlib import Path

    path = Path(settings.BASE_DIR) / "static" / "manifest.json"
    with open(path, encoding="utf-8") as f:
        return HttpResponse(f.read(), content_type="application/manifest+json")
from django.views.generic.base import RedirectView
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.mobile_views import MobileHomeView
from core.views_auth import LoginComBloqueioView
from rdc.views_aceite import AceitePublicoFotoView, AceitePublicoView
from rdc.views_tarefas import TarefaAlertasView

from django.views.generic import TemplateView

urlpatterns = [
    path('', include('core.urls')),
    path('manifest.json', manifest_view),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=False)),
    path("offline/", TemplateView.as_view(template_name="offline.html")),
    path("accounts/login/", LoginComBloqueioView.as_view(), name="login"),
    path("accounts/senha/esqueci/", auth_views.PasswordResetView.as_view(
        template_name="registration/senha_esqueci.html",
        email_template_name="registration/senha_email.txt",
        subject_template_name="registration/senha_assunto.txt",
    ), name="password_reset"),
    path("accounts/senha/enviado/", auth_views.PasswordResetDoneView.as_view(
        template_name="registration/senha_enviado.html"), name="password_reset_done"),
    path("accounts/senha/nova/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/senha_nova.html"), name="password_reset_confirm"),
    path("accounts/senha/pronto/", auth_views.PasswordResetCompleteView.as_view(
        template_name="registration/senha_pronto.html"), name="password_reset_complete"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="/accounts/login/"), name="logout"),
    path("admin/", admin.site.urls),

    # aceite do fiscal (link publico de uso unico, sem login)
    path("aceite/<str:token>/", AceitePublicoView.as_view(), name="aceite-publico"),
    path("aceite/<str:token>/foto/<int:foto_id>/", AceitePublicoFotoView.as_view(), name="aceite-publico-foto"),
    path("tarefas/alertas/", TarefaAlertasView.as_view(), name="tarefa-alertas"),

    # mobile app entry
    path("m/", MobileHomeView.as_view(), name="mobile-home"),

    # web apps
    path("", include("core.urls")),
    path("rdc/", include("rdc.urls")),
    path("importacoes/", include("importacoes.urls")),
    path("cadastros/", include("cadastros.urls")),

    # apis
    path("api/mobile/", include("mobile_api.urls")),
    path("api/", include("core.api_urls")),
]

handler403 = "core.error_views.erro_403"




