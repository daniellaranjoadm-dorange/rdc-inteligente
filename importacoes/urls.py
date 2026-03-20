from django.urls import path
from importacoes.views import ImportacaoCreateView, ImportacoesHomeView

urlpatterns = [
    path("", ImportacoesHomeView.as_view(), name="importacoes-home"),
    path("nova/", ImportacaoCreateView.as_view(), name="importacoes-create"),
]
