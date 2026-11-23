"""Tela para copiar um RDC para outro dia."""
from datetime import timedelta

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from core.choices import TurnoChoices
from core.mixins import AuthenticatedTemplateMixin, RoleRequiredMixin
from rdc.models import RDC
from rdc.services.copiar_rdc_service import copiar_rdc


class CopiarRDCForm(forms.Form):
    data = forms.DateField(label="Data do novo RDC", widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"))
    turno = forms.ChoiceField(label="Turno", choices=TurnoChoices.CHOICES, widget=forms.Select(attrs={"class": "form-select"}))
    funcionarios = forms.BooleanField(label="Equipe (funcionários, funções e horas padrão)", required=False, initial=True)
    atividades = forms.BooleanField(label="Atividades (sem o executado)", required=False, initial=True)
    equipamentos = forms.BooleanField(label="Equipamentos (sem as horas)", required=False, initial=True)


class RDCCopiarView(AuthenticatedTemplateMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "supervisor"]
    template_name = "rdc/copiar_rdc.html"

    def _origem(self, pk):
        return get_object_or_404(RDC.objects.select_related("projeto", "area_local", "disciplina"), pk=pk)

    def get(self, request, pk):
        origem = self._origem(pk)
        form = CopiarRDCForm(initial={"data": origem.data + timedelta(days=1), "turno": origem.turno})
        return render(request, self.template_name, {"rdc": origem, "form": form})

    def post(self, request, pk):
        origem = self._origem(pk)
        form = CopiarRDCForm(request.POST)
        if form.is_valid():
            try:
                novo = copiar_rdc(
                    origem, data=form.cleaned_data["data"], turno=form.cleaned_data["turno"], usuario=request.user,
                    funcionarios=form.cleaned_data["funcionarios"], atividades=form.cleaned_data["atividades"],
                    equipamentos=form.cleaned_data["equipamentos"],
                )
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
            else:
                messages.success(request, f"RDC #{novo.pk} criado a partir do RDC #{origem.pk}. Confira presença e horas do dia.")
                return redirect(reverse("rdc-detail", kwargs={"pk": novo.pk}))
        return render(request, self.template_name, {"rdc": origem, "form": form}, status=400)
