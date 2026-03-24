from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("rdc/", include("rdc.urls")),
    path("importacoes/", include("importacoes.urls")),
    path("cadastros/", include("cadastros.urls")),
    path("api/mobile/", include("mobile_api.urls")),
    path("api/", include("core.api_urls")),
]

handler403 = 'core.views.handler403'

