from django.contrib import admin

from planejamento.models import AtividadeCronograma

@admin.register(AtividadeCronograma)
class AtividadeCronogramaAdmin(admin.ModelAdmin):
    list_display = ("codigo_atividade", "descr_atividade", "projeto", "area_local", "disciplina", "data_inicio", "data_fim", "turno")
    list_filter = ("projeto", "disciplina", "turno", "status_planejado")
    search_fields = ("codigo_atividade", "descr_atividade", "codigo_subatividade", "descr_subatividade")
    autocomplete_fields = ("projeto", "area_local", "disciplina")
