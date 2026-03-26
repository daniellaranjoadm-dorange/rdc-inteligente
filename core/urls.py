from django.urls import path

from core.views import DashboardView
from core.views_importacao import ImportFuncionariosView

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("importar/funcionarios/", ImportFuncionariosView.as_view(), name="import-funcionarios"),
]

