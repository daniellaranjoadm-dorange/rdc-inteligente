from datetime import timedelta
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.choices import (
    OrigemAtividadeChoices,
    StatusRDCChoices,
    StatusValidacaoChoices,
    TipoValidacaoChoices,
    TurnoChoices,
)
from core.models import TimeStampedModel




class SyncableMobileMixin(models.Model):
    mobile_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    sync_updated_at = models.DateTimeField(default=timezone.now, db_index=True)
    sync_deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    @property
    def is_sync_deleted(self):
        return self.sync_deleted_at is not None

    def marcar_excluido_sync(self):
        self.sync_deleted_at = timezone.now()
        self.sync_updated_at = timezone.now()
        self.save(update_fields=["sync_deleted_at", "sync_updated_at"])

    def restaurar_sync(self):
        self.sync_deleted_at = None
        self.sync_updated_at = timezone.now()
        self.save(update_fields=["sync_deleted_at", "sync_updated_at"])


class RDC(SyncableMobileMixin, TimeStampedModel):
    projeto = models.ForeignKey(
        "cadastros.Projeto",
        on_delete=models.PROTECT,
        related_name="rdcs",
    )
    area_local = models.ForeignKey(
        "cadastros.AreaLocal",
        on_delete=models.PROTECT,
        related_name="rdcs",
    )
    disciplina = models.ForeignKey(
        "cadastros.Disciplina",
        on_delete=models.PROTECT,
        related_name="rdcs",
    )
    data = models.DateField()
    turno = models.CharField(max_length=20, choices=TurnoChoices.CHOICES)
    supervisor = models.ForeignKey(
        "cadastros.Funcionario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rdcs_supervisionados",
    )
    dia_semana = models.CharField(max_length=20, blank=True)
    condicao_area = models.CharField(max_length=255, blank=True)
    clima_manha = models.CharField(max_length=60, blank=True)
    clima_tarde = models.CharField(max_length=60, blank=True)
    clima_noite = models.CharField(max_length=60, blank=True)
    horario_inicio = models.TimeField(null=True, blank=True)
    horario_fim = models.TimeField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusRDCChoices.CHOICES,
        default=StatusRDCChoices.RASCUNHO,
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rdcs_criados",
    )
    fechado_em = models.DateTimeField(null=True, blank=True)
    fechado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rdcs_fechados",
    )
    permite_edicao_pos_fechamento = models.BooleanField(default=False)
    justificativa_fechamento = models.TextField(blank=True)

    class Meta:
        ordering = ("-data", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("projeto", "area_local", "disciplina", "data", "turno"),
                name="uq_rdc_contexto_diario",
            )
        ]

    def __str__(self):
        return f"RDC {self.projeto.codigo} - {self.area_local.codigo} - {self.data} - {self.turno}"

    def save(self, *args, **kwargs):
        self.sync_updated_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_fechado(self):
        return str(self.status).lower() == "fechado"

    def usuario_pode_editar(self, user):
        if not getattr(user, "is_authenticated", False):
            return False
        if not self.is_fechado:
            return True
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        permite_pos_fechamento = self.__dict__.get("permite_edicao_pos_fechamento", False)
        return permite_pos_fechamento and self.criado_por_id == getattr(user, "id", None)

    def usuario_pode_forcar_fechamento(self, user):
        return bool(
            getattr(user, "is_authenticated", False)
            and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        )

    def usuario_pode_reabrir(self, user):
        return self.usuario_pode_forcar_fechamento(user)

    def usuario_pode_fechar(self, user):
        if not getattr(user, "is_authenticated", False):
            return False

        perfil = getattr(user, "perfil_acesso", None)
        if perfil and getattr(perfil, "role", None) in {"admin", "supervisor"}:
            return True

        return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))

    @property
    def status_workflow_label(self):
        mapa = {
            "rascunho": "Em elaborAção",
            "pre_preenchido": "Pré-preenchido",
            "em_revisao": "Em revisão",
            "aprovado": "Aprovado",
            "fechado": "Fechado",
        }
        return mapa.get(str(self.status or "").lower(), self.status)

    @property
    def workflow_badge(self):
        mapa = {
            "rascunho": "secondary",
            "pre_preenchido": "info",
            "em_revisao": "warning",
            "aprovado": "primary",
            "fechado": "success",
        }
        return mapa.get(str(self.status or "").lower(), "secondary")

    def usuario_pode_enviar_revisao(self, user):
        return self.usuario_pode_editar(user) and str(self.status).lower() in {"rascunho", "pre_preenchido"}

    def usuario_pode_aprovar(self, user):
        return bool(
            getattr(user, "is_authenticated", False)
            and str(self.status).lower() == "em_revisao"
            and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        )

    def usuario_pode_devolver(self, user):
        return self.usuario_pode_aprovar(user)


class RDCAtividade(SyncableMobileMixin, TimeStampedModel):
    rdc = models.ForeignKey(
        "rdc.RDC",
        on_delete=models.CASCADE,
        related_name="atividades",
    )
    atividade_cronograma = models.ForeignKey(
        "planejamento.AtividadeCronograma",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rdcs_gerados",
    )
    codigo_atividade = models.CharField(max_length=50)
    descr_atividade = models.CharField(max_length=255)
    codigo_subatividade = models.CharField(max_length=50, blank=True)
    descr_subatividade = models.CharField(max_length=255, blank=True)
    qtd_escopo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    qtd_executada = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comentarios = models.TextField(blank=True)
    origem = models.CharField(
        max_length=20,
        choices=OrigemAtividadeChoices.CHOICES,
        default=OrigemAtividadeChoices.CRONOGRAMA,
    )
    obrigatoria = models.BooleanField(default=False)
    ativa_no_dia = models.BooleanField(default=True)

    class Meta:
        ordering = ("codigo_atividade", "codigo_subatividade")
        constraints = [
            models.UniqueConstraint(
                fields=("rdc", "codigo_atividade", "codigo_subatividade", "origem"),
                name="uq_rdc_atividade_unica",
            )
        ]

    def save(self, *args, **kwargs):
        self.sync_updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_atividade} - {self.descr_atividade}"


class RDCFuncionario(SyncableMobileMixin, TimeStampedModel):
    rdc = models.ForeignKey(
        "rdc.RDC",
        on_delete=models.CASCADE,
        related_name="funcionarios",
    )
    funcionario = models.ForeignKey(
        "cadastros.Funcionario",
        on_delete=models.PROTECT,
        related_name="rdcs_participacoes",
    )
    equipe = models.ForeignKey(
        "cadastros.Equipe",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rdcs_funcionarios",
    )
    funcao = models.ForeignKey(
        "cadastros.Funcao",
        on_delete=models.PROTECT,
        related_name="rdcs_funcionarios",
    )
    matricula = models.CharField(max_length=30)
    nome = models.CharField(max_length=255)
    hora_normal = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("8.00"))
    hora_extra = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    hh_total = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    presente_catraca = models.BooleanField(default=False)
    elegivel = models.BooleanField(default=True)
    motivo_bloqueio = models.CharField(max_length=255, blank=True)
    confirmado_supervisor = models.BooleanField(default=False)

    liberado_sem_catraca = models.BooleanField(default=False)
    justificativa_liberacao = models.TextField(blank=True)
    liberado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rdcs_funcionarios_liberados",
    )
    liberado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("nome",)
        constraints = [
            models.UniqueConstraint(
                fields=("rdc", "funcionario"),
                name="uq_rdc_funcionario_unico",
            )
        ]

    def __str__(self):
        return f"{self.nome} - {self.rdc}"

    @property
    def pode_apontar(self):
        return bool(self.elegivel)

    def atualizar_status_elegibilidade(self):
        self.elegivel = True
        self.motivo_bloqueio = ""

        if self.funcionario_id and not self.funcionario.ativo:
            self.elegivel = False
            self.motivo_bloqueio = "Funcionário inativo."
            return

        if not self.presente_catraca:
            if self.liberado_sem_catraca:
                self.elegivel = True
                self.motivo_bloqueio = "Sem catraca no dia €” liberado manualmente."
            else:
                self.elegivel = False
                self.motivo_bloqueio = "Sem catraca no dia."

    def registrar_liberacao_sem_catraca(self, usuario, justificativa):
        self.liberado_sem_catraca = True
        self.justificativa_liberacao = (justificativa or "").strip()
        self.liberado_por = usuario if getattr(usuario, "is_authenticated", False) else None
        self.liberado_em = timezone.now()
        self.atualizar_status_elegibilidade()

    def remover_liberacao_sem_catraca(self):
        self.liberado_sem_catraca = False
        self.justificativa_liberacao = ""
        self.liberado_por = None
        self.liberado_em = None
        self.atualizar_status_elegibilidade()

    def clean(self):
        if self.funcionario_id and self.funcao_id and self.funcao_id != self.funcionario.funcao_id:
            raise ValidationError(
                {"funcao": "A função lançada diverge da função cadastrada do funcionário."}
            )

        if self.liberado_sem_catraca:
            if self.presente_catraca:
                raise ValidationError(
                    {
                        "liberado_sem_catraca": (
                            "Não é possível liberar manualmente um funcionário que já possui catraca no dia."
                        )
                    }
                )
            if not self.justificativa_liberacao.strip():
                raise ValidationError(
                    {"justificativa_liberacao": "Informe a justificativa da liberAção manual."}
                )

        self.atualizar_status_elegibilidade()

    def save(self, *args, **kwargs):
        self.hh_total = (self.hora_normal or Decimal("0.00")) + (self.hora_extra or Decimal("0.00"))

        if self.presente_catraca and self.liberado_sem_catraca:
            self.liberado_sem_catraca = False
            self.justificativa_liberacao = ""
            self.liberado_por = None
            self.liberado_em = None

        self.atualizar_status_elegibilidade()
        super().save(*args, **kwargs)


class RDCApontamento(SyncableMobileMixin, TimeStampedModel):
    rdc = models.ForeignKey(
        "rdc.RDC",
        on_delete=models.CASCADE,
        related_name="apontamentos",
    )
    rdc_funcionario = models.ForeignKey(
        "rdc.RDCFuncionario",
        on_delete=models.CASCADE,
        related_name="apontamentos",
    )
    rdc_atividade = models.ForeignKey(
        "rdc.RDCAtividade",
        on_delete=models.CASCADE,
        related_name="apontamentos",
    )
    horas = models.DecimalField(max_digits=6, decimal_places=2)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ("rdc_funcionario__nome",)
        constraints = [
            models.UniqueConstraint(
                fields=("rdc", "rdc_funcionario", "rdc_atividade"),
                name="uq_rdc_apontamento_unico",
            )
        ]

    def clean(self):
        if not self.rdc_id or not self.rdc_funcionario_id or not self.rdc_atividade_id:
            return

        if self.rdc_funcionario.rdc_id != self.rdc_id:
            raise ValidationError(
                {"rdc_funcionario": "O funcionário informado não pertence a este RDC."}
            )

        if self.rdc_atividade.rdc_id != self.rdc_id:
            raise ValidationError(
                {"rdc_atividade": "A atividade informada não pertence a este RDC."}
            )

        if not self.rdc_funcionario.pode_apontar:
            raise ValidationError(
                {
                    "rdc_funcionario": (
                        self.rdc_funcionario.motivo_bloqueio
                        or "Funcionário não está elegível para apontamento."
                    )
                }
            )

        if self.horas is not None and self.horas <= 0:
            raise ValidationError({"horas": "As horas apontadas devem ser maiores que zero."})

    def save(self, *args, **kwargs):
        self.sync_updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rdc_funcionario} -> {self.rdc_atividade}"


class RDCValidacao(models.Model):
    rdc = models.ForeignKey(
        "rdc.RDC",
        on_delete=models.CASCADE,
        related_name="validacoes",
    )
    tipo = models.CharField(max_length=50, choices=TipoValidacaoChoices.CHOICES)
    referencia = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusValidacaoChoices.CHOICES,
        default=StatusValidacaoChoices.INFO,
    )
    mensagem = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.status}"


class RDCAuditoria(models.Model):
    rdc = models.ForeignKey(
        "rdc.RDC",
        on_delete=models.CASCADE,
        related_name="auditorias",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rdc_auditorias",
    )
    acao = models.CharField(max_length=40)
    secao = models.CharField(max_length=40, blank=True)
    referencia_id = models.PositiveIntegerField(null=True, blank=True)
    resumo = models.CharField(max_length=255)
    detalhe = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.acao} - RDC {self.rdc_id}"


class PerfilOperacionalUsuario(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_operacional_rdc",
    )
    funcionario = models.ForeignKey(
        "cadastros.Funcionario",
        on_delete=models.PROTECT,
        related_name="perfis_operacionais_rdc",
    )
    projeto_padrao = models.ForeignKey(
        "cadastros.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfis_operacionais_rdc",
    )
    disciplina_padrao = models.ForeignKey(
        "cadastros.Disciplina",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfis_operacionais_rdc",
    )
    equipe_padrao = models.ForeignKey(
        "cadastros.Equipe",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfis_operacionais_rdc",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Perfil operacional do usuário"
        verbose_name_plural = "Perfis operacionais dos usuários"
        ordering = ("user__username",)

    def __str__(self):
        return f"{self.user} -> {self.funcionario}"


class CalendarioPlanejamento(TimeStampedModel):
    projeto = models.ForeignKey(
        "cadastros.Projeto",
        on_delete=models.CASCADE,
        related_name="calendarios_planejamento",
    )
    data = models.DateField()
    ano = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    semana_codigo = models.CharField(max_length=10, db_index=True)
    semana_numero = models.PositiveSmallIntegerField()
    semana_label = models.CharField(max_length=40, blank=True)
    data_inicio_semana = models.DateField()
    data_fim_semana = models.DateField()
    dia_semana = models.PositiveSmallIntegerField(help_text="0=Segunda ... 6=Domingo")
    dia_semana_nome = models.CharField(max_length=20)
    eh_dia_util = models.BooleanField(default=True)
    eh_feriado = models.BooleanField(default=False)
    descricao_evento = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Calendário do planejamento"
        verbose_name_plural = "Calendários do planejamento"
        ordering = ("data",)
        constraints = [
            models.UniqueConstraint(
                fields=("projeto", "data"),
                name="uq_calendario_planejamento_projeto_data",
            )
        ]
        indexes = [
            models.Index(fields=("projeto", "semana_codigo"), name="idx_cal_proj_semana"),
            models.Index(fields=("projeto", "data"), name="idx_cal_proj_data"),
        ]

    def __str__(self):
        return f"{self.projeto} - {self.data} ({self.semana_codigo})"

    @property
    def intervalo_semana(self):
        return f"{self.data_inicio_semana:%d/%m} a {self.data_fim_semana:%d/%m}"


class ProgramacaoSemanal(TimeStampedModel):
    projeto = models.ForeignKey(
        "cadastros.Projeto",
        on_delete=models.CASCADE,
        related_name="programacoes_semanais",
    )
    semana_codigo = models.CharField(max_length=10, db_index=True)
    semana_label = models.CharField(max_length=40, blank=True)
    data_inicio_semana = models.DateField(null=True, blank=True)
    data_fim_semana = models.DateField(null=True, blank=True)
    data_programada = models.DateField(null=True, blank=True)
    disciplina = models.ForeignKey(
        "cadastros.Disciplina",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programacoes_semanais",
    )
    area_local = models.ForeignKey(
        "cadastros.AreaLocal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programacoes_semanais",
    )
    equipe = models.ForeignKey(
        "cadastros.Equipe",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programacoes_semanais",
    )
    encarregado = models.ForeignKey(
        "cadastros.Funcionario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programacoes_semanais",
    )
    atividade_cronograma = models.ForeignKey(
        "planejamento.AtividadeCronograma",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programacoes_semanais",
    )
    codigo_atividade = models.CharField(max_length=50)
    descr_atividade = models.CharField(max_length=255)
    codigo_subatividade = models.CharField(max_length=50, blank=True)
    descr_subatividade = models.CharField(max_length=255, blank=True)
    qtd_prevista = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    hh_previsto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    turno = models.CharField(max_length=20, choices=TurnoChoices.CHOICES, default=TurnoChoices.INTEGRAL)
    observacao = models.TextField(blank=True)
    origem_arquivo = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "ProgramAção semanal"
        verbose_name_plural = "Programações semanais"
        ordering = ("projeto__codigo", "semana_codigo", "codigo_atividade")
        indexes = [
            models.Index(fields=("projeto", "semana_codigo"), name="idx_prog_proj_semana"),
            models.Index(fields=("projeto", "data_programada"), name="idx_prog_proj_data"),
        ]

    def __str__(self):
        return f"{self.projeto} / {self.semana_codigo} / {self.codigo_atividade}"



