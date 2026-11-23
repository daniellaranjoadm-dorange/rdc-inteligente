"""Avanço físico por bloco e disciplina + cadastro manual de atividades planejadas."""
from django import forms
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, TemplateView, UpdateView

from cadastros.models import AreaLocal, Projeto
from core.audit import registrar_auditoria
from core.mixins import AuthenticatedTemplateMixin, RoleRequiredMixin
from planejamento.models import AtividadeCronograma
from rdc.services.avanco_service import montar_avanco, svg_curva
from rdc.views_hh import _data_ou_none


def _pode_planejar(user):
    if user.is_superuser:
        return True
    perfil = getattr(user, "perfil_acesso", None)
    return bool(perfil and perfil.role in ("admin", "supervisor"))


class AvancoFisicoView(AuthenticatedTemplateMixin, TemplateView):
    template_name = "rdc/avanco.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        g = self.request.GET
        corte = _data_ou_none(g.get("corte")) or timezone.localdate()
        projetos = Projeto.objects.filter(ativo=True).order_by("nome")
        projeto_id = g.get("projeto") or ""
        if projeto_id and not projetos.filter(pk=projeto_id).exists():
            projeto_id = ""
        cascos_qs = AreaLocal.objects.exclude(casco="")
        if projeto_id:
            cascos_qs = cascos_qs.filter(projeto_id=projeto_id)
        cascos = sorted(set(cascos_qs.values_list("casco", flat=True)))
        casco = g.get("casco") if g.get("casco") in cascos else ""
        area_id = g.get("area") if (g.get("area") or "").isdigit() else None

        dados = montar_avanco(corte, projeto_id=projeto_id or None, casco=casco, area_id=area_id)
        context.update(dados)
        context.update({
            "corte": corte,
            "projetos": projetos,
            "projeto_id": str(projeto_id),
            "cascos": cascos,
            "casco": casco,
            "area_id": area_id,
            "svg": svg_curva(dados["curva"]),
            "pode_planejar": _pode_planejar(self.request.user),
            "filtros_qs": "&".join(f"{k}={v}" for k, v in (("projeto", projeto_id), ("casco", casco),
                                                           ("corte", corte.isoformat())) if v),
        })
        return context


class AtividadePlanejadaForm(forms.ModelForm):
    class Meta:
        model = AtividadeCronograma
        fields = ("projeto", "area_local", "disciplina", "codigo_atividade", "descr_atividade", "qtd_escopo",
                  "unidade", "data_inicio", "data_fim", "peso")
        labels = {
            "area_local": "Bloco / área", "codigo_atividade": "Código", "descr_atividade": "Descrição",
            "qtd_escopo": "Quantidade total (escopo)", "unidade": "Unidade", "data_inicio": "Início previsto",
            "data_fim": "Fim previsto",
        }
        help_texts = {"unidade": "Ex.: t (aço), m (solda), m² (pintura), UN."}
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["projeto"].queryset = Projeto.objects.filter(ativo=True).order_by("nome")
        self.fields["area_local"].queryset = AreaLocal.objects.filter(ativo=True).select_related("projeto")
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get("data_inicio"), dados.get("data_fim")
        if inicio and fim and fim < inicio:
            self.add_error("data_fim", "O fim previsto não pode ser antes do início.")
        projeto, area = dados.get("projeto"), dados.get("area_local")
        if projeto and area and area.projeto_id != projeto.pk:
            self.add_error("area_local", "Este bloco/área é de outro projeto.")
        qtd = dados.get("qtd_escopo")
        if qtd is not None and qtd <= 0:
            self.add_error("qtd_escopo", "Informe a quantidade total para medir o avanço.")
        return dados


class _AtividadePlanejadaBase(AuthenticatedTemplateMixin, RoleRequiredMixin):
    allowed_roles = ["admin", "supervisor"]
    model = AtividadeCronograma
    form_class = AtividadePlanejadaForm
    template_name = "rdc/atividade_planejada_form.html"

    def get_success_url(self):
        return f"{reverse('rdc-avanco')}?projeto={self.object.projeto_id}&area={self.object.area_local_id}#detalhe"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["voltar_url"] = reverse("rdc-avanco")
        return context


class AtividadePlanejadaCreateView(_AtividadePlanejadaBase, CreateView):
    def get_initial(self):
        inicial = super().get_initial()
        area = AreaLocal.objects.filter(pk=self.request.GET.get("area") or 0).first()
        if area:
            inicial.update({"projeto": area.projeto_id, "area_local": area.pk, "disciplina": area.disciplina_padrao_id})
        elif self.request.GET.get("projeto"):
            inicial["projeto"] = self.request.GET.get("projeto")
        return inicial

    def form_valid(self, form):
        form.instance.status_planejado = "Planejada"
        resposta = super().form_valid(form)
        registrar_auditoria(self.request.user, "criar_atividade_planejada", target_model="AtividadeCronograma",
                            target_id=self.object.pk, detail=str(self.object))
        messages.success(self.request, "Atividade planejada cadastrada.")
        return resposta

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Nova atividade planejada"
        return context


class AtividadePlanejadaUpdateView(_AtividadePlanejadaBase, UpdateView):
    def form_valid(self, form):
        resposta = super().form_valid(form)
        registrar_auditoria(self.request.user, "editar_atividade_planejada", target_model="AtividadeCronograma",
                            target_id=self.object.pk, detail=str(self.object))
        messages.success(self.request, "Atividade planejada atualizada.")
        return resposta

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Editar atividade {self.object.codigo_atividade}"
        return context
