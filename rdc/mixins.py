from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from core.mixins import RoleRequiredMixin
from rdc.models import RDC
from rdc.utils import rdc_is_editable


class RDCInlineUpdateBaseView(RoleRequiredMixin, View):
    allowed_roles = ["admin", "supervisor"]
    model = None
    allowed_fields = ()
    success_message = "Atualizado com sucesso."

    def dispatch(self, request, *args, **kwargs):
        self.rdc = get_object_or_404(RDC, pk=kwargs["pk"])
        self.obj = get_object_or_404(self.model, pk=kwargs["pk2"], rdc=self.rdc)
        return super().dispatch(request, *args, **kwargs)

    def get_field_value(self, field, value):
        return value

    def get_display_value(self, field):
        value = getattr(self.obj, field, "")
        if isinstance(value, bool):
            return "Sim" if value else "N?o"
        return str(value if value not in (None, "") else "-")

    def extra_payload(self):
        return {}

    def post_save(self):
        return None

    def post(self, request, *args, **kwargs):
        if not rdc_is_editable(self.rdc):
            return JsonResponse({"ok": False, "message": "RDC fechado para edi??o."}, status=403)

        field = (request.POST.get("field") or "").strip()
        value = request.POST.get("value")

        if field not in self.allowed_fields:
            return JsonResponse({"ok": False, "message": "Campo n?o permitido para edi??o inline."}, status=400)

        try:
            setattr(self.obj, field, self.get_field_value(field, value))
            self.obj.full_clean()
            self.obj.save()
            self.post_save()
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                msg = " ".join(
                    str(m)
                    for messages_list in exc.message_dict.values()
                    for m in messages_list
                )
            else:
                msg = " ".join(str(m) for m in exc.messages)
            return JsonResponse({"ok": False, "message": msg or "Dados inv?lidos."}, status=400)

        payload = {
            "ok": True,
            "message": self.success_message,
            "display": self.get_display_value(field),
        }
        payload.update(self.extra_payload())
        return JsonResponse(payload)
