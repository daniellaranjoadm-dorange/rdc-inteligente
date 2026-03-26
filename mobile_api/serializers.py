from django.db import transaction
from rest_framework import serializers

from cadastros.models import AreaLocal, Disciplina, Equipe, Funcionario, Projeto
from rdc.models import RDC, RDCAtividade, RDCApontamento, RDCFuncionario, RDCValidacao


class MobileProjetoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projeto
        fields = ["id", "codigo", "nome", "ativo"]


class MobileDisciplinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disciplina
        fields = ["id", "nome", "ativo"]


class MobileAreaLocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaLocal
        fields = ["id", "codigo", "descricao", "ativo"]


class MobileEquipeSerializer(serializers.ModelSerializer):
    ativo = serializers.BooleanField(source="ativa", read_only=True)

    class Meta:
        model = Equipe
        fields = ["id", "nome", "ativo"]


class MobileFuncionarioSerializer(serializers.ModelSerializer):
    funcao_nome = serializers.CharField(source="funcao.nome", read_only=True)

    class Meta:
        model = Funcionario
        fields = [
            "id",
            "matricula",
            "nome",
            "ativo",
            "funcao",
            "funcao_nome",
        ]


class MobileRDCAtividadeSerializer(serializers.ModelSerializer):
    origem_display = serializers.SerializerMethodField()

    class Meta:
        model = RDCAtividade
        fields = [
            "id",
            "mobile_uuid",
            "sync_updated_at",
            "sync_deleted_at",
            "rdc",
            "atividade_cronograma",
            "codigo_atividade",
            "descr_atividade",
            "codigo_subatividade",
            "descr_subatividade",
            "qtd_escopo",
            "qtd_executada",
            "comentarios",
            "origem",
            "origem_display",
            "obrigatoria",
            "ativa_no_dia",
            "created_at",
            "updated_at",
        ]

    def get_origem_display(self, obj):
        return getattr(obj, "get_origem_display", lambda: obj.origem)()


class MobileRDCFuncionarioSerializer(serializers.ModelSerializer):
    funcao_nome = serializers.CharField(source="funcao.nome", read_only=True)
    equipe_nome = serializers.CharField(source="equipe.nome", read_only=True)
    liberado_por_username = serializers.CharField(source="liberado_por.username", read_only=True)

    class Meta:
        model = RDCFuncionario
        fields = [
            "id",
            "mobile_uuid",
            "sync_updated_at",
            "sync_deleted_at",
            "rdc",
            "funcionario",
            "equipe",
            "equipe_nome",
            "funcao",
            "funcao_nome",
            "matricula",
            "nome",
            "hora_normal",
            "hora_extra",
            "hh_total",
            "presente_catraca",
            "elegivel",
            "motivo_bloqueio",
            "confirmado_supervisor",
            "liberado_sem_catraca",
            "justificativa_liberacao",
            "liberado_por",
            "liberado_por_username",
            "liberado_em",
            "created_at",
            "updated_at",
        ]


class MobileRDCApontamentoSerializer(serializers.ModelSerializer):
    funcionario_nome = serializers.CharField(source="rdc_funcionario.nome", read_only=True)
    atividade_codigo = serializers.CharField(source="rdc_atividade.codigo_atividade", read_only=True)
    atividade_descricao = serializers.CharField(source="rdc_atividade.descr_atividade", read_only=True)

    class Meta:
        model = RDCApontamento
        fields = [
            "id",
            "mobile_uuid",
            "sync_updated_at",
            "sync_deleted_at",
            "rdc",
            "rdc_funcionario",
            "funcionario_nome",
            "rdc_atividade",
            "atividade_codigo",
            "atividade_descricao",
            "horas",
            "observacao",
            "created_at",
            "updated_at",
        ]


class MobileRDCValidacaoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = RDCValidacao
        fields = [
            "id",
            "rdc",
            "tipo",
            "tipo_display",
            "referencia",
            "status",
            "status_display",
            "mensagem",
            "created_at",
        ]

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()

    def get_status_display(self, obj):
        return obj.get_status_display()


class MobileRDCListSerializer(serializers.ModelSerializer):
    projeto_codigo = serializers.CharField(source="projeto.codigo", read_only=True)
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)
    disciplina_nome = serializers.CharField(source="disciplina.nome", read_only=True)
    area_local_descricao = serializers.CharField(source="area_local.descricao", read_only=True)
    supervisor_nome = serializers.CharField(source="supervisor.nome", read_only=True)
    total_atividades = serializers.IntegerField(read_only=True)
    total_funcionarios = serializers.IntegerField(read_only=True)
    total_apontamentos = serializers.IntegerField(read_only=True)

    class Meta:
        model = RDC
        fields = [
            "id",
            "mobile_uuid",
            "sync_updated_at",
            "sync_deleted_at",
            "data",
            "turno",
            "status",
            "projeto",
            "projeto_codigo",
            "projeto_nome",
            "disciplina",
            "disciplina_nome",
            "area_local",
            "area_local_descricao",
            "supervisor",
            "supervisor_nome",
            "observacoes",
            "fechado_em",
            "total_atividades",
            "total_funcionarios",
            "total_apontamentos",
            "created_at",
            "updated_at",
        ]


class MobileRDCDetailSerializer(serializers.ModelSerializer):
    projeto = MobileProjetoSerializer(read_only=True)
    disciplina = MobileDisciplinaSerializer(read_only=True)
    area_local = MobileAreaLocalSerializer(read_only=True)
    atividades = MobileRDCAtividadeSerializer(many=True, read_only=True)
    funcionarios = MobileRDCFuncionarioSerializer(many=True, read_only=True)
    apontamentos = MobileRDCApontamentoSerializer(many=True, read_only=True)
    validacoes = MobileRDCValidacaoSerializer(many=True, read_only=True)
    supervisor_nome = serializers.CharField(source="supervisor.nome", read_only=True)

    class Meta:
        model = RDC
        fields = [
            "id",
            "mobile_uuid",
            "sync_updated_at",
            "sync_deleted_at",
            "projeto",
            "area_local",
            "disciplina",
            "data",
            "turno",
            "supervisor",
            "supervisor_nome",
            "dia_semana",
            "condicao_area",
            "clima_manha",
            "clima_tarde",
            "clima_noite",
            "horario_inicio",
            "horario_fim",
            "observacoes",
            "status",
            "fechado_em",
            "permite_edicao_pos_fechamento",
            "justificativa_fechamento",
            "atividades",
            "funcionarios",
            "apontamentos",
            "validacoes",
            "created_at",
            "updated_at",
        ]


class MobileMeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    is_staff = serializers.BooleanField()
    is_superuser = serializers.BooleanField()


class MobileBaseOperacionalSerializer(serializers.Serializer):
    referencia = serializers.DateField()
    projetos = MobileProjetoSerializer(many=True)
    disciplinas = MobileDisciplinaSerializer(many=True)
    areas = MobileAreaLocalSerializer(many=True)
    equipes = MobileEquipeSerializer(many=True)
    funcionarios = MobileFuncionarioSerializer(many=True)
    rdcs = MobileRDCListSerializer(many=True)


class MobileRDCCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDC
        fields = [
            "id",
            "mobile_uuid",
            "projeto",
            "area_local",
            "disciplina",
            "data",
            "turno",
            "supervisor",
            "dia_semana",
            "condicao_area",
            "clima_manha",
            "clima_tarde",
            "clima_noite",
            "horario_inicio",
            "horario_fim",
            "observacoes",
            "status",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        request = self.context["request"]
        mobile_uuid = validated_data.pop("mobile_uuid", None)
        instance = RDC(criado_por=request.user, **validated_data)
        if mobile_uuid:
            instance.mobile_uuid = mobile_uuid
        instance.full_clean()
        instance.save()
        return instance


class MobileRDCFuncionarioCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDCFuncionario
        fields = [
            "id",
            "mobile_uuid",
            "funcionario",
            "equipe",
            "funcao",
            "hora_normal",
            "hora_extra",
            "presente_catraca",
            "confirmado_supervisor",
            "liberado_sem_catraca",
            "justificativa_liberacao",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        funcionario = attrs["funcionario"]
        funcao = attrs.get("funcao") or getattr(funcionario, "funcao", None)
        if not funcao:
            raise serializers.ValidationError({"funcao": "Informe a função do funcionário."})
        attrs["funcao"] = funcao
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        rdc = self.context["rdc"]
        funcionario = validated_data["funcionario"]

        liberado_sem_catraca = validated_data.pop("liberado_sem_catraca", False)
        justificativa_liberacao = validated_data.pop("justificativa_liberacao", "")
        mobile_uuid = validated_data.pop("mobile_uuid", None)

        instance = RDCFuncionario(
            rdc=rdc,
            matricula=funcionario.matricula,
            nome=funcionario.nome,
            **validated_data,
        )
        if mobile_uuid:
            instance.mobile_uuid = mobile_uuid

        if instance.presente_catraca:
            instance.remover_liberacao_sem_catraca()
        elif liberado_sem_catraca:
            instance.registrar_liberacao_sem_catraca(request.user, justificativa_liberacao)
        else:
            instance.remover_liberacao_sem_catraca()

        instance.full_clean()
        instance.save()
        return instance


class MobileRDCAtividadeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDCAtividade
        fields = [
            "id",
            "mobile_uuid",
            "atividade_cronograma",
            "codigo_atividade",
            "descr_atividade",
            "codigo_subatividade",
            "descr_subatividade",
            "qtd_escopo",
            "qtd_executada",
            "comentarios",
            "origem",
            "obrigatoria",
            "ativa_no_dia",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        rdc = self.context["rdc"]
        mobile_uuid = validated_data.pop("mobile_uuid", None)
        instance = RDCAtividade(rdc=rdc, **validated_data)
        if mobile_uuid:
            instance.mobile_uuid = mobile_uuid
        instance.full_clean()
        instance.save()
        return instance


class MobileRDCApontamentoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDCApontamento
        fields = [
            "id",
            "mobile_uuid",
            "rdc_funcionario",
            "rdc_atividade",
            "horas",
            "observacao",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        rdc = self.context["rdc"]
        mobile_uuid = validated_data.pop("mobile_uuid", None)
        instance = RDCApontamento(rdc=rdc, **validated_data)
        if mobile_uuid:
            instance.mobile_uuid = mobile_uuid
        instance.full_clean()
        instance.save()
        return instance


class MobileRDCUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDC
        fields = [
            "mobile_uuid",
            "projeto",
            "area_local",
            "disciplina",
            "data",
            "turno",
            "supervisor",
            "dia_semana",
            "condicao_area",
            "clima_manha",
            "clima_tarde",
            "clima_noite",
            "horario_inicio",
            "horario_fim",
            "observacoes",
            "status",
            "permite_edicao_pos_fechamento",
            "justificativa_fechamento",
        ]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        return instance


class MobileRDCFuncionarioUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDCFuncionario
        fields = [
            "mobile_uuid",
            "equipe",
            "funcao",
            "hora_normal",
            "hora_extra",
            "presente_catraca",
            "confirmado_supervisor",
            "liberado_sem_catraca",
            "justificativa_liberacao",
        ]

    def update(self, instance, validated_data):
        request = self.context["request"]

        liberado_sem_catraca = validated_data.pop("liberado_sem_catraca", instance.liberado_sem_catraca)
        justificativa_liberacao = validated_data.pop(
            "justificativa_liberacao",
            instance.justificativa_liberacao,
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if instance.presente_catraca:
            instance.remover_liberacao_sem_catraca()
        elif liberado_sem_catraca:
            instance.registrar_liberacao_sem_catraca(request.user, justificativa_liberacao)
        else:
            instance.remover_liberacao_sem_catraca()

        instance.full_clean()
        instance.save()
        return instance


class MobileRDCAtividadeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDCAtividade
        fields = [
            "mobile_uuid",
            "atividade_cronograma",
            "codigo_atividade",
            "descr_atividade",
            "codigo_subatividade",
            "descr_subatividade",
            "qtd_escopo",
            "qtd_executada",
            "comentarios",
            "origem",
            "obrigatoria",
            "ativa_no_dia",
        ]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        return instance


class MobileRDCApontamentoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDCApontamento
        fields = [
            "mobile_uuid",
            "rdc_funcionario",
            "rdc_atividade",
            "horas",
            "observacao",
        ]

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        return instance




from importacoes.models import ImportacaoArquivo

class MobileImportacaoSerializer(serializers.ModelSerializer):
    nome_arquivo = serializers.CharField(read_only=True)
    total_erros = serializers.IntegerField(read_only=True)

    class Meta:
        model = ImportacaoArquivo
        fields = [
            "id",
            "tipo",
            "status",
            "resumo",
            "total_erros",
            "created_at",
            "nome_arquivo",
        ]
