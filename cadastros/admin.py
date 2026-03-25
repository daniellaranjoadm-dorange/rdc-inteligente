from django.contrib import admin
from django.utils.html import format_html

from cadastros.models import AreaLocal, Disciplina, Empresa, Equipe, Funcao, Funcionario, Projeto


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "cliente", "ativo", "created_at")
    list_filter = ("ativo", "cliente")
    search_fields = ("codigo", "nome", "cliente")


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "ativo")
    list_filter = ("ativo",)
    search_fields = ("codigo", "nome")


@admin.register(AreaLocal)
class AreaLocalAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao", "projeto", "disciplina_padrao", "ativo")
    list_filter = ("ativo", "projeto", "disciplina_padrao")
    search_fields = ("codigo", "descricao", "projeto__nome")
    autocomplete_fields = ("projeto", "disciplina_padrao")


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj_formatado", "pendencia_visual", "ativa")
    list_filter = ("ativa", "cadastro_pendente")
    search_fields = ("nome", "cnpj", "observacoes")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="CNPJ", ordering="cnpj")
    def cnpj_formatado(self, obj):
        return obj.cnpj or "€”"

    @admin.display(description="Pendência", ordering="cadastro_pendente")
    def pendencia_visual(self, obj):
        if obj.cadastro_pendente:
            return format_html('<span style="color:#b45309;font-weight:600;">Pendente</span>')
        return format_html('<span style="color:#15803d;font-weight:600;">OK</span>')


@admin.register(Funcao)
class FuncaoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "ativa")
    list_filter = ("ativa",)
    search_fields = ("codigo", "nome")


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ("matricula", "nome", "funcao", "empresa", "cpf", "ativo")
    list_filter = ("ativo", "funcao", "empresa")
    search_fields = ("matricula", "nome", "cpf", "rg")
    autocomplete_fields = ("funcao", "empresa")


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "disciplina", "encarregado", "empresa", "ativa")
    list_filter = ("ativa", "disciplina", "empresa")
    search_fields = ("codigo", "nome")
    autocomplete_fields = ("disciplina", "encarregado", "empresa")



