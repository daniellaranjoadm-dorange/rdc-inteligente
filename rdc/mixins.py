def rdc_is_editable(rdc):
    return getattr(rdc, "status", "") != "fechado"


from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from core.mixins import RoleRequiredMixin
from rdc.models import RDC


class RDCInlineUpdateBaseView(RoleRequiredMixin, View):
    allowed_roles = ["admin", "supervisor"]
    model = None
    allowed_fields = ()

    def dispatch(self, request, *args, **kwargs):
        self.rdc = get_object_or_404(RDC, pk=kwargs["pk"])
        self.obj = get_object_or_404(self.model, pk=kwargs["pk2"], rdc=self.rdc)
        return super().dispatch(request, *args, **kwargs)

    def get_field_value(self, field, value):
        # convers?o simples
        if value in ("true", "True", "1"):
            return True
        if value in ("false", "False", "0"):
            return False
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
            return JsonResponse({"ok": False}, status=403)

        field = (request.POST.get("field") or "").strip()
        value = request.POST.get("value")

        if field not in self.allowed_fields:
            return JsonResponse(
                {"ok": False, "field": field, "value": str(value)},
                status=400,
            )

        try:
            parsed_value = self.get_field_value(field, value)
            setattr(self.obj, field, parsed_value)
            self.obj.save(update_fields=[field])
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

            return JsonResponse(
                {
                    "ok": False,
                    "field": field,
                    "value": str(value),
                    "error": msg,
                },
                status=400,
            )

        except Exception as exc:
            return JsonResponse(
                {
                    "ok": False,
                    "field": field,
                    "value": str(value),
                    "error": str(exc),
                },
                status=400,
            )

        payload = {
            "ok": True,
            "field": field,
            "value": str(value),
            "display": self.get_display_value(field),
        }
        payload.update(self.extra_payload())
        return JsonResponse(payload)


