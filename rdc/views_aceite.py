"""Aceite do fiscal: pagina publica pelo link e gestao dos links/aceites pela equipe."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from core.audit import registrar_auditoria
from core.mixins import AuthenticatedTemplateMixin, RoleRequiredMixin
from rdc.forms import AceiteFiscalForm
from rdc.models import RDC, RDCAceite, RDCFoto, RDCLinkAceite
from rdc.services.aceite_service import assinatura_de_data_url, criar_link, registrar_aceite


def _ip(request):
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (encaminhado.split(",")[0].strip() if encaminhado else request.META.get("REMOTE_ADDR")) or None


def _url_aceite(request, link):
    return request.build_absolute_uri(reverse("aceite-publico", kwargs={"token": link.token}))


# ---------------------------------------------------------------- publico (sem login)

class AceitePublicoView(View):
    template_name = "aceite/publico.html"

    def _link(self, token):
        return get_object_or_404(RDCLinkAceite.objects.select_related("rdc", "rdc__projeto", "rdc__area_local", "rdc__disciplina"), token=token)

    def _contexto(self, link, form):
        rdc = link.rdc
        return {
            "link": link,
            "rdc": rdc,
            "form": form,
            "hh_trabalhado": rdc.funcionarios.aggregate(t=Sum("hh_total"))["t"] or 0,
            "hh_perdido": rdc.paralisacoes.aggregate(t=Sum("hh_perdido"))["t"] or 0,
            "funcionarios": rdc.funcionarios.select_related("funcao").order_by("nome"),
            "atividades": rdc.atividades.order_by("codigo_atividade"),
            "paralisacoes": rdc.paralisacoes.all(),
            "fotos": rdc.fotos.all(),
        }

    def get(self, request, token):
        link = self._link(token)
        if not link.ativo:
            return render(request, "aceite/indisponivel.html", {"link": link}, status=410)
        return render(request, self.template_name, self._contexto(link, AceiteFiscalForm()))

    def post(self, request, token):
        link = self._link(token)
        if not link.ativo:
            return render(request, "aceite/indisponivel.html", {"link": link}, status=410)
        form = AceiteFiscalForm(request.POST)
        assinatura = None
        if form.is_valid():
            try:
                assinatura = assinatura_de_data_url(form.cleaned_data["assinatura"])
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
        if not form.is_valid() or assinatura is None:
            return render(request, self.template_name, self._contexto(link, form), status=400)
        try:
            aceite = registrar_aceite(
                link.pk,
                decisao=form.cleaned_data["decisao"], nome=form.cleaned_data["nome"],
                cargo=form.cleaned_data["cargo"], empresa=form.cleaned_data["empresa"],
                observacao=form.cleaned_data["observacao"], assinatura_arquivo=assinatura,
                ip=_ip(request), navegador=request.META.get("HTTP_USER_AGENT", ""),
            )
        except ValidationError:
            link.refresh_from_db()
            return render(request, "aceite/indisponivel.html", {"link": link}, status=410)
        return render(request, "aceite/obrigado.html", {"aceite": aceite, "rdc": link.rdc})


class AceitePublicoFotoView(View):
    """Miniatura das fotos do RDC, so enquanto o link estiver ativo."""

    def get(self, request, token, foto_id):
        link = get_object_or_404(RDCLinkAceite, token=token)
        if not link.ativo:
            raise Http404()
        foto = get_object_or_404(RDCFoto, pk=foto_id, rdc_id=link.rdc_id)
        campo = foto.miniatura if request.GET.get("t") != "g" else foto.imagem
        if not campo or not campo.storage.exists(campo.name):
            raise Http404()
        response = FileResponse(campo.open("rb"), content_type="image/jpeg")
        response["Cache-Control"] = "private, max-age=3600"
        return response


# ---------------------------------------------------------------- equipe (com login)

class _AceiteEquipeBase(AuthenticatedTemplateMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "supervisor"]

    def dispatch(self, request, *args, **kwargs):
        self.rdc = get_object_or_404(RDC, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def _voltar(self):
        return redirect(f"{reverse('rdc-detail', kwargs={'pk': self.rdc.pk})}#aceite-fiscal")


class RDCGerarLinkAceiteView(_AceiteEquipeBase):
    def post(self, request, pk):
        link = criar_link(self.rdc, usuario=request.user, destinatario=request.POST.get("destinatario", ""))
        messages.success(request, "Link de aceite criado. Copie e envie ao fiscal.")
        return redirect(f"{reverse('rdc-detail', kwargs={'pk': self.rdc.pk})}?novo_link={link.pk}#aceite-fiscal")


class RDCRevogarLinkAceiteView(_AceiteEquipeBase):
    def post(self, request, pk, link_id):
        link = get_object_or_404(RDCLinkAceite, pk=link_id, rdc=self.rdc)
        if link.ativo:
            link.revogado_em = timezone.now()
            link.save(update_fields=["revogado_em", "updated_at"])
            registrar_auditoria(request.user, "revogar_link_aceite", target_model="RDC", target_id=self.rdc.pk,
                                detail=f"Link para {link.destinatario or '-'}")
            messages.success(request, "Link revogado. Ele não abre mais.")
        return self._voltar()


class RDCAceiteAssinaturaView(AuthenticatedTemplateMixin, View):
    def get(self, request, pk, aceite_id):
        aceite = get_object_or_404(RDCAceite, pk=aceite_id, rdc_id=pk)
        if not aceite.assinatura or not aceite.assinatura.storage.exists(aceite.assinatura.name):
            raise Http404()
        response = FileResponse(aceite.assinatura.open("rb"), content_type="image/png")
        response["Cache-Control"] = "private, max-age=86400"
        return response


class RDCComprovanteAceiteView(AuthenticatedTemplateMixin, View):
    def get(self, request, pk, aceite_id):
        aceite = get_object_or_404(
            RDCAceite.objects.select_related("rdc", "rdc__projeto", "rdc__area_local", "rdc__disciplina"),
            pk=aceite_id, rdc_id=pk,
        )
        from rdc.services.comprovante_aceite import gerar_pdf_comprovante

        pdf = gerar_pdf_comprovante(aceite, gerado_por=request.user)
        response = HttpResponse(pdf, content_type="application/pdf")
        modo = "inline" if request.GET.get("ver") else "attachment"
        response["Content-Disposition"] = f'{modo}; filename="rdc{pk}_comprovante_aceite_{aceite.pk}.pdf"'
        return response


def contexto_aceite(rdc, request):
    """Dados do cartao 'Aceite do fiscal' na tela do RDC."""
    links = list(rdc.links_aceite.all()[:10])
    novo = request.GET.get("novo_link")
    return {
        "aceites": list(rdc.aceites.all()),
        "links_aceite": [{"obj": l, "url": _url_aceite(request, l)} for l in links],
        "novo_link_id": int(novo) if (novo or "").isdigit() else None,
    }
