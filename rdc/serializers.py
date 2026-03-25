from rest_framework import serializers

from rdc.models import RDC, RDCAtividade, RDCFuncionario, RDCValidacao

class RDCAtividadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDCAtividade
        fields = "__all__"

class RDCFuncionarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDCFuncionario
        fields = "__all__"

class RDCValidacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDCValidacao
        fields = "__all__"

class RDCSerializer(serializers.ModelSerializer):
    atividades = RDCAtividadeSerializer(many=True, read_only=True)
    funcionarios = RDCFuncionarioSerializer(many=True, read_only=True)
    validacoes = RDCValidacaoSerializer(many=True, read_only=True)

    class Meta:
        model = RDC
        fields = "__all__"

