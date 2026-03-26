from django.conf import settings
from django.db import models
from django.db.models import JSONField
from django.urls import reverse

from core.choices import StatusImportacaoChoices, TipoImportacaoChoices
from core.models import TimeStampedModel


class ImportacaoArquivo(TimeStampedModel):
    tipo = models.CharField(max_length=30, choices=TipoImportacaoChoices.CHOICES)
    arquivo = models.FileField(upload_to="importacoes/")
    status = models.CharField(
        max_length=30,
        choices=StatusImportacaoChoices.CHOICES,
        default=StatusImportacaoChoices.PENDENTE,
    )
    iniciado_em = models.DateTimeField(null=True, blank=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="importacoes_arquivos",
    )
    observacoes = models.TextField(blank=True)
    resumo = JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nome_arquivo}"

    @property
    def nome_arquivo(self) -> str:
        return self.arquivo.name.split("/")[-1] if self.arquivo else ""

    @property
    def total_erros(self) -> int:
        return self.erros.count()

    def get_admin_url(self) -> str:
        return reverse("admin:importacoes_importacaoarquivo_change", args=[self.pk])

    def get_admin_erros_url(self) -> str:
        return f'{reverse("admin:importacoes_importacaoerro_changelist")}?importacao__id__exact={self.pk}'


class ImportacaoErro(models.Model):
    importacao = models.ForeignKey(
        ImportacaoArquivo,
        on_delete=models.CASCADE,
        related_name="erros",
    )
    linha = models.PositiveIntegerField()
    campo = models.CharField(max_length=100, blank=True)
    mensagem = models.TextField()

    class Meta:
        ordering = ("importacao_id", "linha", "id")

    def __str__(self):
        return f"{self.importacao.nome_arquivo} - linha {self.linha}"



