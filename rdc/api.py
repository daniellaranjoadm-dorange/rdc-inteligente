from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rdc.forms import RDCMontagemForm
from rdc.models import RDC, RDCAtividade, RDCFuncionario, RDCValidacao
from rdc.serializers import RDCAtividadeSerializer, RDCFuncionarioSerializer, RDCSerializer, RDCValidacaoSerializer
from rdc.services.rdc_service import montar_rdc_pre_preenchido


class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]


class RDCViewSet(BaseViewSet):
    queryset = RDC.objects.select_related("projeto", "area_local", "disciplina", "criado_por").all().order_by("-data", "-id")
    serializer_class = RDCSerializer


class RDCAtividadeViewSet(BaseViewSet):
    queryset = RDCAtividade.objects.select_related("rdc", "atividade_cronograma").all()
    serializer_class = RDCAtividadeSerializer


class RDCFuncionarioViewSet(BaseViewSet):
    queryset = RDCFuncionario.objects.select_related("rdc", "funcionario", "funcao", "equipe").all()
    serializer_class = RDCFuncionarioSerializer


class RDCValidacaoViewSet(BaseViewSet):
    queryset = RDCValidacao.objects.select_related("rdc").all().order_by("-created_at")
    serializer_class = RDCValidacaoSerializer


class RDCMontagemAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        form = RDCMontagemForm(request.data)
        form.is_valid(raise_exception=True)
        rdc = montar_rdc_pre_preenchido(
            projeto_id=form.cleaned_data["projeto"].id,
            area_local_id=form.cleaned_data["area_local"].id,
            disciplina_id=form.cleaned_data["disciplina"].id,
            data=form.cleaned_data["data"],
            turno=form.cleaned_data["turno"],
            user=request.user,
        )
        return Response(RDCSerializer(rdc, context={"request": request}).data)

