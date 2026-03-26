from django.urls import path
from rdc.views import *
from rdc.views import RDCApontamentoCreateView

# ===== BASE =====
base_patterns = [
    path("", RDCListView.as_view(), name="rdc-list"),
    path("<int:pk>/", RDCDetailView.as_view(), name="rdc-detail"),
    path("novo/", RDCMontagemView.as_view(), name="rdc-create"),  # legado
]

# ===== RDC CRUD =====
rdc_patterns = [
    path("<int:pk>/editar/", RDCUpdateView.as_view(), name="rdc-update"),
    path("<int:pk>/excluir/", RDCDeleteView.as_view(), name="rdc-delete"),
]

# ===== CONSOLIDADO =====
consolidado_patterns = [
    path("consolidado/", RDCConsolidadoView.as_view(), name="rdc-consolidado"),
    path("consolidado/exportar/<str:tipo>/", RDCConsolidadoExportView.as_view(), name="rdc-consolidado-export"),
]

# ===== EXPORT =====
export_patterns = [
    path("<int:pk>/exportar/<str:tipo>/", RDCExportView.as_view(), name="rdc-export"),
    path("<int:pk>/exportar-modelo/", RDCExportarModeloView.as_view(), name="rdc-exportar-modelo"),
    path("<int:pk>/auditoria/exportar/", RDCAuditoriaExportView.as_view(), name="rdc-auditoria-exportar"),
]

# ===== WORKFLOW =====
workflow_patterns = [
    path("<int:pk>/workflow/", RDCWorkflowView.as_view(), name="rdc-workflow"),
    path("<int:pk>/revalidar/", RDCRevalidarView.as_view(), name="rdc-revalidar"),
]

# ===== ATIVIDADES =====
atividade_patterns = [
    path("<int:pk>/atividades/novo/", RDCAtividadeCreateView.as_view(), name="rdc-atividade-create"),
    path("<int:pk>/atividades/<int:pk2>/editar/", RDCAtividadeUpdateView.as_view(), name="rdc-atividade-update"),
    path("<int:pk>/atividades/<int:pk2>/inline-update/", RDCAtividadeInlineUpdateView.as_view(), name="rdc-atividade-inline-update"),
    path("<int:pk>/atividades/lote/", RDCAtividadeLoteView.as_view(), name="rdc-atividade-lote"),
    path("<int:pk>/atividade/<int:pk2>/delete/", RDCNestedDeleteView.as_view(), name="rdc-atividade-delete"),
    path("<int:pk>/buscar-atividades/", RDCAtividadeBuscaView.as_view(), name="rdc-atividade-busca"),
    path("<int:pk>/importar-atividades-cronograma/", RDCImportarAtividadesCronogramaView.as_view(), name="rdc-importar-atividades-cronograma"),
]

# ===== FUNCIONÁRIOS =====
funcionario_patterns = [
    path("<int:pk>/funcionarios/novo/", RDCFuncionarioLoteView.as_view(), name="rdc-funcionario-create"),
    path("<int:pk>/funcionarios/<int:pk2>/inline-update/", RDCFuncionarioInlineUpdateView.as_view(), name="rdc-funcionario-inline-update"),
    path("<int:pk>/funcionarios/lote/", RDCFuncionarioLoteView.as_view(), name="rdc-funcionario-lote"),
    path("<int:pk>/funcionarios/importar/", RDCImportarFuncionariosAlocacaoView.as_view(), name="rdc-importar-funcionarios-alocacao"),
    path("<int:pk>/buscar-funcionarios/", RDCFuncionarioBuscaView.as_view(), name="rdc-funcionario-busca"),
]

# ===== APONTAMENTOS =====
apontamento_patterns = [
    path("<int:pk>/apontamentos/novo/", RDCApontamentoCreateView.as_view(), name="rdc-apontamento-create"),
    path("<int:pk>/apontamentos/<int:pk2>/inline-update/", RDCApontamentoInlineUpdateView.as_view(), name="rdc-apontamento-inline-update"),
    path("<int:pk>/apontamentos/lote/", RDCApontamentoLoteView.as_view(), name="rdc-apontamento-lote"),
]

# ===== VALIDAÇÕES =====
validacao_patterns = [
    path("<int:pk>/validacoes/", RDCValidacoesView.as_view(), name="rdc-validacoes"),
    path("<int:pk>/validacoes/novo/", RDCValidacaoLoteView.as_view(), name="rdc-validacao-create"),
    path("<int:pk>/validacoes/<int:pk2>/inline-update/", RDCValidacaoInlineUpdateView.as_view(), name="rdc-validacao-inline-update"),
    path("<int:pk>/validacoes/lote/", RDCValidacaoLoteView.as_view(), name="rdc-validacao-lote"),
]

# ===== DASHBOARD / RDO =====
extra_patterns = [
    path("dashboard/", RDCDashboardHomeView.as_view(), name="rdc-dashboard"),
    path("rdo/", RDOView.as_view(), name="rdc-rdo"),
    path("rdo/exportar/<str:tipo>/", RDOExportView.as_view(), name="rdc-rdo-exportar"),
]

# ===== FINAL =====
urlpatterns = (
    base_patterns
    + rdc_patterns
    + consolidado_patterns
    + export_patterns
    + workflow_patterns
    + atividade_patterns
    + funcionario_patterns
    + apontamento_patterns
    + validacao_patterns
    + extra_patterns
)


