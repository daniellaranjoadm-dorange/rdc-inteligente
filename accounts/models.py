from django.conf import settings
from django.db import models


class PerfilAcesso(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        SUPERVISOR = "supervisor", "Supervisor"
        OPERADOR = "operador", "Operador"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_acesso",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.OPERADOR,
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    target_model = models.CharField(max_length=100, blank=True, default="")
    target_id = models.CharField(max_length=50, blank=True, default="")
    detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%d/%m/%Y %H:%M} - {self.action} - {self.target_model}#{self.target_id}"


