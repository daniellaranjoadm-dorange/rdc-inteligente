
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

from django.views.generic import TemplateView

urlpatterns = [
    path('manifest.json', manifest_view),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=False)),
    path("offline/", TemplateView.as_view(template_name="offline.html")),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("admin/", admin.site.urls),

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




