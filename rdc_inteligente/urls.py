from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("rdc/", include("rdc.urls")),
    path("importacoes/", include("importacoes.urls")),
    path("cadastros/", include("cadastros.urls")),
    path("api/mobile/", include("mobile_api.urls")),
    path("api/", include("core.api_urls")),
]
