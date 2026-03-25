from django.contrib import admin

from core.models import ImportJob


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo",
        "status",
        "usuario",
        "total_linhas",
        "linhas_processadas",
        "linhas_com_erro",
        "criado_em",
    )
    list_filter = ("tipo", "status", "criado_em")
    search_fields = ("id", "nome_arquivo_original", "observacoes")
    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "iniciado_em",
        "finalizado_em",
        "resumo",
        "erros",
    )
