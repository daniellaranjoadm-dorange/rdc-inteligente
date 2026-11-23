"""PDF do RDC e envio por e-mail."""
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from core.mixins import AuthenticatedTemplateMixin, RoleRequiredMixin
from rdc.models import RDC
from rdc.services.email_service import enviar_rdc_por_email, separar_emails


class RDCPdfView(AuthenticatedTemplateMixin, View):
    def get(self, request, pk):
        rdc = get_object_or_404(RDC.objects.select_related("projeto", "area_local", "disciplina"), pk=pk)
        from rdc.services.relatorio_rdc import gerar_pdf_rdc

        response = HttpResponse(gerar_pdf_rdc(rdc, gerado_por=request.user), content_type="application/pdf")
        modo = "inline" if request.GET.get("ver") else "attachment"
        response["Content-Disposition"] = f'{modo}; filename="RDC_{rdc.pk}_{rdc.data:%Y%m%d}.pdf"'
        return response


class RDCEnviarEmailView(AuthenticatedTemplateMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "supervisor"]

    def post(self, request, pk):
        rdc = get_object_or_404(RDC.objects.select_related("projeto", "area_local", "disciplina"), pk=pk)
        destinatarios, invalidos = separar_emails(request.POST.get("destinatarios", ""))
        voltar = redirect(f"{reverse('rdc-detail', kwargs={'pk': rdc.pk})}#envio-email")
        if invalidos:
            messages.error(request, "E-mail inválido: " + ", ".join(invalidos))
            return voltar
        try:
            n = enviar_rdc_por_email(rdc, destinatarios, usuario=request.user,
                                     base_url=request.build_absolute_uri("/"), motivo="manual")
        except ValueError as exc:
            messages.warning(request, str(exc))
        except Exception:  # noqa: BLE001
            messages.error(request, "Não foi possível enviar o e-mail agora. Tente de novo em alguns minutos.")
        else:
            messages.success(request, f"RDC enviado por e-mail para {n} destinatário(s).")
        return voltar
