from django.urls import path
from rdc.views import *
from rdc.views import RDCApontamentoCreateView
from rdc.views_foto import (
    RDCFotoArquivoView, RDCFotoDeleteView, RDCFotoUpdateView, RDCFotoUploadView, RDCRelatorioFotograficoView,
)
from rdc.views_aceite import (
    RDCAceiteAssinaturaView, RDCComprovanteAceiteView, RDCGerarLinkAceiteView, RDCRevogarLinkAceiteView,
)
from rdc.views_copiar import RDCCopiarView
from rdc.views_email import RDCEnviarEmailView, RDCPdfView
from rdc.views_hh import PainelHHView
from rdc.views_registros import (
    RDCEquipamentoCreateView, RDCEquipamentoDeleteView, RDCEquipamentoUpdateView,
    RDCOcorrenciaCreateView, RDCOcorrenciaDeleteView, RDCOcorrenciaUpdateView,
)
from rdc.views_paralisacao import RDCParalisacaoCreateView, RDCParalisacaoDeleteView, RDCParalisacaoUpdateView

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

# ===== PARALISAÇÕES =====
paralisacao_patterns = [
    path("<int:pk>/paralisacoes/nova/", RDCParalisacaoCreateView.as_view(), name="rdc-paralisacao-create"),
    path("<int:pk>/paralisacoes/<int:pk2>/editar/", RDCParalisacaoUpdateView.as_view(), name="rdc-paralisacao-update"),
    path("<int:pk>/paralisacoes/<int:pk2>/excluir/", RDCParalisacaoDeleteView.as_view(), name="rdc-paralisacao-delete"),
]

# ===== FOTOS =====
foto_patterns = [
    path("<int:pk>/fotos/enviar/", RDCFotoUploadView.as_view(), name="rdc-foto-upload"),
    path("<int:pk>/fotos/<int:pk2>/editar/", RDCFotoUpdateView.as_view(), name="rdc-foto-update"),
    path("<int:pk>/fotos/<int:pk2>/excluir/", RDCFotoDeleteView.as_view(), name="rdc-foto-delete"),
    path("<int:pk>/fotos/<int:pk2>/arquivo/", RDCFotoArquivoView.as_view(), name="rdc-foto-arquivo"),
    path("<int:pk>/fotos/<int:pk2>/miniatura/", RDCFotoArquivoView.as_view(), {"tamanho": "mini"}, name="rdc-foto-miniatura"),
    path("<int:pk>/fotos/relatorio.pdf", RDCRelatorioFotograficoView.as_view(), name="rdc-relatorio-fotografico"),
]

# ===== ACEITE DO FISCAL =====
aceite_patterns = [
    path("<int:pk>/aceite/link/", RDCGerarLinkAceiteView.as_view(), name="rdc-aceite-gerar-link"),
    path("<int:pk>/aceite/link/<int:link_id>/revogar/", RDCRevogarLinkAceiteView.as_view(), name="rdc-aceite-revogar-link"),
    path("<int:pk>/aceite/<int:aceite_id>/assinatura.png", RDCAceiteAssinaturaView.as_view(), name="rdc-aceite-assinatura"),
    path("<int:pk>/aceite/<int:aceite_id>/comprovante.pdf", RDCComprovanteAceiteView.as_view(), name="rdc-aceite-comprovante"),
]

# ===== EQUIPAMENTOS E OCORRENCIAS =====
registro_patterns = [
    path("<int:pk>/equipamentos/novo/", RDCEquipamentoCreateView.as_view(), name="rdc-equipamento-create"),
    path("<int:pk>/equipamentos/<int:pk2>/editar/", RDCEquipamentoUpdateView.as_view(), name="rdc-equipamento-update"),
    path("<int:pk>/equipamentos/<int:pk2>/excluir/", RDCEquipamentoDeleteView.as_view(), name="rdc-equipamento-delete"),
    path("<int:pk>/ocorrencias/nova/", RDCOcorrenciaCreateView.as_view(), name="rdc-ocorrencia-create"),
    path("<int:pk>/ocorrencias/<int:pk2>/editar/", RDCOcorrenciaUpdateView.as_view(), name="rdc-ocorrencia-update"),
    path("<int:pk>/ocorrencias/<int:pk2>/excluir/", RDCOcorrenciaDeleteView.as_view(), name="rdc-ocorrencia-delete"),
    path("<int:pk>/pdf/", RDCPdfView.as_view(), name="rdc-pdf"),
    path("<int:pk>/copiar/", RDCCopiarView.as_view(), name="rdc-copiar"),
    path("<int:pk>/enviar-email/", RDCEnviarEmailView.as_view(), name="rdc-enviar-email"),
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
    path("hh/", PainelHHView.as_view(), name="rdc-painel-hh"),
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
    + paralisacao_patterns
    + foto_patterns
    + aceite_patterns
    + registro_patterns
    + validacao_patterns
    + extra_patterns
)


