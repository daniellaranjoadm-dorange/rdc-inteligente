from decimal import Decimal
from collections import Counter
from django.db import transaction

from core.choices import (
    OrigemAtividadeChoices,
    StatusRDCChoices,
    StatusValidacaoChoices,
    TipoValidacaoChoices,
    TurnoChoices,
)
from planejamento.models import AtividadeCronograma
from rdc.models import RDC, RDCAtividade, RDCFuncionario

from . import rdc_service as base_service


def sugerir_contexto_rdc_por_cronograma(
    projeto_id=None,
    data=None,
    disciplina_id=None,
    area_local_id=None,
    turno=TurnoChoices.INTEGRAL,
):
    qs = AtividadeCronograma.objects.select_related("projeto", "area_local", "disciplina")

    if projeto_id:
        qs = qs.filter(projeto_id=projeto_id)
    if data:
        qs = qs.filter(data_inicio__lte=data, data_fim__gte=data)
    if disciplina_id:
        qs = qs.filter(disciplina_id=disciplina_id)
    if area_local_id:
        qs = qs.filter(area_local_id=area_local_id)

    atividades = list(qs)
    if not atividades:
        raise ValueError("Nenhuma atividade de cronograma encontrada para sugerir um contexto de RDC.")

    if not data:
        contagem_por_data = Counter()
        for atividade in atividades:
            contagem_por_data[atividade.data_inicio] += 1
        data = contagem_por_data.most_common(1)[0][0]
        atividades = [a for a in atividades if a.data_inicio <= data <= a.data_fim]

    if not atividades:
        raise ValueError("Nenhuma atividade de cronograma ativa na data selecionada.")

    if not disciplina_id:
        disciplina_id = Counter(a.disciplina_id for a in atividades).most_common(1)[0][0]
        atividades = [a for a in atividades if a.disciplina_id == disciplina_id]

    if not area_local_id:
        area_local_id = Counter(a.area_local_id for a in atividades).most_common(1)[0][0]
        atividades = [a for a in atividades if a.area_local_id == area_local_id]

    atividade_ref = atividades[0]
    return {
        "projeto": atividade_ref.projeto,
        "data": data,
        "disciplina": atividade_ref.disciplina,
        "area_local": atividade_ref.area_local,
        "turno": turno,
        "total_atividades": len(atividades),
    }


def gerar_apontamentos_base_automaticos(rdc):
    if rdc.apontamentos.exists():
        return 0

    atividades = list(rdc.atividades.filter(ativa_no_dia=True).order_by("codigo_atividade", "codigo_subatividade"))
    funcionarios = [
        item
        for item in rdc.funcionarios.select_related("funcao").all()
        if getattr(item, "pode_apontar", False) and (item.hh_total or Decimal("0.00")) > 0
    ]

    if not atividades or not funcionarios:
        return 0

    mapa_atividades = {chr(65 + idx): atividade for idx, atividade in enumerate(atividades[:6])}
    criados = 0

    for funcionario in funcionarios:
        distribuicao = base_service.distribuir_horas_por_atividades(funcionario, list(mapa_atividades.values()))
        for letra, horas in distribuicao:
            atividade = mapa_atividades.get(letra)
            if not atividade or not horas or horas <= 0:
                continue
            _, created = base_service.RDCApontamento.objects.get_or_create(
                rdc=rdc,
                rdc_funcionario=funcionario,
                rdc_atividade=atividade,
                defaults={
                    "horas": horas,
                    "observacao": "Gerado automaticamente na montagem assistida.",
                },
            )
            if created:
                criados += 1

    if criados:
        base_service.registrar_validacao(
            rdc,
            TipoValidacaoChoices.ATIVIDADE_FORA_CRONOGRAMA,
            StatusValidacaoChoices.INFO,
            f"Montagem assistida gerou {criados} apontamento(s) base para acelerar o preenchimento do RDC.",
            referencia=f"AUTO:APONTAMENTOS_BASE:{rdc.pk}",
        )

    return criados


@transaction.atomic
def montar_rdc_pre_preenchido(projeto_id, area_local_id, disciplina_id, data, turno, user, recriar=True):
    rdc = RDC.objects.filter(
        projeto_id=projeto_id,
        area_local_id=area_local_id,
        disciplina_id=disciplina_id,
        data=data,
        turno=turno,
    ).first()

    if rdc and recriar:
        rdc = base_service._resetar_rdc_existente(rdc)
    elif not rdc:
        rdc = RDC.objects.create(
            projeto_id=projeto_id,
            area_local_id=area_local_id,
            disciplina_id=disciplina_id,
            data=data,
            turno=turno,
            dia_semana=data.strftime("%A"),
            status=StatusRDCChoices.PRE_PREENCHIDO,
            criado_por=user,
        )

    programacoes, _cal = base_service.buscar_programacao_semana(
        projeto_id,
        data,
        disciplina_id=disciplina_id,
        area_local_id=area_local_id,
        turno=turno,
    )

    usados = set()
    for prog in programacoes:
        chave = (prog.codigo_atividade or "", prog.codigo_subatividade or "")
        if chave in usados:
            continue

        RDCAtividade.objects.create(
            rdc=rdc,
            atividade_cronograma=prog.atividade_cronograma,
            codigo_atividade=prog.codigo_atividade,
            descr_atividade=prog.descr_atividade,
            codigo_subatividade=prog.codigo_subatividade,
            descr_subatividade=prog.descr_subatividade,
            qtd_escopo=prog.qtd_prevista or Decimal("0.00"),
            origem=OrigemAtividadeChoices.PLANEJAMENTO,
            obrigatoria=True,
            ativa_no_dia=True,
            comentarios=(prog.observacao or ""),
        )
        usados.add(chave)

    atividades = list(base_service.buscar_atividades_planejadas(projeto_id, area_local_id, disciplina_id, data, turno))
    for atividade in atividades:
        chave = (atividade.codigo_atividade or "", atividade.codigo_subatividade or "")
        if chave in usados:
            continue

        RDCAtividade.objects.create(
            rdc=rdc,
            atividade_cronograma=atividade,
            codigo_atividade=atividade.codigo_atividade,
            descr_atividade=atividade.descr_atividade,
            codigo_subatividade=atividade.codigo_subatividade,
            descr_subatividade=atividade.descr_subatividade,
            qtd_escopo=atividade.qtd_escopo,
            origem=OrigemAtividadeChoices.CRONOGRAMA,
            obrigatoria=True,
            ativa_no_dia=True,
        )

    if not atividades:
        base_service.registrar_validacao(
            rdc,
            TipoValidacaoChoices.ATIVIDADE_FORA_CRONOGRAMA,
            StatusValidacaoChoices.BLOQUEIO,
            "Nenhuma atividade do cronograma encontrada para o contexto informado.",
            referencia=f"{projeto_id}-{area_local_id}-{disciplina_id}-{data}-{turno}",
        )

    histogramas = list(base_service.buscar_histograma_do_dia(projeto_id, area_local_id, disciplina_id, data, turno))
    if not histogramas:
        base_service.registrar_validacao(
            rdc,
            TipoValidacaoChoices.EQUIPE_FORA_HISTOGRAMA,
            StatusValidacaoChoices.ALERTA,
            "Nenhum histograma planejado encontrado para o contexto informado. O RDC será preenchido por alocação, com catraca apenas como referência.",
            referencia=f"{projeto_id}-{area_local_id}-{disciplina_id}-{data}-{turno}",
        )
        base_service.popular_funcionarios_rdc_por_alocacao_sem_histograma(
            rdc=rdc,
            projeto_id=projeto_id,
            disciplina_id=disciplina_id,
            data=data,
        )
        gerar_apontamentos_base_automaticos(rdc)
        base_service.popular_metadados_profissionais_do_rdc(rdc)
        return rdc

    vistos = set()
    for hist in histogramas:
        alocacoes = base_service.buscar_funcionarios_alocados(projeto_id, disciplina_id, data, hist.equipe_id)
        total_encontrado = 0

        for alocacao in base_service._alocacoes_priorizadas(alocacoes):
            funcionario = alocacao.funcionario
            if funcionario.id in vistos:
                base_service.registrar_validacao(
                    rdc,
                    TipoValidacaoChoices.DUPLICIDADE_APONTAMENTO,
                    StatusValidacaoChoices.BLOQUEIO,
                    f"Funcionário {funcionario.nome} apareceu mais de uma vez no mesmo RDC.",
                    referencia=funcionario.matricula,
                )
                continue

            elegivel = True
            motivo_bloqueio = ""
            presente = base_service.validar_presenca_catraca(funcionario.matricula, data)
            total_encontrado += 1

            if not funcionario.ativo:
                elegivel = False
                motivo_bloqueio = "Funcionário inativo."
            elif not alocacao.esta_valido_em(data):
                elegivel = False
                motivo_bloqueio = "Funcionário sem alocação ativa no contexto."
                base_service.registrar_validacao(
                    rdc,
                    TipoValidacaoChoices.FUNCIONARIO_SEM_ALOCACAO,
                    StatusValidacaoChoices.BLOQUEIO,
                    f"{funcionario.nome} sem alocação ativa para o projeto/disciplina/data.",
                    referencia=funcionario.matricula,
                )
            elif not presente:
                elegivel = False
                motivo_bloqueio = "Sem registro de catraca no dia."
                base_service.registrar_validacao(
                    rdc,
                    TipoValidacaoChoices.FUNCIONARIO_SEM_CATRACA,
                    StatusValidacaoChoices.BLOQUEIO,
                    f"{funcionario.nome} não possui presença de catraca em {data}.",
                    referencia=funcionario.matricula,
                )

            if funcionario.funcao_id != hist.funcao_id:
                base_service.registrar_validacao(
                    rdc,
                    TipoValidacaoChoices.FUNCAO_DIVERGENTE,
                    StatusValidacaoChoices.ALERTA,
                    f"Função divergente para {funcionario.nome}: cadastrado em {funcionario.funcao} e histograma em {hist.funcao}.",
                    referencia=funcionario.matricula,
                )

            RDCFuncionario.objects.create(
                rdc=rdc,
                funcionario=funcionario,
                equipe=alocacao.equipe,
                funcao=funcionario.funcao,
                matricula=funcionario.matricula,
                nome=funcionario.nome,
                hora_normal=Decimal("8.00") if presente else Decimal("0.00"),
                hora_extra=Decimal("0.00"),
                hh_total=Decimal("8.00") if presente else Decimal("0.00"),
                presente_catraca=presente,
                elegivel=elegivel,
                motivo_bloqueio=motivo_bloqueio,
            )
            vistos.add(funcionario.id)

        if total_encontrado == 0:
            base_service.registrar_validacao(
                rdc,
                TipoValidacaoChoices.EQUIPE_FORA_HISTOGRAMA,
                StatusValidacaoChoices.ALERTA,
                f"Nenhum funcionário alocado encontrado para equipe {hist.equipe}.",
                referencia=str(hist.equipe_id),
            )

    gerar_apontamentos_base_automaticos(rdc)
    base_service.popular_metadados_profissionais_do_rdc(rdc)
    return rdc


@transaction.atomic
def montar_rdc_simulado_por_cronograma(
    user,
    projeto_id=None,
    data=None,
    disciplina_id=None,
    area_local_id=None,
    turno=TurnoChoices.INTEGRAL,
):
    contexto = sugerir_contexto_rdc_por_cronograma(
        projeto_id=projeto_id,
        data=data,
        disciplina_id=disciplina_id,
        area_local_id=area_local_id,
        turno=turno,
    )

    rdc = montar_rdc_pre_preenchido(
        projeto_id=contexto["projeto"].id,
        area_local_id=contexto["area_local"].id,
        disciplina_id=contexto["disciplina"].id,
        data=contexto["data"],
        turno=turno,
        user=user,
        recriar=True,
    )

    base_service.registrar_validacao(
        rdc,
        TipoValidacaoChoices.ATIVIDADE_FORA_CRONOGRAMA,
        StatusValidacaoChoices.INFO,
        f"RDC simulado montado a partir do cronograma. Atividades ativas no contexto: {contexto['total_atividades']}.",
        referencia=f"{contexto['projeto'].codigo}-{contexto['disciplina'].codigo}-{contexto['area_local'].codigo}",
    )
    return rdc, contexto

