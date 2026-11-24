from django.urls import path

from punchlist import views as v

urlpatterns = [
    path("", v.PunchPainelView.as_view(), name="punch-painel"),
    path("nova/", v.PunchCreateView.as_view(), name="punch-create"),
    path("<int:pk>/", v.PunchDetailView.as_view(), name="punch-detail"),
    path("<int:pk>/editar/", v.PunchUpdateView.as_view(), name="punch-update"),
    path("<int:pk>/<str:acao>/", v.PunchAcaoView.as_view(), name="punch-acao"),
    path("foto/<int:pk>/", v.PunchFotoView.as_view(), name="punch-foto"),
    path("foto/<int:pk>/mini/", v.PunchFotoView.as_view(), {"tamanho": "mini"}, name="punch-foto-mini"),
]
