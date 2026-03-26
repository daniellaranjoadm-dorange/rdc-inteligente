from rest_framework import serializers

from planejamento.models import AtividadeCronograma


class AtividadeCronogramaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtividadeCronograma
        fields = "__all__"


