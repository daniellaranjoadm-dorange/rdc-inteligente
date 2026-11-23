"""Endpoint para um agendador externo disparar os alertas do dia (protegido por token)."""
import hmac

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from rdc.services.email_service import enviar_alertas_por_email


@method_decorator(csrf_exempt, name="dispatch")
class TarefaAlertasView(View):
    def post(self, request):
        esperado = getattr(settings, "ALERTAS_TOKEN", "")
        recebido = request.headers.get("X-Tarefa-Token", "")
        if not esperado or not hmac.compare_digest(esperado, recebido):
            return JsonResponse({"ok": False, "erro": "não autorizado"}, status=403)
        try:
            n = enviar_alertas_por_email()
        except ValueError as exc:
            return JsonResponse({"ok": False, "erro": str(exc)}, status=503)
        return JsonResponse({"ok": True, "emails": n})
