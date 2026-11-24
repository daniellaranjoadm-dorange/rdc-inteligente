"""Diário de solda: soldadores qualificados, EPS (WPS), juntas, soldagem executada e ensaios (END)."""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel

DIAS_AVISO_QUALIFICACAO = 30


class ProcessoSoldagem(models.TextChoices):
    SMAW = "SMAW", "SMAW (eletrodo revestido)"
    FCAW = "FCAW", "FCAW (arame tubular)"
    GMAW = "GMAW", "GMAW (MIG/MAG)"
    GTAW = "GTAW", "GTAW (TIG)"
    SAW = "SAW", "SAW (arco submerso)"


class MetodoEND(models.TextChoices):
    VS = "VS", "Visual (VS)"
    LP = "LP", "Líquido penetrante (LP)"
    PM = "PM", "Partícula magnética (PM)"
    UT = "UT", "Ultrassom (UT)"
    RX = "RX", "Radiografia (RX)"


class TipoJunta(models.TextChoices):
    TOPO = "topo", "Topo (costura)"
    FILETE = "filete", "Filete"
    PENETRACAO_TOTAL = "penetracao_total", "Ângulo com penetração total"
    TUBULACAO = "tubulacao", "Tubulação (spool)"


class StatusJunta(models.TextChoices):
    PLANEJADA = "planejada", "Planejada"
    EM_EXECUCAO = "em_execucao", "Em execução"
    AGUARDANDO_END = "aguardando_end", "Aguardando END"
    REPROVADA = "reprovada", "Reprovada · reparo"
    APROVADA = "aprovada", "Aprovada"
    CONCLUIDA = "concluida", "Concluída (sem END)"


class Passe(models.TextChoices):
    COMPLETO = "completo", "Completa (todos os passes)"
    RAIZ = "raiz", "Raiz"
    ENCHIMENTO = "enchimento", "Enchimento"
    ACABAMENTO = "acabamento", "Acabamento"


class ResultadoEND(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    APROVADO = "aprovado", "Aprovado"
    REPROVADO = "reprovado", "Reprovado"


class DefeitoSolda(models.TextChoices):
    POROSIDADE = "porosidade", "Porosidade"
    FALTA_FUSAO = "falta_fusao", "Falta de fusão"
    FALTA_PENETRACAO = "falta_penetracao", "Falta de penetração"
    TRINCA = "trinca", "Trinca"
    INCLUSAO_ESCORIA = "inclusao_escoria", "Inclusão de escória"
    MORDEDURA = "mordedura", "Mordedura"
    DESALINHAMENTO = "desalinhamento", "Desalinhamento"
    OUTRO = "outro", "Outro"


class Soldador(TimeStampedModel):
    funcionario = models.OneToOneField("cadastros.Funcionario", on_delete=models.PROTECT, related_name="soldador")
    sinete = models.CharField("Sinete / estampa", max_length=20, unique=True,
                              help_text="Código que o soldador marca na junta.")
    processos = models.CharField("Processos qualificados", max_length=60, help_text="Ex.: FCAW, SMAW")
    posicoes = models.CharField("Posições", max_length=60, blank=True, help_text="Ex.: 1G a 4G, 3F")
    certificado = models.CharField("Certificado / registro", max_length=60, blank=True)
    validade_qualificacao = models.DateField("Validade da qualificação")
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("sinete",)
        verbose_name = "Soldador"
        verbose_name_plural = "Soldadores"

    def __str__(self):
        return f"{self.sinete} · {self.funcionario.nome}"

    def qualificado_em(self, data):
        return self.ativo and self.validade_qualificacao >= data

    @property
    def situacao_qualificacao(self):
        hoje = timezone.localdate()
        if self.validade_qualificacao < hoje:
            return "vencida"
        if (self.validade_qualificacao - hoje).days <= DIAS_AVISO_QUALIFICACAO:
            return "vencendo"
        return "valida"


class EPS(TimeStampedModel):
    codigo = models.CharField("Código da EPS (WPS)", max_length=40, unique=True)
    processo = models.CharField(max_length=10, choices=ProcessoSoldagem.choices)
    material = models.CharField("Material base", max_length=60, help_text="Ex.: aço naval AH36")
    espessura = models.CharField("Faixa de espessura", max_length=40, blank=True, help_text="Ex.: 6 a 25 mm")
    posicoes = models.CharField("Posições", max_length=60, blank=True)
    consumivel = models.CharField("Consumível", max_length=60, blank=True, help_text="Ex.: E71T-1C")
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ("codigo",)
        verbose_name = "EPS (WPS)"
        verbose_name_plural = "EPS (WPS)"

    def __str__(self):
        return f"{self.codigo} · {self.processo}"


class JuntaSolda(TimeStampedModel):
    projeto = models.ForeignKey("cadastros.Projeto", on_delete=models.CASCADE, related_name="juntas_solda")
    area_local = models.ForeignKey("cadastros.AreaLocal", on_delete=models.PROTECT, related_name="juntas_solda",
                                   verbose_name="Bloco / área")
    codigo = models.CharField("Identificação da junta", max_length=40, help_text="Ex.: B202-C14")
    descricao = models.CharField("Localização", max_length=160, blank=True, help_text="Ex.: costura do fundo, caverna 34")
    tipo = models.CharField(max_length=20, choices=TipoJunta.choices, default=TipoJunta.TOPO)
    comprimento_m = models.DecimalField("Comprimento (m)", max_digits=8, decimal_places=2)
    espessura_mm = models.DecimalField("Espessura (mm)", max_digits=6, decimal_places=1, null=True, blank=True)
    eps = models.ForeignKey(EPS, on_delete=models.PROTECT, null=True, blank=True, related_name="juntas",
                            verbose_name="EPS (WPS)")
    metodo_end = models.CharField("END exigido", max_length=2, choices=MetodoEND.choices, blank=True,
                                  help_text="Deixe vazio se a junta não exige ensaio.")
    status = models.CharField(max_length=20, choices=StatusJunta.choices, default=StatusJunta.PLANEJADA)

    class Meta:
        ordering = ("area_local__codigo", "codigo")
        constraints = [models.UniqueConstraint(fields=("projeto", "codigo"), name="uq_junta_projeto_codigo")]
        verbose_name = "Junta de solda"
        verbose_name_plural = "Juntas de solda"

    def __str__(self):
        return self.codigo

    @property
    def metros_soldados(self):
        total = self.execucoes.filter(reparo=False).aggregate(t=models.Sum("metros"))["t"] or Decimal("0")
        return min(total, self.comprimento_m)


class ExecucaoSolda(TimeStampedModel):
    junta = models.ForeignKey(JuntaSolda, on_delete=models.CASCADE, related_name="execucoes")
    soldador = models.ForeignKey(Soldador, on_delete=models.PROTECT, related_name="execucoes")
    data = models.DateField()
    metros = models.DecimalField("Metros soldados", max_digits=8, decimal_places=2)
    passe = models.CharField(max_length=20, choices=Passe.choices, default=Passe.COMPLETO)
    reparo = models.BooleanField("É reparo", default=False)
    rdc = models.ForeignKey("rdc.RDC", on_delete=models.SET_NULL, null=True, blank=True, related_name="soldas")
    observacao = models.CharField(max_length=255, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="soldas_lancadas")

    class Meta:
        ordering = ("-data", "-id")
        verbose_name = "Soldagem executada"
        verbose_name_plural = "Soldagens executadas"


class InspecaoEND(TimeStampedModel):
    junta = models.ForeignKey(JuntaSolda, on_delete=models.CASCADE, related_name="inspecoes")
    metodo = models.CharField(max_length=2, choices=MetodoEND.choices)
    ciclo = models.PositiveSmallIntegerField(default=1, help_text="1 = ensaio original; 2 em diante = após reparo")
    solicitado_em = models.DateField("Chamada de END em")
    inspecionado_em = models.DateField("Ensaiado em", null=True, blank=True)
    resultado = models.CharField(max_length=10, choices=ResultadoEND.choices, default=ResultadoEND.PENDENTE)
    metros_inspecionados = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    metros_reprovados = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    defeito = models.CharField(max_length=20, choices=DefeitoSolda.choices, blank=True)
    inspetor = models.CharField(max_length=120, blank=True)
    relatorio = models.CharField("Nº do relatório", max_length=60, blank=True)
    observacao = models.CharField(max_length=255, blank=True)
    soldadores = models.ManyToManyField(Soldador, blank=True, related_name="inspecoes",
                                        help_text="Quem soldou o trecho ensaiado (para a taxa de reparo).")

    class Meta:
        ordering = ("-solicitado_em", "-id")
        verbose_name = "Ensaio (END)"
        verbose_name_plural = "Ensaios (END)"

    def __str__(self):
        return f"{self.get_metodo_display()} · {self.junta} · ciclo {self.ciclo}"

    @property
    def dias_aguardando(self):
        if self.resultado != ResultadoEND.PENDENTE:
            return 0
        return (timezone.localdate() - self.solicitado_em).days
