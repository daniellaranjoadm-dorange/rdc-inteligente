from django.contrib import admin
from .models import PerfilAcesso, AuditLog


@admin.register(PerfilAcesso)
class PerfilAcessoAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    list_filter = ("role",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "target_model", "target_id")
    search_fields = ("user__username", "action", "target_model", "target_id", "detail")
    list_filter = ("action", "target_model", "created_at")

