from rest_framework import serializers

from acesso.models import RegistroCatraca


class RegistroCatracaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroCatraca
        fields = "__all__"
