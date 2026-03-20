from django.db import models

from core.models import TimeStampedModel


class RegistroCatraca(TimeStampedModel):
    data = models.DateField()
    matricula = models.CharField(max_length=30, db_index=True)
    funcionario = models.ForeignKey(
        "cadastros.Funcionario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_catraca",
    )
    projeto = models.ForeignKey(
        "cadastros.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_catraca",
    )
    entrada_1 = models.TimeField(null=True, blank=True)
    saida_1 = models.TimeField(null=True, blank=True)
    entrada_2 = models.TimeField(null=True, blank=True)
    saida_2 = models.TimeField(null=True, blank=True)
    presente = models.BooleanField(default=False)
    origem_arquivo = models.CharField(max_length=255)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ("-data", "matricula")
        constraints = [
            models.UniqueConstraint(
                fields=("data", "matricula"),
                name="uq_registro_catraca_data_matricula",
            )
        ]

    def __str__(self):
        return f"{self.data} - {self.matricula}"
