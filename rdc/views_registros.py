"""Registros simples do dia (equipamentos e ocorrencias): incluir, editar e excluir."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, UpdateView

from core.audit import registrar_auditoria
from core.mixins import AuthenticatedTemplateMixin, RDCEditableMixin, RoleRequiredMixin
from rdc.forms import RDCEquipamentoForm, RDCOcorrenciaForm
from rdc.models import RDC, RDCEquipamento, RDCOcorrencia


class _RegistroBase(AuthenticatedTemplateMixin, RoleRequiredMixin, RDCEditableMixin):
    allowed_roles = ["admin", "supervisor"]
    template_name = "rdc/registro_form.html"
    aba = ""
    titulo_novo = ""
    titulo_editar = ""
    acao_audit = ""

    def dispatch(self, request, *args, **kwargs):
        self.rdc = get_object_or_404(RDC, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(rdc=self.rdc)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["rdc"] = self.rdc
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "rdc": self.rdc,
            "titulo": self.titulo_editar if getattr(self, "object", None) else self.titulo_novo,
            "eyebrow": self.eyebrow,
            "voltar_url": self.get_success_url(),
        })
        return context

    def get_success_url(self):
        return f"{reverse('rdc-detail', kwargs={'pk': self.rdc.pk})}?tab={self.aba}#{self.aba}"

    def form_valid(self, form):
        novo = form.instance.pk is None
        form.instance.rdc = self.rdc
        if novo:
            form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        registrar_auditoria(self.request.user, f"{'create' if novo else 'update'}_{self.acao_audit}",
                            target_model="RDC", target_id=self.rdc.pk, detail=str(self.object))
        messages.success(self.request, f"{self.model._meta.verbose_name.capitalize()} {'registrado' if novo else 'atualizado'}.")
        return response


class _RegistroDeleteBase(AuthenticatedTemplateMixin, RoleRequiredMixin, RDCEditableMixin, View):
    allowed_roles = ["admin", "supervisor"]
    model = None
    aba = ""
    acao_audit = ""

    def dispatch(self, request, *args, **kwargs):
        self.rdc = get_object_or_404(RDC, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, pk2):
        obj = get_object_or_404(self.model, pk=pk2, rdc=self.rdc)
        resumo = str(obj)
        obj.delete()
        registrar_auditoria(request.user, f"delete_{self.acao_audit}", target_model="RDC", target_id=self.rdc.pk, detail=resumo)
        messages.success(request, "Registro excluído.")
        return redirect(f"{reverse('rdc-detail', kwargs={'pk': self.rdc.pk})}?tab={self.aba}#{self.aba}")


class _Equipamento:
    model = RDCEquipamento
    form_class = RDCEquipamentoForm
    aba = "equipamentos"
    eyebrow = "Equipamentos"
    titulo_novo = "Registrar equipamento do dia"
    titulo_editar = "Editar equipamento"
    acao_audit = "equipamento"


class _Ocorrencia:
    model = RDCOcorrencia
    form_class = RDCOcorrenciaForm
    aba = "ocorrencias"
    eyebrow = "Segurança e qualidade"
    titulo_novo = "Registrar ocorrência"
    titulo_editar = "Editar ocorrência"
    acao_audit = "ocorrencia"


class RDCEquipamentoCreateView(_Equipamento, _RegistroBase, CreateView):
    pass


class RDCEquipamentoUpdateView(_Equipamento, _RegistroBase, UpdateView):
    pk_url_kwarg = "pk2"


class RDCEquipamentoDeleteView(_RegistroDeleteBase):
    model = RDCEquipamento
    aba = "equipamentos"
    acao_audit = "equipamento"


class RDCOcorrenciaCreateView(_Ocorrencia, _RegistroBase, CreateView):
    pass


class RDCOcorrenciaUpdateView(_Ocorrencia, _RegistroBase, UpdateView):
    pk_url_kwarg = "pk2"


class RDCOcorrenciaDeleteView(_RegistroDeleteBase):
    model = RDCOcorrencia
    aba = "ocorrencias"
    acao_audit = "ocorrencia"
