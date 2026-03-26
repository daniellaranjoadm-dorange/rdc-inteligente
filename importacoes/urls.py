from django.urls import path
from .views import (
    ImportacoesHomeView,
    ImportacaoCreateView,
    download_modelo_funcionarios,
    download_erros_importacao,
    ImportacoesMobileView,
)

urlpatterns = [
    path("", ImportacoesHomeView.as_view(), name="importacoes-home"),
    path("nova/", ImportacaoCreateView.as_view(), name="importacoes-create"),
    path("modelo/", download_modelo_funcionarios, name="download_modelo_funcionarios"),
    path("erros/<int:pk>/", download_erros_importacao, name="download_erros_importacao"),

    # 🔥 MOBILE
    path("mobile/", ImportacoesMobileView.as_view(), name="importacoes-mobile"),
]

