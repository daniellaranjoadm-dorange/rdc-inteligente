"""Punch list: pendências por bloco/compartimento, com foto, responsável, prazo e verificação."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class Categoria(models.TextChoices):
    A = "A", "A · impede conclusão / teste"
    B = "B", "B · antes da entrega"
    C = "C", "C · acabamento / menor"


class Origem(models.TextChoices):
    INTERNA = "interna", "Inspeção interna (CQ)"
    FISCAL = "fiscal", "Fiscal / armador"
    CLASSE = "classe", "Sociedade classificadora"
    COMISSIONAMENTO = "comissionamento", "Comissionamento / testes"
    SEGURANCA = "seguranca", "Segurança"


class Status(models.TextChoices):
    ABERTA = "aberta", "Aberta"
    EM_ANDAMENTO = "em_andamento", "Em andamento"
    AGUARDANDO_VERIFICACAO = "aguardando_verificacao", "Aguardando verificação"
    FECHADA = "fechada", "Fechada"
    CANCELADA = "cancelada", "Cancelada"


STATUS_EM_ABERTO = (Status.ABERTA, Status.EM_ANDAMENTO, Status.AGUARDANDO_VERIFICACAO)


class PunchItem(TimeStampedModel):
    projeto = models.ForeignKey("cadastros.Projeto", on_delete=models.CASCADE, related_name="punch_itens")
    numero = models.PositiveIntegerField(editable=False)
    area_local = models.ForeignKey("cadastros.AreaLocal", on_delete=models.PROTECT, related_name="punch_itens",
                                   verbose_name="Bloco / área")
    compartimento = models.CharField(max_length=120, blank=True, help_text="Ex.: praça de máquinas, convés 2, tanque 3BB")
    disciplina = models.ForeignKey("cadastros.Disciplina", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="punch_itens")
    descricao = models.TextField("O que está pendente")
    categoria = models.CharField(max_length=1, choices=Categoria.choices, default=Categoria.B)
    origem = models.CharField(max_length=20, choices=Origem.choices, default=Origem.INTERNA)
    responsavel_empresa = models.ForeignKey("cadastros.Empresa", on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name="punch_itens", verbose_name="Empresa responsável")
    responsavel = models.CharField("Responsável", max_length=120, blank=True)
    prazo = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ABERTA)
    reaberturas = models.PositiveSmallIntegerField(default=0)
    aberta_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="punch_abertos")
    resolvida_em = models.DateTimeField(null=True, blank=True)
    resolvida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="punch_resolvidos")
    nota_resolucao = models.TextField(blank=True)
    fechada_em = models.DateTimeField(null=True, blank=True)
    fechada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="punch_fechados")
    nota_verificacao = models.TextField(blank=True)

    class Meta:
        ordering = ("categoria", "prazo", "numero")
        constraints = [models.UniqueConstraint(fields=("projeto", "numero"), name="uq_punch_projeto_numero")]
        verbose_name = "Pendência (punch)"
        verbose_name_plural = "Punch list"

    def __str__(self):
        return f"{self.codigo} · {self.descricao[:50]}"

    @property
    def codigo(self):
        return f"PL-{self.numero:04d}"

    @property
    def em_aberto(self):
        return self.status in STATUS_EM_ABERTO

    @property
    def vencida(self):
        return bool(self.prazo and self.em_aberto and self.prazo < timezone.localdate())

    @property
    def dias_aberta(self):
        fim = self.fechada_em or timezone.now()
        return (fim - self.created_at).days


def _caminho_foto(instance, filename):
    return f"punch/{instance.item.projeto_id}/{instance.item_id}/{uuid.uuid4().hex}.jpg"


def _caminho_miniatura(instance, filename):
    return f"punch/{instance.item.projeto_id}/{instance.item_id}/mini_{uuid.uuid4().hex}.jpg"


class PunchFoto(TimeStampedModel):
    class Momento(models.TextChoices):
        ABERTURA = "abertura", "Na abertura"
        RESOLUCAO = "resolucao", "Na resolução"

    item = models.ForeignKey(PunchItem, on_delete=models.CASCADE, related_name="fotos")
    momento = models.CharField(max_length=12, choices=Momento.choices, default=Momento.ABERTURA)
    imagem = models.ImageField(upload_to=_caminho_foto)
    miniatura = models.ImageField(upload_to=_caminho_miniatura)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="punch_fotos")

    class Meta:
        ordering = ("created_at", "id")
