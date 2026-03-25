from django.contrib import messages
import csv
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

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
        qs = ImportacaoArquivo.objects.select_related("criado_por").prefetch_related("erros").order_by("-created_at")
        status = self.request.GET.get("status", "").strip()
        q = self.request.GET.get("q", "").strip()

        if status:
            qs = qs.filter(status=status)

        if q:
            qs = qs.filter(arquivo__icontains=q)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        highlight_id = self.request.GET.get("highlight")
        status = self.request.GET.get("status", "").strip()
        q = self.request.GET.get("q", "").strip()

        base_qs = ImportacaoArquivo.objects.all()

        context["importacao_destacada"] = None
        if highlight_id:
            try:
                importacao = ImportacaoArquivo.objects.prefetch_related("erros").get(pk=highlight_id)
                context["importacao_destacada"] = importacao
                context["erros_preview"] = importacao.erros.all()[:10]
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

        return context


class ImportacaoCreateView(LoginRequiredMixin, CreateView):
    model = ImportacaoArquivo
    form_class = ImportacaoArquivoForm
    template_name = "importacoes/form.html"
    success_url = reverse_lazy("importacoes-home")
    login_url = "/accounts/login/"

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        executar_importacao(self.object.pk)
        messages.success(self.request, "Importação recebida e processada.")
        return redirect(f"{self.success_url}?highlight={self.object.pk}")




def download_modelo_funcionarios(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="modelo_funcionarios.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['matricula', 'nome', 'empresa', 'funcao'])
    writer.writerow(['123', 'João Silva', 'Empresa Exemplo', 'Operador'])

    return response


from django.http import HttpResponse
from importacoes.models import ImportacaoArquivo

def download_erros_importacao(request, pk):
    importacao = ImportacaoArquivo.objects.get(pk=pk)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="erros_importacao_{importacao.pk}.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['linha', 'campo', 'mensagem'])

    for erro in importacao.erros.all():
        writer.writerow([erro.linha, erro.campo, erro.mensagem])

    return response
