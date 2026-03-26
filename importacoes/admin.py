from django.contrib import admin, messages
from django.db.models import Count
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from importacoes.models import ImportacaoArquivo, ImportacaoErro
from importacoes.services import executar_importacao


class ImportacaoErroInline(admin.TabularInline):
    model = ImportacaoErro
    extra = 0
    readonly_fields = ("linha", "campo", "mensagem")
    can_delete = False
    ordering = ("linha",)
    show_change_link = False
    verbose_name = "Erro da importação"
    verbose_name_plural = "Erros da importação"


@admin.action(description="Limpar erros das importações selecionadas")
def limpar_erros_das_importacoes(modeladmin, request, queryset):
    total = 0
    for importacao in queryset:
        deletados, _ = importacao.erros.all().delete()
        total += deletados
    modeladmin.message_user(request, f"{total} erro(s) removido(s).", level=messages.SUCCESS)


@admin.action(description="Reprocessar importações selecionadas")
def reprocessar_importacoes(modeladmin, request, queryset):
    total = 0
    for importacao in queryset:
        executar_importacao(importacao.id)
        total += 1
    modeladmin.message_user(request, f"{total} importação(ões) reprocessada(s).", level=messages.SUCCESS)


@admin.register(ImportacaoArquivo)
class ImportacaoArquivoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo",
        "nome_arquivo",
        "status",
        "total_erros_coluna",
        "criado_por",
        "created_at",
        "finalizado_em",
        "link_erros",
    )
    list_filter = ("tipo", "status", "created_at", "criado_por")
    search_fields = ("arquivo", "observacoes", "criado_por__username", "criado_por__first_name")
    autocomplete_fields = ("criado_por",)
    readonly_fields = ("iniciado_em", "finalizado_em", "created_at", "updated_at")
    inlines = (ImportacaoErroInline,)
    actions = (limpar_erros_das_importacoes, reprocessar_importacoes)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(total_erros_qtd=Count("erros"))

    @admin.display(description="Arquivo", ordering="arquivo")
    def nome_arquivo(self, obj: ImportacaoArquivo) -> str:
        return obj.nome_arquivo

    @admin.display(description="Qtde erros", ordering="total_erros_qtd")
    def total_erros_coluna(self, obj: ImportacaoArquivo) -> int:
        return getattr(obj, "total_erros_qtd", 0)

    @admin.display(description="Ver erros")
    def link_erros(self, obj: ImportacaoArquivo) -> str:
        url = f'{reverse("admin:importacoes_importacaoerro_changelist")}?importacao__id__exact={obj.pk}'
        return format_html('<a href="{}">Abrir erros</a>', url)

    def save_model(self, request: HttpRequest, obj: ImportacaoArquivo, form, change):
        if not obj.pk and not obj.criado_por_id:
            obj.criado_por = request.user
        if not obj.iniciado_em:
            obj.iniciado_em = timezone.now()
        super().save_model(request, obj, form, change)

        if obj.status in {"pendente", "erro"}:
            executar_importacao(obj.id)

    def response_change(self, request, obj):
        if "_limpar_erros" in request.POST:
            deletados, _ = obj.erros.all().delete()
            self.message_user(
                request,
                f"{deletados} erro(s) removido(s) da importação {obj.id}.",
                level=messages.SUCCESS,
            )
            return redirect(request.path)
        if "_reprocessar" in request.POST:
            executar_importacao(obj.id)
            self.message_user(
                request,
                f"Importação {obj.id} reprocessada com sucesso.",
                level=messages.SUCCESS,
            )
            return redirect(request.path)
        return super().response_change(request, obj)

    def render_change_form(self, request, context, *args, **kwargs):
        context["adminform"].form.fields["observacoes"].help_text = (
            "Resumo do processamento. Use os botões abaixo para reprocessar ou limpar erros."
        )
        return super().render_change_form(request, context, *args, **kwargs)


@admin.action(description="Limpar erros selecionados")
def limpar_erros_selecionados(modeladmin, request, queryset):
    deletados, _ = queryset.delete()
    modeladmin.message_user(request, f"{deletados} erro(s) removido(s).", level=messages.SUCCESS)


@admin.action(description="Limpar todos os erros filtrados")
def limpar_erros_filtrados(modeladmin, request, queryset):
    deletados, _ = queryset.delete()
    modeladmin.message_user(request, f"{deletados} erro(s) removido(s) pelos filtros atuais.", level=messages.SUCCESS)


@admin.register(ImportacaoErro)
class ImportacaoErroAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "importacao_link",
        "tipo_importacao",
        "arquivo_importacao",
        "linha",
        "campo",
        "mensagem_curta",
    )
    list_filter = ("importacao__tipo", "importacao__status", "importacao__created_at", "campo")
    search_fields = (
        "campo",
        "mensagem",
        "importacao__arquivo",
        "importacao__observacoes",
        "importacao__criado_por__username",
    )
    autocomplete_fields = ("importacao",)
    list_select_related = ("importacao",)
    actions = (limpar_erros_selecionados, limpar_erros_filtrados)

    @admin.display(description="Importação")
    def importacao_link(self, obj: ImportacaoErro) -> str:
        url = reverse("admin:importacoes_importacaoarquivo_change", args=[obj.importacao_id])
        return format_html('<a href="{}">#{}</a>', url, obj.importacao_id)

    @admin.display(description="Tipo", ordering="importacao__tipo")
    def tipo_importacao(self, obj: ImportacaoErro) -> str:
        return obj.importacao.get_tipo_display()

    @admin.display(description="Arquivo", ordering="importacao__arquivo")
    def arquivo_importacao(self, obj: ImportacaoErro) -> str:
        return obj.importacao.nome_arquivo

    @admin.display(description="Mensagem")
    def mensagem_curta(self, obj: ImportacaoErro) -> str:
        return obj.mensagem[:140] + ("..." if len(obj.mensagem) > 140 else "")



