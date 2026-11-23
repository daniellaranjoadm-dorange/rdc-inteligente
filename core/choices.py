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





class MotivoParalisacaoChoices:
    """Motivos de parada em obra naval. Agrupados para o relatorio de HH perdido."""

    CHUVA = "chuva"
    VENTO = "vento"
    TROVOADA = "trovoada"
    MARE = "mare"
    FALTA_MATERIAL = "falta_material"
    FALTA_LIBERACAO = "falta_liberacao"
    AGUARDANDO_ICAMENTO = "aguardando_icamento"
    AGUARDANDO_INSPECAO = "aguardando_inspecao"
    UTILIDADES = "utilidades"
    EQUIPAMENTO = "equipamento"
    INTERFERENCIA = "interferencia"
    SEGURANCA = "seguranca"
    OUTROS = "outros"

    CHOICES = (
        (CHUVA, "Chuva"),
        (VENTO, "Vento forte"),
        (TROVOADA, "Trovoada / descargas atmosféricas"),
        (MARE, "Maré / condição de mar"),
        (FALTA_MATERIAL, "Falta de material"),
        (FALTA_LIBERACAO, "Falta de liberação / PT"),
        (AGUARDANDO_ICAMENTO, "Aguardando guindaste / içamento"),
        (AGUARDANDO_INSPECAO, "Aguardando inspeção (CQ / cliente)"),
        (UTILIDADES, "Falta de energia, ar ou gases"),
        (EQUIPAMENTO, "Quebra de equipamento / ferramenta"),
        (INTERFERENCIA, "Interferência de outra frente"),
        (SEGURANCA, "Parada de segurança"),
        (OUTROS, "Outros"),
    )

    CLIMATICOS = {CHUVA, VENTO, TROVOADA, MARE}


class ResponsabilidadeParalisacaoChoices:
    CLIMA = "clima"
    CONTRATANTE = "contratante"
    CONTRATADA = "contratada"
    TERCEIROS = "terceiros"

    CHOICES = (
        (CLIMA, "Clima / força maior"),
        (CONTRATANTE, "Contratante (cliente)"),
        (CONTRATADA, "Contratada (nossa equipe)"),
        (TERCEIROS, "Terceiros / outra frente"),
    )

    # Sugestao inicial por motivo; o supervisor pode trocar no formulario.
    PADRAO_POR_MOTIVO = {
        MotivoParalisacaoChoices.CHUVA: CLIMA,
        MotivoParalisacaoChoices.VENTO: CLIMA,
        MotivoParalisacaoChoices.TROVOADA: CLIMA,
        MotivoParalisacaoChoices.MARE: CLIMA,
        MotivoParalisacaoChoices.FALTA_LIBERACAO: CONTRATANTE,
        MotivoParalisacaoChoices.AGUARDANDO_INSPECAO: CONTRATANTE,
        MotivoParalisacaoChoices.UTILIDADES: CONTRATANTE,
        MotivoParalisacaoChoices.AGUARDANDO_ICAMENTO: CONTRATANTE,
        MotivoParalisacaoChoices.INTERFERENCIA: TERCEIROS,
        MotivoParalisacaoChoices.FALTA_MATERIAL: CONTRATADA,
        MotivoParalisacaoChoices.EQUIPAMENTO: CONTRATADA,
        MotivoParalisacaoChoices.SEGURANCA: CONTRATADA,
        MotivoParalisacaoChoices.OUTROS: CONTRATADA,
    }


class TipoAreaNavalChoices:
    """Como a area/local se encaixa na obra do navio."""

    BLOCO = "bloco"
    MEGABLOCO = "megabloco"
    ANEL = "anel"
    CASCO = "casco"
    DIQUE = "dique"
    CAIS = "cais"
    OFICINA = "oficina"
    APOIO = "apoio"
    OUTRO = "outro"

    CHOICES = (
        (BLOCO, "Bloco"),
        (MEGABLOCO, "Megabloco"),
        (ANEL, "Anel"),
        (CASCO, "Casco / navio inteiro"),
        (DIQUE, "Dique / carreira"),
        (CAIS, "Cais de acabamento"),
        (OFICINA, "Oficina"),
        (APOIO, "Área de apoio"),
        (OUTRO, "Outro"),
    )


class EtapaConstrucaoNavalChoices:
    """Etapa de construcao em que a area esta."""

    FABRICACAO = "fabricacao"
    SUBMONTAGEM = "submontagem"
    MONTAGEM_BLOCO = "montagem_bloco"
    PRE_EDIFICACAO = "pre_edificacao"
    EDIFICACAO = "edificacao"
    OUTFITTING = "outfitting"
    PINTURA = "pintura"
    COMISSIONAMENTO = "comissionamento"
    PROVAS = "provas"

    CHOICES = (
        (FABRICACAO, "Fabricação (painéis / peças)"),
        (SUBMONTAGEM, "Submontagem"),
        (MONTAGEM_BLOCO, "Montagem de bloco"),
        (PRE_EDIFICACAO, "Pré-edificação"),
        (EDIFICACAO, "Edificação no dique / carreira"),
        (OUTFITTING, "Outfitting (acabamento)"),
        (PINTURA, "Pintura / tratamento de superfície"),
        (COMISSIONAMENTO, "Comissionamento"),
        (PROVAS, "Provas de cais e de mar"),
    )


class CategoriaFotoChoices:
    GERAL = "geral"
    AVANCO = "avanco"
    PARALISACAO = "paralisacao"
    SEGURANCA = "seguranca"
    QUALIDADE = "qualidade"
    MATERIAL = "material"

    CHOICES = (
        (GERAL, "Geral da frente"),
        (AVANCO, "Avanço do serviço"),
        (PARALISACAO, "Paralisação / impedimento"),
        (SEGURANCA, "Segurança"),
        (QUALIDADE, "Qualidade / inspeção"),
        (MATERIAL, "Material / recebimento"),
    )


class DecisaoAceiteChoices:
    APROVADO = "aprovado"
    RESSALVAS = "ressalvas"
    REPROVADO = "reprovado"

    CHOICES = (
        (APROVADO, "Aprovado"),
        (RESSALVAS, "Aprovado com ressalvas"),
        (REPROVADO, "Reprovado"),
    )


class TipoEquipamentoChoices:
    GUINDASTE = "guindaste"
    PORTICO = "portico"
    PONTE_ROLANTE = "ponte_rolante"
    MUNCK = "munck"
    PLATAFORMA = "plataforma"
    EMPILHADEIRA = "empilhadeira"
    MAQUINA_SOLDA = "maquina_solda"
    COMPRESSOR = "compressor"
    GERADOR = "gerador"
    JATO = "jato"
    OUTRO = "outro"

    CHOICES = (
        (GUINDASTE, "Guindaste"),
        (PORTICO, "Pórtico"),
        (PONTE_ROLANTE, "Ponte rolante"),
        (MUNCK, "Caminhão munck"),
        (PLATAFORMA, "Plataforma elevatória"),
        (EMPILHADEIRA, "Empilhadeira"),
        (MAQUINA_SOLDA, "Máquina de solda"),
        (COMPRESSOR, "Compressor"),
        (GERADOR, "Gerador"),
        (JATO, "Equipamento de jato / pintura"),
        (OUTRO, "Outro"),
    )


class MotivoParadaEquipamentoChoices:
    MANUTENCAO = "manutencao"
    QUEBRA = "quebra"
    SEM_OPERADOR = "sem_operador"
    AGUARDANDO_FRENTE = "aguardando_frente"
    CLIMA = "clima"
    ABASTECIMENTO = "abastecimento"
    OUTRO = "outro"

    CHOICES = (
        (MANUTENCAO, "Manutenção programada"),
        (QUEBRA, "Quebra / defeito"),
        (SEM_OPERADOR, "Sem operador / sinaleiro"),
        (AGUARDANDO_FRENTE, "Aguardando frente liberar"),
        (CLIMA, "Clima (vento, chuva)"),
        (ABASTECIMENTO, "Abastecimento / energia"),
        (OUTRO, "Outro"),
    )


class TipoOcorrenciaChoices:
    QUASE_ACIDENTE = "quase_acidente"
    INCIDENTE = "incidente"
    ACIDENTE_SEM_AFASTAMENTO = "acidente_sem_afastamento"
    ACIDENTE_COM_AFASTAMENTO = "acidente_com_afastamento"
    CONDICAO_INSEGURA = "condicao_insegura"
    NAO_CONFORMIDADE = "nao_conformidade"
    MEIO_AMBIENTE = "meio_ambiente"
    FISCALIZACAO = "fiscalizacao"

    CHOICES = (
        (QUASE_ACIDENTE, "Quase-acidente"),
        (INCIDENTE, "Incidente (dano material)"),
        (ACIDENTE_SEM_AFASTAMENTO, "Acidente sem afastamento"),
        (ACIDENTE_COM_AFASTAMENTO, "Acidente com afastamento"),
        (CONDICAO_INSEGURA, "Condição / ato inseguro"),
        (NAO_CONFORMIDADE, "Não conformidade de qualidade"),
        (MEIO_AMBIENTE, "Meio ambiente (vazamento, resíduo)"),
        (FISCALIZACAO, "Visita / fiscalização"),
    )

    SEGURANCA = {QUASE_ACIDENTE, INCIDENTE, ACIDENTE_SEM_AFASTAMENTO, ACIDENTE_COM_AFASTAMENTO, CONDICAO_INSEGURA}


class GravidadeOcorrenciaChoices:
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

    CHOICES = ((BAIXA, "Baixa"), (MEDIA, "Média"), (ALTA, "Alta"), (CRITICA, "Crítica"))


class StatusOcorrenciaChoices:
    ABERTA = "aberta"
    EM_TRATAMENTO = "em_tratamento"
    ENCERRADA = "encerrada"

    CHOICES = ((ABERTA, "Aberta"), (EM_TRATAMENTO, "Em tratamento"), (ENCERRADA, "Encerrada"))
