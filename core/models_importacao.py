from django.conf import settings
from django.db import models


class ImportJob(models.Model):
    TIPO_FUNCIONARIOS = "funcionarios"
    TIPO_CATRACA = "catraca"
    TIPO_ALOCACAO = "alocacao"
    TIPO_PROJETOS = "projetos"
    TIPO_OUTRO = "outro"

    TIPOS = [
        (TIPO_FUNCIONARIOS, "Funcionários"),
        (TIPO_CATRACA, "Catraca"),
        (TIPO_ALOCACAO, "Alocação"),
        (TIPO_PROJETOS, "Projetos"),
        (TIPO_OUTRO, "Outro"),
    ]

    STATUS_PENDENTE = "pendente"
    STATUS_PROCESSANDO = "processando"
    STATUS_CONCLUIDO = "concluido"
    STATUS_CONCLUIDO_PARCIAL = "concluido_parcial"
    STATUS_ERRO = "erro"

    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_PROCESSANDO, "Processando"),
        (STATUS_CONCLUIDO, "Concluído"),
        (STATUS_CONCLUIDO_PARCIAL, "Concluído com ressalvas"),
        (STATUS_ERRO, "Erro"),
    ]

    tipo = models.CharField(max_length=50, choices=TIPOS)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE,
    )
    arquivo = models.FileField(upload_to="importacoes/%Y/%m/", blank=True, null=True)
    nome_arquivo_original = models.CharField(max_length=255, blank=True, default="")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_jobs",
    )

    total_linhas = models.PositiveIntegerField(default=0)
    linhas_processadas = models.PositiveIntegerField(default=0)
    linhas_com_erro = models.PositiveIntegerField(default=0)

    resumo = models.JSONField(default=dict, blank=True)
    erros = models.JSONField(default=list, blank=True)
    observacoes = models.TextField(blank=True, default="")

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    iniciado_em = models.DateTimeField(blank=True, null=True)
    finalizado_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Importação"
        verbose_name_plural = "Importações"

    def __str__(self):
        return f"{self.get_tipo_display()} #{self.pk} - {self.get_status_display()}"
