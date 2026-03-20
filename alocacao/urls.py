from django.urls import path
from alocacao.views import AlocacaoHomeView
urlpatterns = [path("", AlocacaoHomeView.as_view(), name="alocacao-home")]
