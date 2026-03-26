from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    MobileImportacaoListAPIView,
    BaseOperacionalAPIView,
    MeAPIView,
    MobileRDCAtividadeListCreateAPIView,
    MobileRDCAtividadeRetrieveUpdateDestroyAPIView,
    MobileRDCApontamentoListCreateAPIView,
    MobileRDCApontamentoRetrieveUpdateDestroyAPIView,
    MobileRDCDetailAPIView,
    MobileRDCFuncionarioListCreateAPIView,
    MobileRDCFuncionarioRetrieveUpdateDestroyAPIView,
    MobileRDCListCreateAPIView,
    MobileRDCRetrieveUpdateDestroyAPIView,
    MobileSyncAPIView,
)

urlpatterns = [
    path("token/", TokenObtainPairView.as_view(), name="mobile-token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="mobile-token-refresh"),
    path("me/", MeAPIView.as_view(), name="mobile-me"),
    path("base-operacional/", BaseOperacionalAPIView.as_view(), name="mobile-base-operacional"),
    path("sync/", MobileSyncAPIView.as_view(), name="mobile-sync"),
    path("rdcs/", MobileRDCListCreateAPIView.as_view(), name="mobile-rdc-list-create"),
    path("rdcs/<int:pk>/", MobileRDCRetrieveUpdateDestroyAPIView.as_view(), name="mobile-rdc-detail-rud"),
    path("rdcs/<int:pk>/detalhe/", MobileRDCDetailAPIView.as_view(), name="mobile-rdc-detail"),
    path("rdcs/<int:pk>/funcionarios/", MobileRDCFuncionarioListCreateAPIView.as_view(), name="mobile-rdc-funcionarios"),
    path("rdcs/<int:pk>/funcionarios/<int:item_pk>/", MobileRDCFuncionarioRetrieveUpdateDestroyAPIView.as_view(), name="mobile-rdc-funcionario-rud"),
    path("rdcs/<int:pk>/atividades/", MobileRDCAtividadeListCreateAPIView.as_view(), name="mobile-rdc-atividades"),
    path("rdcs/<int:pk>/atividades/<int:item_pk>/", MobileRDCAtividadeRetrieveUpdateDestroyAPIView.as_view(), name="mobile-rdc-atividade-rud"),
    path("rdcs/<int:pk>/apontamentos/", MobileRDCApontamentoListCreateAPIView.as_view(), name="mobile-rdc-apontamentos"),
    path("rdcs/<int:pk>/apontamentos/<int:item_pk>/", MobileRDCApontamentoRetrieveUpdateDestroyAPIView.as_view(), name="mobile-rdc-apontamento-rud"),
    path("importacoes/", MobileImportacaoListAPIView.as_view(), name="mobile-importacoes"),
]
