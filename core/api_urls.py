from django.urls import path
from rest_framework.routers import DefaultRouter

from cadastros.api import AreaLocalViewSet, DisciplinaViewSet, EquipeViewSet, FuncionarioViewSet, ProjetoViewSet
from rdc.api import RDCAtividadeViewSet, RDCFuncionarioViewSet, RDCMontagemAPIView, RDCValidacaoViewSet, RDCViewSet

router = DefaultRouter()
router.register("projetos", ProjetoViewSet, basename="api-projetos")
router.register("disciplinas", DisciplinaViewSet, basename="api-disciplinas")
router.register("areas", AreaLocalViewSet, basename="api-areas")
router.register("funcionarios", FuncionarioViewSet, basename="api-funcionarios")
router.register("equipes", EquipeViewSet, basename="api-equipes")
router.register("rdcs", RDCViewSet, basename="api-rdcs")
router.register("rdc-atividades", RDCAtividadeViewSet, basename="api-rdc-atividades")
router.register("rdc-funcionarios", RDCFuncionarioViewSet, basename="api-rdc-funcionarios")
router.register("rdc-validacoes", RDCValidacaoViewSet, basename="api-rdc-validacoes")

urlpatterns = router.urls + [
    path("rdc/montar/", RDCMontagemAPIView.as_view(), name="api-rdc-montar"),
]
