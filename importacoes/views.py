from django.contrib import messages
import csv
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView

from core.mixins import AuthenticatedTemplateMixin
from importacoes.forms import ImportacaoArquivoForm
from importacoes.models import ImportacaoArquivo
from importacoes.services import executar_importacao


class ImportacoesHomeView(AuthenticatedTemplateMixin, ListView):
    model = ImportacaoArquivo
    template_name = "importacoes/home.html"
    context_object_name = "importacoes"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            ImportacaoArquivo.objects.select_related("criado_por")
            .prefetch_related("erros")
            .order_by("-created_at")
        )
        status = self.request.GET.get("status", "").strip()
        q = self.request.GET.get("q", "").strip()

        if status:
            qs = qs.filter(status=status)

        if q:
            qs = qs.filter(arquivo__icontains=q)

        return qs

    def _resumo_padrao(self, importacao):
        resumo = getattr(importacao, "resumo", None) or {}
        return {
            "created": resumo.get("created", 0),
            "updated": resumo.get("updated", 0),
            "unchanged": resumo.get("unchanged", 0),
            "erros": resumo.get("erros", 0),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        highlight_id = self.request.GET.get("highlight")
        status = self.request.GET.get("status", "").strip()
        q = self.request.GET.get("q", "").strip()

        base_qs = ImportacaoArquivo.objects.all()

        context["importacao_destacada"] = None
        context["resumo_destacado"] = {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "erros": 0,
        }

        if highlight_id:
            try:
                importacao = ImportacaoArquivo.objects.prefetch_related("erros").get(pk=highlight_id)
                context["importacao_destacada"] = importacao
                context["erros_preview"] = importacao.erros.all()[:10]
                context["resumo_destacado"] = self._resumo_padrao(importacao)
            except ImportacaoArquivo.DoesNotExist:
                context["importacao_destacada"] = None

        context["filtro_status"] = status
        context["busca_arquivo"] = q
        context["totais"] = {
            "total": base_qs.count(),
            "concluidas": base_qs.filter(status="concluida").count(),
            "com_erro": base_qs.filter(status="erro").count(),
            "em_andamento": base_qs.filter(status__in=["pendente", "processando"]).count(),
        }

        resumos_por_id = {}
        for imp in context.get("importacoes", []):
            resumos_por_id[imp.id] = self._resumo_padrao(imp)

        context["resumos_por_id"] = resumos_por_id
        return context


class ImportacoesMobileView(AuthenticatedTemplateMixin, ListView):
    model = ImportacaoArquivo
    template_name = "importacoes/mobile.html"
    context_object_name = "importacoes"
    paginate_by = 20

    def get_queryset(self):
        return ImportacaoArquivo.objects.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = ImportacaoArquivo.objects.all()
        context["totais"] = {
            "total": base_qs.count(),
            "concluidas": base_qs.filter(status="concluida").count(),
            "com_erro": base_qs.filter(status="erro").count(),
            "em_andamento": base_qs.filter(status__in=["pendente", "processando"]).count(),
        }
        return context


class ImportacaoCreateView(LoginRequiredMixin, CreateView):
    model = ImportacaoArquivo
    form_class = ImportacaoArquivoForm
    template_name = "importacoes/form.html"
    success_url = reverse_lazy("importacoes-home")
    login_url = "/accounts/login/"

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        super().form_valid(form)
        executar_importacao(self.object.pk)
        messages.success(self.request, "Importação recebida e processada.")
        return redirect(f"{self.success_url}?highlight={self.object.pk}")


def download_modelo_funcionarios(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="modelo_funcionarios.csv"'

    writer = csv.writer(response, delimiter=";")
    writer.writerow(["matricula", "nome", "empresa", "funcao"])
    writer.writerow(["123", "João Silva", "Empresa Exemplo", "Operador"])

    return response


def download_erros_importacao(request, pk):
    importacao = ImportacaoArquivo.objects.get(pk=pk)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="erros_importacao_{importacao.pk}.csv"'

    writer = csv.writer(response, delimiter=";")
    writer.writerow(["linha", "campo", "mensagem"])

    for erro in importacao.erros.all():
        writer.writerow([erro.linha, erro.campo, erro.mensagem])

    return response
