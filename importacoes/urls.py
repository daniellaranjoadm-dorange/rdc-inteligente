from django.urls import path
from importacoes.views import download_erros_importacao,  download_modelo_funcionarios,  ImportacaoCreateView, ImportacoesHomeView

urlpatterns = [
    path('<int:pk>/erros/', download_erros_importacao, name='download_erros_importacao'),
    path('modelo/funcionarios/', download_modelo_funcionarios, name='download_modelo_funcionarios'),
    path("", ImportacoesHomeView.as_view(), name="importacoes-home"),
    path("nova/", ImportacaoCreateView.as_view(), name="importacoes-create"),
]

