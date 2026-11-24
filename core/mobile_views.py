from django.views import View
from django.views.generic import TemplateView

from core.mixins import AuthenticatedTemplateMixin


class MobileHomeView(AuthenticatedTemplateMixin, TemplateView):
    """Inicio do app no celular. Exige login: sem isso a tela parecia logada sem estar."""

    template_name = "mobile_home.html"


def service_worker_view(request):
    """Service worker servido na raiz para controlar o site inteiro (em /static/ ele só controlaria /static/)."""
    from pathlib import Path

    from django.conf import settings
    from django.http import HttpResponse

    caminho = Path(settings.BASE_DIR) / "static" / "sw.js"
    resposta = HttpResponse(caminho.read_text(encoding="utf-8"), content_type="application/javascript; charset=utf-8")
    resposta["Service-Worker-Allowed"] = "/"
    resposta["Cache-Control"] = "no-cache"
    return resposta


class TelasOfflineView(AuthenticatedTemplateMixin, View):
    """Telas de campo que o celular deve guardar para abrir sem sinal (RDCs recentes e seus formulários)."""

    def get(self, request):
        from datetime import timedelta

        from django.http import JsonResponse
        from django.utils import timezone

        from rdc.models import RDC

        hoje = timezone.localdate()
        urls = ["/m/", "/rdc/blocos/", "/punch/", "/punch/nova/", "/soldagem/juntas/"]
        rdcs = RDC.objects.filter(data__gte=hoje - timedelta(days=2)).exclude(status="fechado").order_by("-data")[:15]
        for rdc in rdcs:
            base = f"/rdc/{rdc.pk}/"
            urls += [base, f"{base}paralisacoes/nova/", f"{base}ocorrencias/nova/", f"{base}equipamentos/novo/",
                     f"{base}fotos/enviar/"]
        try:
            from soldagem.models import JuntaSolda, StatusJunta
            juntas = JuntaSolda.objects.filter(status__in=[StatusJunta.EM_EXECUCAO, StatusJunta.PLANEJADA,
                                                           StatusJunta.REPROVADA]).order_by("-updated_at")[:30]
            urls += [f"/soldagem/juntas/{j.pk}/" for j in juntas]
        except Exception:  # noqa: BLE001 - lista é só um atalho; nunca derruba o modo campo
            pass
        return JsonResponse({"urls": urls})
