from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.mobile_views import MobileHomeView

urlpatterns = [
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
