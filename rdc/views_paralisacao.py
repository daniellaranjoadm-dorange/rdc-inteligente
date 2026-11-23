"""Paralisacoes do RDC: periodos parados e HH perdido."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, UpdateView

from core.audit import registrar_auditoria
from core.mixins import AuthenticatedTemplateMixin, RDCEditableMixin, RoleRequiredMixin
from rdc.forms import RDCParalisacaoForm
from rdc.models import RDC, RDCParalisacao


class _ParalisacaoBase(AuthenticatedTemplateMixin, RoleRequiredMixin, RDCEditableMixin):
    allowed_roles = ["admin", "supervisor"]
    model = RDCParalisacao
    form_class = RDCParalisacaoForm
    template_name = "rdc/paralisacao_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.rdc = get_object_or_404(RDC, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["rdc"] = self.rdc
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rdc"] = self.rdc
        return context

    def get_success_url(self):
        return f"{reverse('rdc-detail', kwargs={'pk': self.rdc.pk})}?tab=paralisacoes#paralisacoes"


class RDCParalisacaoCreateView(_ParalisacaoBase, CreateView):
    def form_valid(self, form):
        form.instance.rdc = self.rdc
        form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        p = self.object
        registrar_auditoria(
            self.request.user,
            "create_paralisacao",
            target_model="RDC",
            target_id=self.rdc.pk,
            detail=f"{p.get_motivo_display()} {p.inicio:%H:%M}-{p.fim:%H:%M}, {p.pessoas_afetadas} pessoa(s), HH perdido {p.hh_perdido}",
        )
        messages.success(self.request, f"Paralisação registrada: {p.hh_perdido} HH perdido.")
        return response


class RDCParalisacaoUpdateView(_ParalisacaoBase, UpdateView):
    pk_url_kwarg = "pk2"

    def get_queryset(self):
        return RDCParalisacao.objects.filter(rdc=self.rdc)

    def form_valid(self, form):
        response = super().form_valid(form)
        p = self.object
        registrar_auditoria(
            self.request.user,
            "update_paralisacao",
            target_model="RDC",
            target_id=self.rdc.pk,
            detail=f"{p.get_motivo_display()} {p.inicio:%H:%M}-{p.fim:%H:%M}, HH perdido {p.hh_perdido}",
        )
        messages.success(self.request, "Paralisação atualizada.")
        return response


class RDCParalisacaoDeleteView(AuthenticatedTemplateMixin, RoleRequiredMixin, RDCEditableMixin, View):
    allowed_roles = ["admin", "supervisor"]

    def dispatch(self, request, *args, **kwargs):
        self.rdc = get_object_or_404(RDC, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, pk, pk2):
        paralisacao = get_object_or_404(RDCParalisacao, pk=pk2, rdc=self.rdc)
        resumo = f"{paralisacao.get_motivo_display()} {paralisacao.inicio:%H:%M}-{paralisacao.fim:%H:%M}"
        paralisacao.delete()
        registrar_auditoria(request.user, "delete_paralisacao", target_model="RDC", target_id=self.rdc.pk, detail=resumo)
        messages.success(request, "Paralisação excluída.")
        return redirect(f"{reverse('rdc-detail', kwargs={'pk': self.rdc.pk})}?tab=paralisacoes#paralisacoes")
