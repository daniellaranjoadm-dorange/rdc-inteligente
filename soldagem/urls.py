from django.urls import path

from soldagem import views as v

urlpatterns = [
    path("", v.PainelSoldaView.as_view(), name="solda-painel"),
    path("juntas/", v.JuntaListView.as_view(), name="solda-juntas"),
    path("juntas/nova/", v.JuntaCreateView.as_view(), name="solda-junta-create"),
    path("juntas/<int:pk>/", v.JuntaDetailView.as_view(), name="solda-junta-detail"),
    path("juntas/<int:pk>/editar/", v.JuntaUpdateView.as_view(), name="solda-junta-update"),
    path("juntas/<int:pk>/soldar/", v.RegistrarSoldaView.as_view(), name="solda-registrar"),
    path("end/<int:pk>/resultado/", v.ResultadoENDView.as_view(), name="solda-end-resultado"),
    path("soldadores/", v.SoldadorListView.as_view(), name="solda-soldadores"),
    path("soldadores/novo/", v.SoldadorCreateView.as_view(), name="solda-soldador-create"),
    path("soldadores/<int:pk>/editar/", v.SoldadorUpdateView.as_view(), name="solda-soldador-update"),
    path("eps/", v.EPSListView.as_view(), name="solda-eps"),
    path("eps/nova/", v.EPSCreateView.as_view(), name="solda-eps-create"),
    path("eps/<int:pk>/editar/", v.EPSUpdateView.as_view(), name="solda-eps-update"),
]
