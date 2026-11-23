"""Painel de HH por bloco, disciplina, navio e etapa."""
from datetime import date, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import TemplateView

from cadastros.models import Projeto
from core.mixins import AuthenticatedTemplateMixin
from rdc.services.hh_service import montar_painel_hh, normalizar_periodo


def _data_ou_none(valor):
    """Data do filtro; texto invalido (ex.: 2026-13-45) vira None em vez de erro 500."""
    try:
        return parse_date(valor or "")
    except ValueError:
        return None


def _atalhos(hoje):
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    return [
        ("Esta semana", inicio_semana, hoje),
        ("Este mês", hoje.replace(day=1), hoje),
        ("Últimos 30 dias", hoje - timedelta(days=29), hoje),
        ("Últimos 12 meses", hoje - timedelta(days=364), hoje),
    ]


class PainelHHView(AuthenticatedTemplateMixin, TemplateView):
    template_name = "rdc/painel_hh.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.localdate()

        inicio = _data_ou_none(self.request.GET.get("inicio"))
        fim = _data_ou_none(self.request.GET.get("fim"))
        inicio, fim = normalizar_periodo(inicio, fim, hoje=hoje)

        projeto_id = self.request.GET.get("projeto") or ""
        projetos = Projeto.objects.filter(ativo=True).order_by("nome")
        if projeto_id and not projetos.filter(pk=projeto_id).exists():
            projeto_id = ""

        context.update(montar_painel_hh(inicio, fim, projeto_id=projeto_id or None))
        context.update({
            "inicio": inicio,
            "fim": fim,
            "projeto_id": str(projeto_id),
            "projetos": projetos,
            "atalhos": [
                {"rotulo": r, "inicio": i, "fim": f, "ativo": (i == inicio and f == fim)}
                for r, i, f in _atalhos(hoje)
            ],
        })
        return context
