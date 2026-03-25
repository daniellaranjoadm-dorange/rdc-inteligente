class TurnoChoices:
    MANHA = "manha"
    TARDE = "tarde"
    NOITE = "noite"
    INTEGRAL = "integral"

    CHOICES = (
        (MANHA, "Manhã"),
        (TARDE, "Tarde"),
        (NOITE, "Noite"),
        (INTEGRAL, "Integral"),
    )


class StatusRDCChoices:
    RASCUNHO = "rascunho"
    PRE_PREENCHIDO = "pre_preenchido"
    EM_REVISAO = "em_revisao"
    APROVADO = "aprovado"
    FECHADO = "fechado"

    CHOICES = (
        (RASCUNHO, "Rascunho"),
        (PRE_PREENCHIDO, "Pré-preenchido"),
        (EM_REVISAO, "Em revisão"),
        (APROVADO, "Aprovado"),
        (FECHADO, "Fechado"),
    )


class OrigemAtividadeChoices:
    CRONOGRAMA = "cronograma"
    MANUAL = "manual"
    AJUSTE_SUPERVISOR = "ajuste_supervisor"

    CHOICES = (
        (CRONOGRAMA, "Cronograma"),
        (MANUAL, "Manual"),
        (AJUSTE_SUPERVISOR, "Ajuste do supervisor"),
    )


class TipoValidacaoChoices:
    FUNCIONARIO_SEM_CATRACA = "funcionario_sem_catraca"
    FUNCIONARIO_SEM_ALOCACAO = "funcionario_sem_alocacao"
    ATIVIDADE_FORA_CRONOGRAMA = "atividade_fora_cronograma"
    FUNCAO_DIVERGENTE = "funcao_divergente"
    EQUIPE_FORA_HISTOGRAMA = "equipe_fora_histograma"
    DUPLICIDADE_APONTAMENTO = "duplicidade_apontamento"

    CHOICES = (
        (FUNCIONARIO_SEM_CATRACA, "Funcionário sem catraca"),
        (FUNCIONARIO_SEM_ALOCACAO, "Funcionário sem alocAção"),
        (ATIVIDADE_FORA_CRONOGRAMA, "Atividade fora do cronograma"),
        (FUNCAO_DIVERGENTE, "Função divergente"),
        (EQUIPE_FORA_HISTOGRAMA, "Equipe fora do histograma"),
        (DUPLICIDADE_APONTAMENTO, "Duplicidade de apontamento"),
    )


class StatusValidacaoChoices:
    ALERTA = "alerta"
    BLOQUEIO = "bloqueio"
    INFO = "info"

    CHOICES = (
        (ALERTA, "Alerta"),
        (BLOQUEIO, "Bloqueio"),
        (INFO, "Informativo"),
    )


class TipoImportacaoChoices:
    FUNCIONARIOS = "funcionarios"
    CATRACA = "catraca"
    ALOCACOES = "alocacoes"
    CRONOGRAMA = "cronograma"
    HISTOGRAMA = "histograma"

    CHOICES = (
        (FUNCIONARIOS, "Funcionários"),
        (CATRACA, "Catraca"),
        (ALOCACOES, "Alocações"),
        (CRONOGRAMA, "Cronograma"),
        (HISTOGRAMA, "Histograma"),
    )


class StatusImportacaoChoices:
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    CONCLUIDO_COM_ERROS = "concluido_com_erros"
    ERRO = "erro"

    CHOICES = (
        (PENDENTE, "Pendente"),
        (PROCESSANDO, "Processando"),
        (CONCLUIDO, "Concluído"),
        (CONCLUIDO_COM_ERROS, "Concluído com erros"),
        (ERRO, "Erro"),
    )


