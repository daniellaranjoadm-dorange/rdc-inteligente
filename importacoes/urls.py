from django.urls import path
from importacoes.views import download_modelo_funcionarios,  ImportacaoCreateView, ImportacoesHomeView

urlpatterns = [
    path('modelo/funcionarios/', download_modelo_funcionarios, name='download_modelo_funcionarios'),
    path("", ImportacoesHomeView.as_view(), name="importacoes-home"),
    path("nova/", ImportacaoCreateView.as_view(), name="importacoes-create"),
]

