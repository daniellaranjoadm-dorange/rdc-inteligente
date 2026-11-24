from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from cadastros.models import AreaLocal, Projeto
from core.mixins import AuthenticatedTemplateMixin, RoleRequiredMixin
from soldagem.forms import EPSForm, ExecucaoForm, JuntaForm, ResultadoENDForm, SoldadorForm
from soldagem.models import EPS, InspecaoEND, JuntaSolda, ResultadoEND, Soldador, StatusJunta
from soldagem.services import LIMITE_TAXA_REPARO, montar_painel_solda, registrar_execucao, registrar_resultado_end


def pode_editar(user):
    if user.is_superuser:
        return True
    perfil = getattr(user, "perfil_acesso", None)
    return bool(perfil and perfil.role in ("admin", "supervisor"))


class _Ctx:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pode_editar"] = pode_editar(self.request.user)
        return context


class PainelSoldaView(AuthenticatedTemplateMixin, _Ctx, TemplateView):
    template_name = "soldagem/painel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projetos = Projeto.objects.filter(ativo=True).order_by("nome")
        projeto_id = self.request.GET.get("projeto") or ""
        if projeto_id and not projetos.filter(pk=projeto_id).exists():
            projeto_id = ""
        area_id = self.request.GET.get("area") if (self.request.GET.get("area") or "").isdigit() else ""
        areas = AreaLocal.objects.filter(juntas_solda__isnull=False).distinct().order_by("codigo")
        if projeto_id:
            areas = areas.filter(projeto_id=projeto_id)
        context.update(montar_painel_solda(projeto_id or None, area_id or None))
        context.update({"projetos": projetos, "projeto_id": str(projeto_id), "areas": areas, "area_id": area_id,
                        "resultado_form": ResultadoENDForm()})
        return context


class JuntaListView(AuthenticatedTemplateMixin, _Ctx, ListView):
    template_name = "soldagem/juntas.html"
    paginate_by = 50
    context_object_name = "juntas"

    def get_queryset(self):
        g = self.request.GET
        qs = JuntaSolda.objects.select_related("area_local", "projeto", "eps")
        if g.get("projeto"):
            qs = qs.filter(projeto_id=g["projeto"]) if g["projeto"].isdigit() else qs
        if (g.get("area") or "").isdigit():
            qs = qs.filter(area_local_id=g["area"])
        if g.get("status") in StatusJunta.values:
            qs = qs.filter(status=g["status"])
        if g.get("q"):
            qs = qs.filter(Q(codigo__icontains=g["q"]) | Q(descricao__icontains=g["q"]))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        g = self.request.GET
        context.update({
            "projetos": Projeto.objects.filter(ativo=True).order_by("nome"),
            "areas": AreaLocal.objects.filter(juntas_solda__isnull=False).distinct().order_by("codigo"),
            "status_choices": StatusJunta.choices,
            "f": {"projeto": g.get("projeto", ""), "area": g.get("area", ""), "status": g.get("status", ""), "q": g.get("q", "")},
        })
        return context


class JuntaDetailView(AuthenticatedTemplateMixin, _Ctx, DetailView):
    template_name = "soldagem/junta_detalhe.html"
    context_object_name = "junta"
    queryset = JuntaSolda.objects.select_related("area_local", "projeto", "eps")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        junta = self.object
        execucoes = list(junta.execucoes.select_related("soldador", "soldador__funcionario", "rdc"))
        inspecoes = list(junta.inspecoes.prefetch_related("soldadores"))
        eventos = [("solda", e.data, 0, e.pk, e) for e in execucoes] + [
            ("end", i.inspecionado_em or i.solicitado_em, 1, i.pk, i) for i in inspecoes]
        eventos.sort(key=lambda ev: (ev[1], ev[2], ev[3]))
        context.update({
            "eventos": [{"tipo": t, "obj": o} for t, _d, _o, _pk, o in eventos],
            "inspecoes": inspecoes,
            "execucao_form": kwargs.get("execucao_form") or ExecucaoForm(),
            "resultado_form": kwargs.get("resultado_form") or ResultadoENDForm(),
            "pendente": junta.inspecoes.filter(resultado=ResultadoEND.PENDENTE).first(),
            "aceita_solda": junta.status in (StatusJunta.PLANEJADA, StatusJunta.EM_EXECUCAO, StatusJunta.REPROVADA),
            "e_reparo": junta.status == StatusJunta.REPROVADA,
        })
        return context


class RegistrarSoldaView(AuthenticatedTemplateMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "supervisor"]

    def post(self, request, pk):
        junta = get_object_or_404(JuntaSolda, pk=pk)
        form = ExecucaoForm(request.POST)
        if form.is_valid():
            try:
                registrar_execucao(junta, reparo=junta.status == StatusJunta.REPROVADA, usuario=request.user,
                                   **form.cleaned_data)
                junta.refresh_from_db()
                msg = "Solda registrada."
                if junta.status == StatusJunta.AGUARDANDO_END:
                    msg += f" Junta completa: chamada de {junta.get_metodo_end_display() or 'END'} aberta."
                messages.success(request, msg)
                return redirect("solda-junta-detail", pk=pk)
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
        else:
            messages.error(request, "Confira os campos da solda: " + "; ".join(
                f"{form.fields[c].label or c}: {' '.join(e)}" for c, e in form.errors.items()))
        return redirect("solda-junta-detail", pk=pk)


class ResultadoENDView(AuthenticatedTemplateMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "supervisor"]

    def post(self, request, pk):
        inspecao = get_object_or_404(InspecaoEND.objects.select_related("junta"), pk=pk)
        form = ResultadoENDForm(request.POST)
        voltar = request.POST.get("voltar") or reverse("solda-junta-detail", args=[inspecao.junta_id])
        if not voltar.startswith("/"):
            voltar = reverse("solda-junta-detail", args=[inspecao.junta_id])
        if form.is_valid():
            try:
                registrar_resultado_end(inspecao, usuario=request.user, **form.cleaned_data)
                messages.success(request, f"Resultado do END da junta {inspecao.junta.codigo} registrado.")
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
        else:
            messages.error(request, "Confira o resultado do END.")
        return redirect(voltar)


class _Cadastro(AuthenticatedTemplateMixin, RoleRequiredMixin):
    allowed_roles = ["admin", "supervisor"]
    template_name = "soldagem/form.html"
    titulo = ""
    lista = ""

    def get_success_url(self):
        return reverse(self.lista)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo if not getattr(self, "object", None) else f"Editar {self.object}"
        context["voltar_url"] = reverse(self.lista)
        return context

    def form_valid(self, form):
        messages.success(self.request, "Salvo.")
        return super().form_valid(form)


class JuntaCreateView(_Cadastro, CreateView):
    form_class, model, titulo, lista = JuntaForm, JuntaSolda, "Nova junta de solda", "solda-juntas"

    def get_initial(self):
        inicial = super().get_initial()
        area = AreaLocal.objects.filter(pk=self.request.GET.get("area") or 0).first()
        if area:
            inicial.update({"projeto": area.projeto_id, "area_local": area.pk})
        return inicial

    def get_success_url(self):
        return reverse("solda-junta-detail", args=[self.object.pk])


class JuntaUpdateView(_Cadastro, UpdateView):
    form_class, model, lista = JuntaForm, JuntaSolda, "solda-juntas"

    def get_success_url(self):
        return reverse("solda-junta-detail", args=[self.object.pk])


class SoldadorListView(AuthenticatedTemplateMixin, _Ctx, ListView):
    template_name = "soldagem/soldadores.html"
    context_object_name = "soldadores"
    queryset = Soldador.objects.select_related("funcionario", "funcionario__empresa")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["limite_taxa"] = LIMITE_TAXA_REPARO
        return context


class SoldadorCreateView(_Cadastro, CreateView):
    form_class, model, titulo, lista = SoldadorForm, Soldador, "Novo soldador", "solda-soldadores"


class SoldadorUpdateView(_Cadastro, UpdateView):
    form_class, model, lista = SoldadorForm, Soldador, "solda-soldadores"


class EPSListView(AuthenticatedTemplateMixin, _Ctx, ListView):
    template_name = "soldagem/eps.html"
    context_object_name = "lista"
    queryset = EPS.objects.all()


class EPSCreateView(_Cadastro, CreateView):
    form_class, model, titulo, lista = EPSForm, EPS, "Nova EPS (WPS)", "solda-eps"


class EPSUpdateView(_Cadastro, UpdateView):
    form_class, model, lista = EPSForm, EPS, "solda-eps"
