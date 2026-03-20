from django.urls import path
from relatorios.views import RelatoriosHomeView

urlpatterns = [path("", RelatoriosHomeView.as_view(), name="relatorios-home")]
