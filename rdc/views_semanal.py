"""Download do relatório semanal em PDF e envio manual por e-mail."""
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.dateparse import parse_date
from django.views import View

from cadastros.models import Projeto
from core.audit import registrar_auditoria
from core.mixins import AuthenticatedTemplateMixin, RoleRequiredMixin
from rdc.services.relatorio_semanal import enviar_relatorios_semanais, gerar_pdf_semanal


def _fim(request):
    try:
        return parse_date(request.GET.get("fim") or request.POST.get("fim") or "")
    except ValueError:
        return None


class RelatorioSemanalPDFView(AuthenticatedTemplateMixin, View):
    def get(self, request):
        projeto_id = request.GET.get("projeto") or ""
        if not projeto_id.isdigit():
            projeto = Projeto.objects.filter(ativo=True).order_by("nome").first()
            if not projeto:
                raise Http404
        else:
            projeto = get_object_or_404(Projeto, pk=projeto_id)
        pdf, dados = gerar_pdf_semanal(projeto, _fim(request), gerado_por=request.user)
        resposta = HttpResponse(pdf, content_type="application/pdf")
        resposta["Content-Disposition"] = f'inline; filename="Relatorio_semanal_{projeto.codigo}_{dados["fim"]:%Y%m%d}.pdf"'
        return resposta


class RelatorioSemanalEnviarView(AuthenticatedTemplateMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "supervisor"]

    def post(self, request):
        projeto = get_object_or_404(Projeto, pk=request.POST.get("projeto") or 0)
        voltar = request.POST.get("voltar") or "/rdc/blocos/"
        if not voltar.startswith("/"):
            voltar = "/rdc/blocos/"
        if not projeto.lista_emails_relatorio:
            messages.error(request, "Cadastre os e-mails do projeto (Cadastros > Projetos > Editar) antes de enviar.")
            return redirect(voltar)
        try:
            n = enviar_relatorios_semanais(_fim(request), projeto_id=projeto.pk)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(voltar)
        if n:
            registrar_auditoria(request.user, "enviar_relatorio_semanal", target_model="Projeto", target_id=projeto.pk,
                                detail=", ".join(projeto.lista_emails_relatorio))
            messages.success(request, f"Relatório semanal enviado para {', '.join(projeto.lista_emails_relatorio)}.")
        else:
            messages.warning(request, "Nenhum RDC na semana: o relatório não foi enviado.")
        return redirect(voltar)
