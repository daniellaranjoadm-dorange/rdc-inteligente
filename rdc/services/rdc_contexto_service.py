from django.db.models import Q

from alocacao.models import FuncionarioProjeto, HistogramaPlanejado
from core.choices import TurnoChoices
from planejamento.models import AtividadeCronograma
from rdc.models import PerfilOperacionalUsuario, CalendarioPlanejamento, ProgramacaoSemanal


def obter_semana_planejamento(projeto_id, data_ref):
    item = (
        CalendarioPlanejamento.objects.filter(projeto_id=projeto_id, data=data_ref)
        .only('semana_codigo', 'semana_label', 'data_inicio_semana', 'data_fim_semana', 'descricao_evento')
        .first()
    )
    if not item:
        return None
    return {
        'semana_codigo': item.semana_codigo,
        'semana_label': item.semana_label or f"SEM {item.semana_codigo}",
        'data_inicio_semana': item.data_inicio_semana,
        'data_fim_semana': item.data_fim_semana,
        'descricao_evento': item.descricao_evento,
        'origem': 'calendario',
    }


def obter_perfil_operacional(user):
    if not getattr(user, 'is_authenticated', False):
        return None
    return (
        PerfilOperacionalUsuario.objects.select_related('funcionario', 'projeto_padrao', 'disciplina_padrao', 'equipe_padrao')
        .filter(user=user, ativo=True)
        .first()
    )


def buscar_programacao_semana(projeto_id, data_ref, disciplina_id=None, equipe_id=None, area_local_id=None, turno=None):
    calendario = CalendarioPlanejamento.objects.filter(projeto_id=projeto_id, data=data_ref).first()
    if not calendario:
        return ProgramacaoSemanal.objects.none(), None

    qs = ProgramacaoSemanal.objects.select_related(
        'disciplina', 'area_local', 'equipe', 'encarregado', 'atividade_cronograma'
    ).filter(
        projeto_id=projeto_id,
        semana_codigo=calendario.semana_codigo,
    )

    if disciplina_id:
        qs = qs.filter(Q(disciplina_id=disciplina_id) | Q(disciplina__isnull=True))
    if equipe_id:
        qs = qs.filter(Q(equipe_id=equipe_id) | Q(equipe__isnull=True))
    if area_local_id:
        qs = qs.filter(Q(area_local_id=area_local_id) | Q(area_local__isnull=True))
    if turno:
        qs = qs.filter(turno__in=[turno, TurnoChoices.INTEGRAL])

    if qs.filter(data_programada=data_ref).exists():
        qs = qs.filter(Q(data_programada=data_ref) | Q(data_programada__isnull=True))

    return qs.order_by('codigo_atividade', 'descr_atividade'), calendario


def montar_contexto_montagem_rdc(user, data_ref):
    from cadastros.models import AreaLocal
    from .rdc_service import buscar_funcionarios_alocados, buscar_histograma_do_dia

    perfil = obter_perfil_operacional(user)
    funcionario = getattr(perfil, 'funcionario', None)
    projeto = getattr(perfil, 'projeto_padrao', None)
    disciplina = getattr(perfil, 'disciplina_padrao', None)
    equipe = getattr(perfil, 'equipe_padrao', None)

    if funcionario and not equipe:
        equipe = (
            getattr(funcionario, 'equipes_lideradas', None).filter(ativo=True).select_related('disciplina').first()
            if hasattr(funcionario, 'equipes_lideradas') else None
        )
        if equipe and not disciplina:
            disciplina = equipe.disciplina

    alocados = FuncionarioProjeto.objects.none()
    if projeto and disciplina:
        alocados = buscar_funcionarios_alocados(projeto.id, disciplina.id, data_ref, getattr(equipe, 'id', None))

    if not projeto and alocados.exists():
        projeto = alocados.first().projeto
    if not disciplina and alocados.exists():
        disciplina = alocados.first().disciplina
    if not equipe and alocados.exists():
        equipe = alocados.first().equipe

    area_local = None
    if projeto and disciplina:
        hist_qs = buscar_histograma_do_dia(projeto.id, None, disciplina.id, data_ref, TurnoChoices.INTEGRAL)
        hist_first = hist_qs.first() if hasattr(hist_qs, 'first') else None
        if hist_first:
            area_local = getattr(hist_first, 'area_local', None)
        if not area_local:
            atividade = (
                AtividadeCronograma.objects.filter(
                    projeto=projeto,
                    disciplina=disciplina,
                    data_inicio__lte=data_ref,
                    data_fim__gte=data_ref
                )
                .select_related('area_local')
                .first()
            )
            if atividade:
                area_local = atividade.area_local

    if not area_local and projeto:
        area_local = AreaLocal.objects.filter(projeto=projeto, ativo=True).order_by('descricao').first()

    semana = obter_semana_planejamento(getattr(projeto, 'id', None), data_ref) if projeto else None
    programacoes = ProgramacaoSemanal.objects.none()

    if projeto:
        programacoes, calendario = buscar_programacao_semana(
            projeto.id,
            data_ref,
            getattr(disciplina, 'id', None),
            getattr(equipe, 'id', None),
            getattr(area_local, 'id', None),
            TurnoChoices.INTEGRAL,
        )
        if calendario and not semana:
            semana = obter_semana_planejamento(projeto.id, data_ref)

    atividades_sugeridas = []
    for prog in programacoes[:12]:
        atividades_sugeridas.append({
            'codigo_atividade': prog.codigo_atividade,
            'descr_atividade': prog.descr_atividade,
            'codigo_subatividade': prog.codigo_subatividade,
            'descr_subatividade': prog.descr_subatividade,
            'qtd_prevista': prog.qtd_prevista,
            'hh_previsto': prog.hh_previsto,
            'origem': 'programacao',
        })

    histograma_qs = HistogramaPlanejado.objects.none()
    if projeto and disciplina and area_local:
        histograma_qs = buscar_histograma_do_dia(
            projeto.id, area_local.id, disciplina.id, data_ref, TurnoChoices.INTEGRAL
        )

    return {
        'perfil': perfil,
        'funcionario': funcionario,
        'encarregado': funcionario,
        'projeto': projeto,
        'disciplina': disciplina,
        'equipe': equipe,
        'area_local': area_local,
        'data': data_ref,
        'turno': TurnoChoices.INTEGRAL,
        'semana': semana,
        'alocados': list(alocados[:50]),
        'total_alocados': alocados.count() if hasattr(alocados, 'count') else 0,
        'histograma_do_dia': list(histograma_qs[:50]),
        'total_histograma': histograma_qs.count() if hasattr(histograma_qs, 'count') else 0,
        'programacoes': list(programacoes[:50]),
        'total_programacoes': programacoes.count() if hasattr(programacoes, 'count') else 0,
        'atividades_sugeridas': atividades_sugeridas,
        'tem_contexto_minimo': bool(projeto and disciplina),
        'mensagem_contexto': 'Contexto operacional encontrado.' if (projeto and disciplina) else 'Cadastre um Perfil Operacional do Usuário para habilitar sugestões reais.',
    }


def resumo_montagem_rdc(contexto):
    semana = contexto.get('semana') or {}
    return {
        'projeto': getattr(contexto.get('projeto'), 'codigo', '') or 'Não sugerido',
        'disciplina': getattr(contexto.get('disciplina'), 'nome', '') or 'Não sugerida',
        'area_local': getattr(contexto.get('area_local'), 'descricao', '') or 'Não sugerida',
        'encarregado': getattr(contexto.get('encarregado'), 'nome', '') or 'Não identificado',
        'equipe': getattr(contexto.get('equipe'), 'nome', '') or 'Não sugerida',
        'colaboradores': contexto.get('total_alocados', 0),
        'atividades': contexto.get('total_programacoes', 0),
        'histograma': contexto.get('total_histograma', 0),
        'semana_codigo': semana.get('semana_codigo') if semana else '-',
        'intervalo_semana': f"{semana.get('data_inicio_semana').strftime('%d/%m/%Y')} a {semana.get('data_fim_semana').strftime('%d/%m/%Y')}" if semana and semana.get('data_inicio_semana') and semana.get('data_fim_semana') else '-',
        'origem_semana': 'Semana de planejamento carregada do calendário' if semana else 'Semana calculada sem calendário carregado',
    }


