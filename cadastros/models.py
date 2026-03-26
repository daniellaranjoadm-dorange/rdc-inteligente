from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel


class Projeto(TimeStampedModel):
    codigo = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=255)
    cliente = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("nome",)

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Disciplina(TimeStampedModel):
    codigo = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class Empresa(TimeStampedModel):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, blank=True, default="")
    ativa = models.BooleanField(default=True)
    cadastro_pendente = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ("nome",)
        constraints = [
            models.UniqueConstraint(
                fields=("cnpj",),
                condition=~Q(cnpj=""),
                name="uq_empresa_cnpj_preenchido",
            )
        ]

    def __str__(self):
        pendencia = " [pendente]" if self.cadastro_pendente else ""
        return f"{self.nome}{pendencia}"


class Funcao(TimeStampedModel):
    codigo = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=120)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ("nome",)

    def __str__(self):
        return self.nome


class Funcionario(TimeStampedModel):
    matricula = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, blank=True)
    rg = models.CharField(max_length=20, blank=True)
    funcao = models.ForeignKey("cadastros.Funcao", on_delete=models.PROTECT, related_name="funcionarios")
    empresa = models.ForeignKey("cadastros.Empresa", on_delete=models.PROTECT, related_name="funcionarios")
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("nome",)

    def __str__(self):
        return f"{self.matricula} - {self.nome}"


class AreaLocal(TimeStampedModel):
    projeto = models.ForeignKey("cadastros.Projeto", on_delete=models.CASCADE, related_name="areas")
    codigo = models.CharField(max_length=30)
    descricao = models.CharField(max_length=255)
    disciplina_padrao = models.ForeignKey(
        "cadastros.Disciplina",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="areas_padrao",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("projeto__nome", "descricao")
        constraints = [
            models.UniqueConstraint(fields=("projeto", "codigo"), name="uq_area_local_projeto_codigo")
        ]

    def __str__(self):
        return f"{self.projeto.codigo} - {self.codigo} - {self.descricao}"


class Equipe(TimeStampedModel):
    codigo = models.CharField(max_length=30)
    nome = models.CharField(max_length=120)
    disciplina = models.ForeignKey("cadastros.Disciplina", on_delete=models.PROTECT, related_name="equipes")
    encarregado = models.ForeignKey(
        "cadastros.Funcionario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipes_como_encarregado",
    )
    empresa = models.ForeignKey("cadastros.Empresa", on_delete=models.PROTECT, related_name="equipes")
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ("nome",)
        constraints = [
            models.UniqueConstraint(fields=("codigo", "disciplina", "empresa"), name="uq_equipe_codigo_disciplina_empresa")
        ]

    def clean(self):
        if self.encarregado and self.encarregado.empresa_id != self.empresa_id:
            raise ValidationError("O encarregado deve pertencer Ã  mesma empresa da equipe.")

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


