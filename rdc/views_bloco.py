"""Visão geral dos blocos e página do bloco com liberação para edificação."""
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from cadastros.models import AreaLocal, Projeto
from core.mixins import AuthenticatedTemplateMixin
from rdc.services.bloco_service import detalhe_bloco, liberacao_blocos


def _pode_enviar(user):
    if user.is_superuser:
        return True
    perfil = getattr(user, "perfil_acesso", None)
    return bool(perfil and perfil.role in ("admin", "supervisor"))


class BlocosView(AuthenticatedTemplateMixin, TemplateView):
    template_name = "rdc/blocos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        projetos = Projeto.objects.filter(ativo=True).order_by("nome")
        projeto_id = self.request.GET.get("projeto") or ""
        if projeto_id and not projetos.filter(pk=projeto_id).exists():
            projeto_id = ""
        cascos = sorted(set(AreaLocal.objects.exclude(casco="").values_list("casco", flat=True)))
        casco = self.request.GET.get("casco") if self.request.GET.get("casco") in cascos else ""
        blocos = liberacao_blocos(projeto_id=projeto_id or None)
        if casco:
            blocos = [b for b in blocos if b["area"].casco == casco]
        context.update({
            "blocos": blocos, "projetos": projetos, "projeto_id": str(projeto_id), "cascos": cascos, "casco": casco,
            "liberados": sum(b["liberado"] for b in blocos),
            "pode_enviar": _pode_enviar(self.request.user),
        })
        return context


class BlocoDetalheView(AuthenticatedTemplateMixin, TemplateView):
    template_name = "rdc/bloco_detalhe.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        area = get_object_or_404(AreaLocal.objects.select_related("projeto", "disciplina_padrao"), pk=kwargs["pk"])
        context["area"] = area
        context.update(detalhe_bloco(area))
        return context
