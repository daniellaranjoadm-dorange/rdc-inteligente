from django.contrib import admin

from alocacao.models import FuncionarioProjeto, HistogramaPlanejado

@admin.register(FuncionarioProjeto)
class FuncionarioProjetoAdmin(admin.ModelAdmin):
    list_display = ("funcionario", "projeto", "disciplina", "equipe", "data_inicio", "data_fim", "ativo")
    list_filter = ("ativo", "projeto", "disciplina", "equipe")
    search_fields = ("funcionario__nome", "funcionario__matricula")
    autocomplete_fields = ("funcionario", "projeto", "disciplina", "equipe")

@admin.register(HistogramaPlanejado)
class HistogramaPlanejadoAdmin(admin.ModelAdmin):
    list_display = ("data", "turno", "projeto", "area_local", "disciplina", "equipe", "funcao", "quantidade_planejada")
    list_filter = ("data", "turno", "projeto", "disciplina", "equipe", "funcao")
    search_fields = ("equipe__nome", "funcao__nome", "area_local__descricao")
    autocomplete_fields = ("projeto", "area_local", "disciplina", "equipe", "funcao")


