from django.core.exceptions import ValidationError
from django.db import models

from core.choices import EtapaConstrucaoNavalChoices, TipoAreaNavalChoices
from django.db.models import Q

from core.models import TimeStampedModel


class Projeto(TimeStampedModel):
    codigo = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=255)
    cliente = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    emails_relatorio = models.TextField(
        "E-mails que recebem o RDC", blank=True,
        help_text="Separe por vírgula ou um por linha. Recebem o PDF do RDC quando ele é fechado.",
    )

    @property
    def lista_emails_relatorio(self):
        import re
        return [e for e in re.split(r"[\s,;]+", self.emails_relatorio or "") if "@" in e]

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
    tipo = models.CharField(
        "Tipo", max_length=20, choices=TipoAreaNavalChoices.CHOICES, blank=True,
        help_text="Bloco, megabloco, anel, dique, cais, oficina...",
    )
    casco = models.CharField(
        "Casco / navio", max_length=60, blank=True,
        help_text="Identificação do navio, ex.: Handymax 01 ou número do casco.",
    )
    etapa = models.CharField("Etapa", max_length=20, choices=EtapaConstrucaoNavalChoices.CHOICES, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("projeto__nome", "descricao")
        constraints = [
            models.UniqueConstraint(fields=("projeto", "codigo"), name="uq_area_local_projeto_codigo")
        ]

    def __str__(self):
        return f"{self.projeto.codigo} - {self.codigo} - {self.descricao}"

    @property
    def resumo_naval(self):
        """Ex.: "Bloco · Handymax 01 · Edificação no dique / carreira" (so o que estiver preenchido)."""
        partes = [self.get_tipo_display() if self.tipo else "", self.casco, self.get_etapa_display() if self.etapa else ""]
        return " · ".join(p for p in partes if p)


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


