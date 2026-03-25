from rest_framework import serializers

from alocacao.models import FuncionarioProjeto, HistogramaPlanejado


class FuncionarioProjetoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuncionarioProjeto
        fields = "__all__"


class HistogramaPlanejadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistogramaPlanejado
        fields = "__all__"

