from django.urls import path

from rdc.views import (
    RDCValidacoesView,
    RDCImportarFuncionariosAlocacaoView,
    
    RDCImportarAtividadesCronogramaView,
    RDCNestedDeleteView,
    
    RDCWorkflowView,
    RDCAtividadeBuscaView,
    RDCFuncionarioBuscaView,
    RDCAuditoriaExportView,
    RDCListView,
    RDCDetailView,
    RDCUpdateView,
    RDCDeleteView,
    RDCConsolidadoView,
    RDCConsolidadoExportView,
    RDCExportView,
    RDCExportarModeloView,
    RDCRevalidarView,
    RDCAtividadeCreateView,
    RDCAtividadeUpdateView,
    RDCAtividadeInlineUpdateView,
    RDCAtividadeLoteView,
    RDCFuncionarioInlineUpdateView,
    RDCFuncionarioLoteView,
    RDCApontamentoInlineUpdateView,
    RDCApontamentoLoteView,
    RDCValidacaoInlineUpdateView,
    RDCValidacaoLoteView,
)

urlpatterns = [

    # ===== BASE =====
    path("", RDCListView.as_view(), name="rdc-list"),
    path("<int:pk>/", RDCDetailView.as_view(), name="rdc-detail"),

    # ===== RDC =====
    path("<int:pk>/editar/", RDCUpdateView.as_view(), name="rdc-update"),
    path("<int:pk>/excluir/", RDCDeleteView.as_view(), name="rdc-delete"),

    # ===== CONSOLIDADO =====
    path("consolidado/", RDCConsolidadoView.as_view(), name="rdc-consolidado"),
    path("consolidado/exportar/<str:tipo>/", RDCConsolidadoExportView.as_view(), name="rdc-consolidado-export"),

    # ===== EXPORT =====
    path("<int:pk>/exportar/<str:tipo>/", RDCExportView.as_view(), name="rdc-export"),
    path("<int:pk>/exportar-modelo/", RDCExportarModeloView.as_view(), name="rdc-exportar-modelo"),

    # ===== REVALIDAR =====
    path("<int:pk>/revalidar/", RDCRevalidarView.as_view(), name="rdc-revalidar"),

    # ===== ATIVIDADES =====
    path("<int:pk>/atividades/novo/", RDCAtividadeCreateView.as_view(), name="rdc-atividade-create"),
    path("<int:pk>/atividades/<int:pk2>/editar/", RDCAtividadeUpdateView.as_view(), name="rdc-atividade-update"),
    path("<int:pk>/atividades/<int:pk2>/inline-update/", RDCAtividadeInlineUpdateView.as_view(), name="rdc-atividade-inline-update"),
    path("<int:pk>/atividades/lote/", RDCAtividadeLoteView.as_view(), name="rdc-atividade-lote"),

    # ===== FUNCIONARIOS =====
    path("<int:pk>/funcionarios/<int:pk2>/inline-update/", RDCFuncionarioInlineUpdateView.as_view(), name="rdc-funcionario-inline-update"),
    path("<int:pk>/funcionarios/lote/", RDCFuncionarioLoteView.as_view(), name="rdc-funcionario-lote"),

    # ===== APONTAMENTOS =====
    path("<int:pk>/apontamentos/<int:pk2>/inline-update/", RDCApontamentoInlineUpdateView.as_view(), name="rdc-apontamento-inline-update"),
    path("<int:pk>/apontamentos/lote/", RDCApontamentoLoteView.as_view(), name="rdc-apontamento-lote"),

    # ===== VALIDACOES =====
    path("<int:pk>/validacoes/<int:pk2>/inline-update/", RDCValidacaoInlineUpdateView.as_view(), name="rdc-validacao-inline-update"),
    path("<int:pk>/validacoes/lote/", RDCValidacaoLoteView.as_view(), name="rdc-validacao-lote"),
]


# ===== BUSCAS =====
urlpatterns += [
    path("<int:pk>/buscar-atividades/", RDCAtividadeBuscaView.as_view(), name="rdc-atividade-busca"),
    path("<int:pk>/buscar-funcionarios/", RDCFuncionarioBuscaView.as_view(), name="rdc-funcionario-busca"),
]

# ===== AUDITORIA =====
urlpatterns += [
    path("<int:pk>/auditoria/exportar/", RDCAuditoriaExportView.as_view(), name="rdc-auditoria-exportar"),
]

# ===== APONTAMENTO CREATE (compatibilidade) =====
urlpatterns += [
    path("<int:pk>/apontamentos/novo/", RDCApontamentoLoteView.as_view(), name="rdc-apontamento-create"),
]


# ===== DELETE =====
urlpatterns += [
    ]

# ===== WORKFLOW =====
urlpatterns += [
    path("<int:pk>/workflow/", RDCWorkflowView.as_view(), name="rdc-workflow"),
]


urlpatterns += [
    path("<int:pk>/atividade/<int:pk2>/delete/", RDCNestedDeleteView.as_view(), name="rdc-atividade-delete"),
]


urlpatterns += [
    path("<int:pk>/importar-atividades-cronograma/", RDCImportarAtividadesCronogramaView.as_view(), name="rdc-importar-atividades-cronograma"),
]


urlpatterns += [
    ]


urlpatterns += [
    path("<int:pk>/funcionarios/novo/", RDCFuncionarioLoteView.as_view(), name="rdc-funcionario-create"),
]


urlpatterns += [
    path("<int:pk>/funcionarios/importar/", RDCImportarFuncionariosAlocacaoView.as_view(), name="rdc-importar-funcionarios-alocacao"),
]


urlpatterns += [
    path("<int:pk>/validacoes/novo/", RDCValidacaoLoteView.as_view(), name="rdc-validacao-create"),
]


urlpatterns += [
    path("<int:pk>/validacoes/", RDCValidacoesView.as_view(), name="rdc-validacoes"),
]
