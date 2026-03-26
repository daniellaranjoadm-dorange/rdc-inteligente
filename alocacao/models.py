from django.db import models

from core.choices import TurnoChoices
from core.models import TimeStampedModel


class FuncionarioProjeto(TimeStampedModel):
    funcionario = models.ForeignKey(
        "cadastros.Funcionario",
        on_delete=models.CASCADE,
        related_name="alocacoes",
    )
    projeto = models.ForeignKey(
        "cadastros.Projeto",
        on_delete=models.CASCADE,
        related_name="alocacoes_funcionarios",
    )
    disciplina = models.ForeignKey(
        "cadastros.Disciplina",
        on_delete=models.CASCADE,
        related_name="alocacoes_funcionarios",
    )
    equipe = models.ForeignKey(
        "cadastros.Equipe",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alocacoes_funcionarios",
    )
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("-data_inicio", "funcionario__nome")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=models.F("data_inicio")),
                name="ck_alocacao_data_fim_gte_inicio",
            )
        ]

    def __str__(self):
        return f"{self.funcionario} -> {self.projeto} / {self.disciplina}"

    def esta_valido_em(self, data_referencia):
        if not self.ativo:
            return False
        if self.data_inicio and data_referencia < self.data_inicio:
            return False
        if self.data_fim and data_referencia > self.data_fim:
            return False
        return True


class HistogramaPlanejado(TimeStampedModel):
    projeto = models.ForeignKey("cadastros.Projeto", on_delete=models.CASCADE, related_name="histogramas")
    area_local = models.ForeignKey("cadastros.AreaLocal", on_delete=models.CASCADE, related_name="histogramas")
    disciplina = models.ForeignKey("cadastros.Disciplina", on_delete=models.CASCADE, related_name="histogramas")
    equipe = models.ForeignKey("cadastros.Equipe", on_delete=models.CASCADE, related_name="histogramas")
    funcao = models.ForeignKey("cadastros.Funcao", on_delete=models.CASCADE, related_name="histogramas")
    quantidade_planejada = models.PositiveIntegerField()
    data = models.DateField()
    turno = models.CharField(max_length=20, choices=TurnoChoices.CHOICES, default=TurnoChoices.INTEGRAL)

    class Meta:
        ordering = ("-data", "projeto__nome")
        constraints = [
            models.UniqueConstraint(
                fields=("projeto", "area_local", "disciplina", "equipe", "funcao", "data", "turno"),
                name="uq_histograma_planejado_contexto",
            )
        ]

    def __str__(self):
        return f"{self.data} - {self.equipe} - {self.funcao} ({self.quantidade_planejada})"

