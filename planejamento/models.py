from django.db import models

from core.choices import TurnoChoices
from core.models import TimeStampedModel

class AtividadeCronograma(TimeStampedModel):
    projeto = models.ForeignKey("cadastros.Projeto", on_delete=models.CASCADE, related_name="atividades_cronograma")
    area_local = models.ForeignKey("cadastros.AreaLocal", on_delete=models.CASCADE, related_name="atividades_cronograma")
    disciplina = models.ForeignKey("cadastros.Disciplina", on_delete=models.CASCADE, related_name="atividades_cronograma")
    codigo_atividade = models.CharField(max_length=50)
    descr_atividade = models.CharField(max_length=255)
    codigo_subatividade = models.CharField(max_length=50, blank=True)
    descr_subatividade = models.CharField(max_length=255, blank=True)
    qtd_escopo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unidade = models.CharField(max_length=20)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    turno = models.CharField(max_length=20, choices=TurnoChoices.CHOICES, default=TurnoChoices.INTEGRAL)
    status_planejado = models.CharField(max_length=50)

    class Meta:
        ordering = ("data_inicio", "codigo_atividade")
        constraints = [
            models.CheckConstraint(condition=models.Q(data_fim__gte=models.F("data_inicio")), name="ck_cronograma_data_fim_gte_inicio")
        ]

    def __str__(self):
        return f"{self.codigo_atividade} - {self.descr_atividade}"

