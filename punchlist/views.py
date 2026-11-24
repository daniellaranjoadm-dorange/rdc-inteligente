import csv

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, TemplateView, UpdateView

from cadastros.models import AreaLocal, Disciplina, Empresa, Projeto
from core.mixins import AuthenticatedTemplateMixin, RoleRequiredMixin
from punchlist.models import STATUS_EM_ABERTO, Categoria, PunchFoto, PunchItem, Status
from punchlist.services import (
    MAX_FOTOS, abrir_item, cancelar_item, iniciar_item, montar_painel_punch, resolver_item, verificar_item,
)


def pode_verificar(user):
    if user.is_superuser:
        return True
    perfil = getattr(user, "perfil_acesso", None)
    return bool(perfil and perfil.role in ("admin", "supervisor"))


class _Estilo:
    def _estilizar(self):
        for field in self.fields.values():
            w = field.widget
            w.attrs.setdefault("class", "form-select" if isinstance(w, forms.Select) else "form-control")


class PunchForm(_Estilo, forms.ModelForm):
    class Meta:
        model = PunchItem
        fields = ("projeto", "area_local", "compartimento", "disciplina", "categoria", "origem", "descricao",
                  "responsavel_empresa", "responsavel", "prazo")
        widgets = {"descricao": forms.Textarea(attrs={"rows": 3}),
                   "prazo": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "projeto" in self.fields:
            self.fields["projeto"].queryset = Projeto.objects.filter(ativo=True).order_by("nome")
            self.fields["area_local"].queryset = AreaLocal.objects.filter(ativo=True).select_related("projeto").order_by("codigo")
        self.fields["disciplina"].queryset = Disciplina.objects.filter(ativo=True).order_by("nome")
        self.fields["responsavel_empresa"].queryset = Empresa.objects.filter(ativa=True).order_by("nome")
        self._estilizar()

    def clean(self):
        dados = super().clean()
        projeto, area = dados.get("projeto"), dados.get("area_local")
        if projeto and area and area.projeto_id != projeto.pk:
            self.add_error("area_local", "Este bloco/área é de outro projeto.")
        return dados


class PunchEditForm(PunchForm):
    class Meta(PunchForm.Meta):
        fields = ("compartimento", "disciplina", "categoria", "origem", "descricao", "responsavel_empresa",
                  "responsavel", "prazo")

    def clean(self):
        return forms.ModelForm.clean(self)


def _filtrar(request):
    g = request.GET
    qs = PunchItem.objects.select_related("area_local", "projeto", "disciplina", "responsavel_empresa")
    f = {k: g.get(k, "") for k in ("projeto", "area", "categoria", "status", "situacao", "empresa", "q")}
    if f["projeto"].isdigit():
        qs = qs.filter(projeto_id=f["projeto"])
    if f["area"].isdigit():
        qs = qs.filter(area_local_id=f["area"])
    if f["categoria"] in Categoria.values:
        qs = qs.filter(categoria=f["categoria"])
    if f["status"] in Status.values:
        qs = qs.filter(status=f["status"])
    if f["empresa"].isdigit():
        qs = qs.filter(responsavel_empresa_id=f["empresa"])
    if f["situacao"] == "abertas" or (not f["status"] and not f["situacao"]):
        qs = qs.filter(status__in=STATUS_EM_ABERTO)
    elif f["situacao"] == "vencidas":
        qs = qs.filter(status__in=STATUS_EM_ABERTO, prazo__lt=timezone.localdate())
    if f["q"]:
        termo = f["q"].upper().replace("PL-", "")
        filtro = Q(descricao__icontains=f["q"]) | Q(compartimento__icontains=f["q"]) | Q(responsavel__icontains=f["q"])
        if termo.isdigit():
            filtro |= Q(numero=int(termo))
        qs = qs.filter(filtro)
    qs = qs.annotate(ordem_status=Case(
        When(status__in=STATUS_EM_ABERTO, then=Value(0)), default=Value(1), output_field=IntegerField()))
    return qs.order_by("ordem_status", "categoria", "prazo", "numero"), f


class PunchPainelView(AuthenticatedTemplateMixin, TemplateView):
    template_name = "punchlist/painel.html"

    def get(self, request, *args, **kwargs):
        if request.GET.get("formato") == "csv":
            return self._csv(request)
        return super().get(request, *args, **kwargs)

    def _csv(self, request):
        itens, _f = _filtrar(request)
        resposta = HttpResponse(content_type="text/csv; charset=utf-8")
        resposta["Content-Disposition"] = f'attachment; filename="punch_list_{timezone.localdate():%Y%m%d}.csv"'
        resposta.write("﻿")
        w = csv.writer(resposta, delimiter=";")
        w.writerow(["Código", "Projeto", "Bloco", "Compartimento", "Categoria", "Origem", "Disciplina", "Descrição",
                    "Empresa", "Responsável", "Prazo", "Situação", "Aberta em", "Fechada em"])
        for i in itens:
            w.writerow([i.codigo, i.projeto.nome, i.area_local.codigo, i.compartimento, i.categoria,
                        i.get_origem_display(), i.disciplina.nome if i.disciplina else "", i.descricao,
                        i.responsavel_empresa.nome if i.responsavel_empresa else "", i.responsavel,
                        f"{i.prazo:%d/%m/%Y}" if i.prazo else "", i.get_status_display(),
                        f"{timezone.localtime(i.created_at):%d/%m/%Y}",
                        f"{timezone.localtime(i.fechada_em):%d/%m/%Y}" if i.fechada_em else ""])
        return resposta

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        itens, f = _filtrar(self.request)
        context.update(montar_painel_punch(f["projeto"] if f["projeto"].isdigit() else None,
                                           f["area"] if f["area"].isdigit() else None))
        query = self.request.GET.copy()
        query.pop("formato", None)
        context.update({
            "itens": itens[:300], "total_filtrado": itens.count(), "f": f, "query_csv": query.urlencode(),
            "projetos": Projeto.objects.filter(ativo=True).order_by("nome"),
            "areas": AreaLocal.objects.filter(ativo=True).order_by("codigo"),
            "empresas": Empresa.objects.filter(punch_itens__isnull=False).distinct().order_by("nome"),
            "categorias": Categoria.choices, "status_choices": Status.choices,
            "pode_verificar": pode_verificar(self.request.user),
        })
        return context


class PunchCreateView(AuthenticatedTemplateMixin, View):
    template_name = "punchlist/form.html"

    def _render(self, request, form, erro=None):
        return render(request, self.template_name, {"form": form, "erro": erro, "titulo": "Nova pendência",
                                                    "max_fotos": MAX_FOTOS, "com_fotos": True})

    def get(self, request):
        inicial = {}
        area = AreaLocal.objects.filter(pk=request.GET.get("area") or 0).first()
        if area:
            inicial = {"projeto": area.projeto_id, "area_local": area.pk, "disciplina": area.disciplina_padrao_id}
        elif request.GET.get("projeto"):
            inicial = {"projeto": request.GET.get("projeto")}
        return self._render(request, PunchForm(initial=inicial))

    def post(self, request):
        form = PunchForm(request.POST)
        if not form.is_valid():
            return self._render(request, form)
        dados = dict(form.cleaned_data)
        try:
            item = abrir_item(usuario=request.user, fotos=request.FILES.getlist("fotos"), **dados)
        except ValidationError as exc:
            return self._render(request, form, " ".join(exc.messages))
        messages.success(request, f"Pendência {item.codigo} aberta.")
        if request.POST.get("outra"):
            return redirect(f"{reverse('punch-create')}?area={item.area_local_id}")
        return redirect("punch-detail", pk=item.pk)


class PunchUpdateView(AuthenticatedTemplateMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = ["admin", "supervisor"]
    model = PunchItem
    form_class = PunchEditForm
    template_name = "punchlist/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Editar {self.object.codigo}"
        return context

    def get_success_url(self):
        messages.success(self.request, "Pendência atualizada.")
        return reverse("punch-detail", args=[self.object.pk])


class PunchDetailView(AuthenticatedTemplateMixin, DetailView):
    template_name = "punchlist/detalhe.html"
    context_object_name = "item"
    queryset = PunchItem.objects.select_related("area_local", "projeto", "disciplina", "responsavel_empresa",
                                                "aberta_por", "resolvida_por", "fechada_por")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fotos = list(self.object.fotos.all())
        context.update({
            "fotos_abertura": [f for f in fotos if f.momento == PunchFoto.Momento.ABERTURA],
            "fotos_resolucao": [f for f in fotos if f.momento == PunchFoto.Momento.RESOLUCAO],
            "pode_verificar": pode_verificar(self.request.user), "max_fotos": MAX_FOTOS,
        })
        return context


class PunchAcaoView(AuthenticatedTemplateMixin, View):
    """POST /punch/<pk>/<acao>/ : iniciar, resolver (qualquer usuário); verificar, cancelar (admin/supervisor)."""

    def post(self, request, pk, acao):
        item = get_object_or_404(PunchItem, pk=pk)
        if acao in ("verificar", "cancelar") and not pode_verificar(request.user):
            raise PermissionDenied
        try:
            if acao == "iniciar":
                iniciar_item(item, usuario=request.user)
                messages.success(request, "Pendência em andamento.")
            elif acao == "resolver":
                resolver_item(item, nota=request.POST.get("nota", ""), fotos=request.FILES.getlist("fotos"),
                              usuario=request.user)
                messages.success(request, "Marcada como resolvida. Aguardando verificação do CQ.")
            elif acao == "verificar":
                aprovado = request.POST.get("decisao") == "aceitar"
                verificar_item(item, aprovado=aprovado, nota=request.POST.get("nota", ""), usuario=request.user)
                messages.success(request, "Pendência fechada." if aprovado else "Correção recusada; pendência reaberta.")
            elif acao == "cancelar":
                cancelar_item(item, motivo=request.POST.get("nota", ""), usuario=request.user)
                messages.success(request, "Pendência cancelada.")
            else:
                raise Http404
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("punch-detail", pk=pk)


class PunchFotoView(AuthenticatedTemplateMixin, View):
    def get(self, request, pk, tamanho="grande"):
        foto = get_object_or_404(PunchFoto, pk=pk)
        campo = foto.miniatura if tamanho == "mini" else foto.imagem
        try:
            resposta = FileResponse(campo.open("rb"), content_type="image/jpeg")
        except (FileNotFoundError, ValueError):
            raise Http404
        resposta["Cache-Control"] = "private, max-age=86400"
        return resposta
