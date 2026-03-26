from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from cadastros.models import AreaLocal, Disciplina, Equipe, Funcionario, Projeto
from cadastros.serializers import AreaLocalSerializer, DisciplinaSerializer, EquipeSerializer, FuncionarioSerializer, ProjetoSerializer


class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]


class ProjetoViewSet(BaseViewSet):
    queryset = Projeto.objects.all().order_by("nome")
    serializer_class = ProjetoSerializer


class DisciplinaViewSet(BaseViewSet):
    queryset = Disciplina.objects.all().order_by("nome")
    serializer_class = DisciplinaSerializer


class AreaLocalViewSet(BaseViewSet):
    queryset = AreaLocal.objects.select_related("projeto", "disciplina_padrao").all().order_by("descricao")
    serializer_class = AreaLocalSerializer


class FuncionarioViewSet(BaseViewSet):
    queryset = Funcionario.objects.select_related("funcao", "empresa").all().order_by("nome")
    serializer_class = FuncionarioSerializer


class EquipeViewSet(BaseViewSet):
    queryset = Equipe.objects.select_related("disciplina", "empresa", "encarregado").all().order_by("nome")
    serializer_class = EquipeSerializer


