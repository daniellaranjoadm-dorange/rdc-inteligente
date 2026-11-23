"""Fotos do RDC: envio, visualizacao (so com login), edicao, exclusao e relatorio fotografico."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, UpdateView

from core.audit import registrar_auditoria
from core.mixins import AuthenticatedTemplateMixin, RDCEditableMixin, RoleRequiredMixin
from rdc.forms import RDCFotoDadosForm
from rdc.models import RDC, RDCFoto
from rdc.services.foto_service import FOTOS_POR_ENVIO, processar_foto


def _url_aba_fotos(rdc):
    return f"{reverse('rdc-detail', kwargs={'pk': rdc.pk})}?tab=fotos#fotos"


class _FotoEdicaoBase(AuthenticatedTemplateMixin, RoleRequiredMixin, RDCEditableMixin):
    allowed_roles = ["admin", "supervisor"]

    def dispatch(self, request, *args, **kwargs):
        self.rdc = get_object_or_404(RDC, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)


class RDCFotoUploadView(_FotoEdicaoBase, FormView):
    form_class = RDCFotoDadosForm
    template_name = "rdc/foto_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["rdc"] = self.rdc
        if self.request.method == "GET":
            paralisacao = self.request.GET.get("paralisacao")
            if paralisacao and self.rdc.paralisacoes.filter(pk=paralisacao).exists():
                kwargs.setdefault("initial", {}).update({"paralisacao": paralisacao, "categoria": "paralisacao"})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"rdc": self.rdc, "fotos_por_envio": FOTOS_POR_ENVIO})
        return context

    def form_valid(self, form):
        arquivos = self.request.FILES.getlist("fotos")
        if not arquivos:
            form.add_error(None, "Escolha ao menos uma foto.")
            return self.form_invalid(form)
        if len(arquivos) > FOTOS_POR_ENVIO:
            form.add_error(None, f"Envie no máximo {FOTOS_POR_ENVIO} fotos por vez.")
            return self.form_invalid(form)

        salvas, erros = 0, []
        for arquivo in arquivos:
            try:
                dados = processar_foto(arquivo)
            except ValidationError as exc:
                erros.extend(exc.messages)
                continue
            foto = RDCFoto(
                rdc=self.rdc,
                categoria=form.cleaned_data["categoria"],
                legenda=form.cleaned_data["legenda"],
                rdc_atividade=form.cleaned_data["rdc_atividade"],
                paralisacao=form.cleaned_data["paralisacao"],
                tirada_em=dados["tirada_em"],
                largura=dados["largura"],
                altura=dados["altura"],
                tamanho_bytes=dados["tamanho_bytes"],
                criado_por=self.request.user,
            )
            foto.imagem.save("foto.jpg", dados["imagem"], save=False)
            foto.miniatura.save("min.jpg", dados["miniatura"], save=False)
            foto.save()
            salvas += 1

        if salvas:
            registrar_auditoria(
                self.request.user, "create_foto", target_model="RDC", target_id=self.rdc.pk,
                detail=f"{salvas} foto(s) - {form.cleaned_data['legenda'] or 'sem legenda'}",
            )
            messages.success(self.request, f"{salvas} foto(s) adicionada(s) ao RDC.")
        for erro in erros:
            messages.error(self.request, erro)
        if not salvas:
            form.add_error(None, "Nenhuma foto foi salva. Confira os arquivos.")
            return self.form_invalid(form)
        return redirect(_url_aba_fotos(self.rdc))


class RDCFotoUpdateView(_FotoEdicaoBase, UpdateView):
    model = RDCFoto
    form_class = RDCFotoDadosForm
    template_name = "rdc/foto_editar.html"
    pk_url_kwarg = "pk2"

    def get_queryset(self):
        return RDCFoto.objects.filter(rdc=self.rdc)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["rdc"] = self.rdc
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rdc"] = self.rdc
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Foto atualizada.")
        return response

    def get_success_url(self):
        return _url_aba_fotos(self.rdc)


class RDCFotoDeleteView(_FotoEdicaoBase, View):
    def post(self, request, pk, pk2):
        foto = get_object_or_404(RDCFoto, pk=pk2, rdc=self.rdc)
        resumo = foto.legenda or f"foto {foto.pk}"
        foto.delete()
        registrar_auditoria(request.user, "delete_foto", target_model="RDC", target_id=self.rdc.pk, detail=resumo)
        messages.success(request, "Foto excluída.")
        return redirect(_url_aba_fotos(self.rdc))


class RDCFotoArquivoView(AuthenticatedTemplateMixin, View):
    """Entrega a imagem so para quem esta logado (as fotos da obra nao sao publicas)."""

    def get(self, request, pk, pk2, tamanho="grande"):
        foto = get_object_or_404(RDCFoto, pk=pk2, rdc_id=pk)
        campo = foto.miniatura if tamanho == "mini" else foto.imagem
        if not campo or not campo.name or not campo.storage.exists(campo.name):
            raise Http404("Arquivo da foto não encontrado.")
        response = FileResponse(campo.open("rb"), content_type="image/jpeg")
        response["Cache-Control"] = "private, max-age=86400"
        if request.GET.get("baixar"):
            response["Content-Disposition"] = f'attachment; filename="rdc{pk}_foto{foto.pk}.jpg"'
        return response


class RDCRelatorioFotograficoView(AuthenticatedTemplateMixin, View):
    """PDF com as fotos do RDC, duas por linha, com legenda e horario."""

    def get(self, request, pk):
        rdc = get_object_or_404(RDC.objects.select_related("projeto", "area_local", "disciplina"), pk=pk)
        fotos = list(rdc.fotos.select_related("rdc_atividade", "paralisacao").all())
        if not fotos:
            messages.warning(request, "Este RDC ainda não tem fotos para o relatório fotográfico.")
            return redirect(_url_aba_fotos(rdc))
        from rdc.services.relatorio_fotografico import gerar_pdf_fotografico

        pdf = gerar_pdf_fotografico(rdc, fotos, gerado_por=request.user, gerado_em=timezone.localtime())
        registrar_auditoria(request.user, "exportar_relatorio_fotografico", target_model="RDC", target_id=rdc.pk,
                            detail=f"{len(fotos)} foto(s)")
        response = HttpResponse(pdf, content_type="application/pdf")
        modo = "inline" if request.GET.get("ver") else "attachment"  # ?ver=1 abre no navegador
        response["Content-Disposition"] = f'{modo}; filename="rdc{rdc.pk}_relatorio_fotografico_{rdc.data:%Y%m%d}.pdf"'
        return response
