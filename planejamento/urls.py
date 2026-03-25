from django.urls import path
from planejamento.views import PlanejamentoHomeView
urlpatterns = [path("", PlanejamentoHomeView.as_view(), name="planejamento-home")]

