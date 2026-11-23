"""Cria o RDC de outro dia a partir de um existente (equipe, atividades e equipamentos)."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from core.audit import registrar_auditoria

IGNORAR = {"id", "rdc", "created_at", "updated_at", "mobile_uuid", "sync_updated_at", "sync_deleted_at"}


def _copiar_campos(obj, **sobrescrever):
    dados = {}
    for campo in obj._meta.concrete_fields:
        if campo.name in IGNORAR or campo.primary_key:
            continue
        dados[campo.attname] = getattr(obj, campo.attname)
    dados.update(sobrescrever)
    return type(obj)(**dados)


@transaction.atomic
def copiar_rdc(origem, *, data, turno, usuario, funcionarios=True, atividades=True, equipamentos=True):
    from rdc.models import RDC

    if RDC.objects.filter(projeto_id=origem.projeto_id, area_local_id=origem.area_local_id,
                          disciplina_id=origem.disciplina_id, data=data, turno=turno).exists():
        raise ValidationError("Já existe RDC para esta área, disciplina, data e turno.")

    novo = RDC.objects.create(
        projeto_id=origem.projeto_id, area_local_id=origem.area_local_id, disciplina_id=origem.disciplina_id,
        data=data, turno=turno, supervisor_id=origem.supervisor_id,
        horario_inicio=origem.horario_inicio, horario_fim=origem.horario_fim,
        status="rascunho", criado_por=usuario,
    )

    mapa_atividades = {}
    if atividades:
        for a in origem.atividades.all():
            nova = _copiar_campos(a, rdc_id=novo.pk, qtd_executada=Decimal("0"), comentarios="", ativa_no_dia=True)
            nova.save()
            mapa_atividades[a.pk] = nova.pk
    if funcionarios:
        for f in origem.funcionarios.all():
            # Presenca e liberacao sao do dia: comecam limpas no RDC novo.
            _copiar_campos(
                f, rdc_id=novo.pk, presente_catraca=False, confirmado_supervisor=False, elegivel=True,
                motivo_bloqueio="", liberado_sem_catraca=False, justificativa_liberacao="",
                liberado_por_id=None, liberado_em=None,
            ).save()
    if equipamentos:
        for e in origem.equipamentos.all():
            _copiar_campos(e, rdc_id=novo.pk, horas_trabalhadas=Decimal("0"), horas_paradas=Decimal("0"),
                           motivo_parada="", observacao="", criado_por_id=getattr(usuario, "pk", None)).save()

    registrar_auditoria(usuario, "copiar_rdc", target_model="RDC", target_id=novo.pk,
                        detail=f"Criado a partir do RDC #{origem.pk} ({origem.data:%d/%m/%Y})")
    return novo
