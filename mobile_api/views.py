from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from cadastros.models import AreaLocal, Disciplina, Equipe, Funcionario, Projeto
from rdc.models import RDC, RDCAtividade, RDCApontamento, RDCFuncionario

from .permissions import PerfilRolePermission

from .serializers import (
    MobileAreaLocalSerializer,
    MobileBaseOperacionalSerializer,
    MobileDisciplinaSerializer,
    MobileEquipeSerializer,
    MobileFuncionarioSerializer,
    MobileMeSerializer,
    MobileProjetoSerializer,
    MobileRDCAtividadeCreateSerializer,
    MobileRDCAtividadeSerializer,
    MobileRDCAtividadeUpdateSerializer,
    MobileRDCApontamentoCreateSerializer,
    MobileRDCApontamentoSerializer,
    MobileRDCApontamentoUpdateSerializer,
    MobileRDCDetailSerializer,
    MobileRDCFuncionarioCreateSerializer,
    MobileRDCFuncionarioSerializer,
    MobileRDCFuncionarioUpdateSerializer,
    MobileRDCListSerializer,
    MobileRDCCreateSerializer,
    MobileRDCUpdateSerializer,
)


class MeAPIView(APIView):
    permission_classes = [PerfilRolePermission]

    def get(self, request, *args, **kwargs):
        data = {
            "id": request.user.id,
            "username": request.user.username,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "is_staff": request.user.is_staff,
            "is_superuser": request.user.is_superuser,
        }
        serializer = MobileMeSerializer(data)
        return Response(serializer.data)


class BaseOperacionalAPIView(APIView):
    permission_classes = [PerfilRolePermission]

    def get(self, request, *args, **kwargs):
        data_ref = request.GET.get("data")
        referencia = timezone.localdate()
        if data_ref:
            try:
                referencia = timezone.datetime.fromisoformat(data_ref).date()
            except ValueError:
                pass

        projeto_id = (request.GET.get("projeto") or "").strip()
        disciplina_id = (request.GET.get("disciplina") or "").strip()
        area_id = (request.GET.get("area_local") or "").strip()

        projetos = Projeto.objects.filter(ativo=True).order_by("codigo", "nome")
        disciplinas = Disciplina.objects.filter(ativo=True).order_by("nome")
        areas = AreaLocal.objects.filter(ativo=True).order_by("codigo", "descricao")
        equipes = Equipe.objects.filter(ativa=True).order_by("nome")
        funcionarios = (
            Funcionario.objects.filter(ativo=True)
            .select_related("funcao")
            .order_by("nome")
        )

        rdcs = (
            RDC.objects.select_related("projeto", "disciplina", "area_local", "supervisor")
            .filter(data=referencia, sync_deleted_at__isnull=True)
            .annotate(
                total_atividades=Count("atividades", distinct=True),
                total_funcionarios=Count("funcionarios", distinct=True),
                total_apontamentos=Count("apontamentos", distinct=True),
            )
            .order_by("projeto__codigo", "disciplina__nome", "area_local__descricao", "id")
        )

        if projeto_id:
            rdcs = rdcs.filter(projeto_id=projeto_id)
        if disciplina_id:
            rdcs = rdcs.filter(disciplina_id=disciplina_id)
        if area_id:
            rdcs = rdcs.filter(area_local_id=area_id)

        payload = {
            "referencia": referencia,
            "projetos": projetos,
            "disciplinas": disciplinas,
            "areas": areas,
            "equipes": equipes,
            "funcionarios": funcionarios,
            "rdcs": rdcs,
        }
        serializer = MobileBaseOperacionalSerializer(payload, context={"request": request})
        return Response(serializer.data)


class MobileRDCListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [PerfilRolePermission]
    allowed_roles_by_method = {
        "GET": ["admin", "supervisor", "operador"],
        "POST": ["admin", "supervisor"],
    }

    def get_queryset(self):
        queryset = (
            RDC.objects.select_related("projeto", "disciplina", "area_local", "supervisor")
            .annotate(
                total_atividades=Count("atividades", distinct=True),
                total_funcionarios=Count("funcionarios", distinct=True),
                total_apontamentos=Count("apontamentos", distinct=True),
            )
            .filter(sync_deleted_at__isnull=True)
            .order_by("-data", "-id")
        )

        data_ini = (self.request.GET.get("data_ini") or "").strip()
        data_fim = (self.request.GET.get("data_fim") or "").strip()
        projeto_id = (self.request.GET.get("projeto") or "").strip()
        disciplina_id = (self.request.GET.get("disciplina") or "").strip()
        status_param = (self.request.GET.get("status") or "").strip()

        if data_ini:
            queryset = queryset.filter(data__gte=data_ini)
        if data_fim:
            queryset = queryset.filter(data__lte=data_fim)
        if projeto_id:
            queryset = queryset.filter(projeto_id=projeto_id)
        if disciplina_id:
            queryset = queryset.filter(disciplina_id=disciplina_id)
        if status_param:
            queryset = queryset.filter(status=status_param)

        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MobileRDCCreateSerializer
        return MobileRDCListSerializer

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        read_serializer = MobileRDCDetailSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class MobileRDCDetailAPIView(generics.RetrieveAPIView):
    permission_classes = [PerfilRolePermission]
    serializer_class = MobileRDCDetailSerializer
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return (
            RDC.objects.select_related("projeto", "disciplina", "area_local", "supervisor")
            .prefetch_related("atividades", "funcionarios", "apontamentos", "validacoes")
            .filter(sync_deleted_at__isnull=True)
            .order_by("-data", "-id")
        )


class MobileRDCFuncionarioListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [PerfilRolePermission]
    allowed_roles_by_method = {
        "GET": ["admin", "supervisor", "operador"],
        "POST": ["admin", "supervisor"],
    }

    def get_rdc(self):
        return get_object_or_404(RDC, pk=self.kwargs["pk"])

    def get_queryset(self):
        return (
            RDCFuncionario.objects.select_related(
                "funcionario",
                "funcao",
                "equipe",
                "liberado_por",
            )
            .filter(rdc=self.get_rdc(), sync_deleted_at__isnull=True)
            .order_by("nome")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MobileRDCFuncionarioCreateSerializer
        return MobileRDCFuncionarioSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["rdc"] = self.get_rdc()
        return context

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        read_serializer = MobileRDCFuncionarioSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class MobileRDCAtividadeListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [PerfilRolePermission]
    allowed_roles_by_method = {
        "GET": ["admin", "supervisor", "operador"],
        "POST": ["admin", "supervisor"],
    }

    def get_rdc(self):
        return get_object_or_404(RDC, pk=self.kwargs["pk"])

    def get_queryset(self):
        return (
            RDCAtividade.objects.select_related("atividade_cronograma")
            .filter(rdc=self.get_rdc(), sync_deleted_at__isnull=True)
            .order_by("codigo_atividade", "codigo_subatividade")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MobileRDCAtividadeCreateSerializer
        return MobileRDCAtividadeSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["rdc"] = self.get_rdc()
        return context

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        read_serializer = MobileRDCAtividadeSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class MobileRDCApontamentoListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [PerfilRolePermission]
    allowed_roles_by_method = {
        "GET": ["admin", "supervisor", "operador"],
        "POST": ["admin", "supervisor"],
    }

    def get_rdc(self):
        return get_object_or_404(RDC, pk=self.kwargs["pk"])

    def get_queryset(self):
        return (
            RDCApontamento.objects.select_related("rdc_funcionario", "rdc_atividade")
            .filter(rdc=self.get_rdc(), sync_deleted_at__isnull=True)
            .order_by("rdc_funcionario__nome", "id")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MobileRDCApontamentoCreateSerializer
        return MobileRDCApontamentoSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["rdc"] = self.get_rdc()
        return context

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        read_serializer = MobileRDCApontamentoSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class MobileRDCRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [PerfilRolePermission]
    allowed_roles_by_method = {
        "GET": ["admin", "supervisor", "operador"],
        "PUT": ["admin", "supervisor"],
        "PATCH": ["admin", "supervisor"],
        "DELETE": ["admin"],
    }
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return (
            RDC.objects.select_related("projeto", "disciplina", "area_local", "supervisor")
            .prefetch_related("atividades", "funcionarios", "apontamentos", "validacoes")
            .order_by("-data", "-id")
        )

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return MobileRDCUpdateSerializer
        return MobileRDCDetailSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", request.method == "PATCH")
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read_serializer = MobileRDCDetailSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.marcar_excluido_sync()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MobileRDCFuncionarioRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [PerfilRolePermission]
    allowed_roles_by_method = {
        "GET": ["admin", "supervisor", "operador"],
        "PUT": ["admin", "supervisor"],
        "PATCH": ["admin", "supervisor"],
        "DELETE": ["admin"],
    }
    lookup_url_kwarg = "item_pk"

    def get_queryset(self):
        rdc = get_object_or_404(RDC, pk=self.kwargs["pk"])
        return (
            RDCFuncionario.objects.select_related(
                "funcionario",
                "funcao",
                "equipe",
                "liberado_por",
            )
            .filter(rdc=rdc, sync_deleted_at__isnull=True)
            .order_by("nome")
        )

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return MobileRDCFuncionarioUpdateSerializer
        return MobileRDCFuncionarioSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", request.method == "PATCH")
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read_serializer = MobileRDCFuncionarioSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.marcar_excluido_sync()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MobileRDCAtividadeRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [PerfilRolePermission]
    allowed_roles_by_method = {
        "GET": ["admin", "supervisor", "operador"],
        "PUT": ["admin", "supervisor"],
        "PATCH": ["admin", "supervisor"],
        "DELETE": ["admin"],
    }
    lookup_url_kwarg = "item_pk"

    def get_queryset(self):
        rdc = get_object_or_404(RDC, pk=self.kwargs["pk"])
        return (
            RDCAtividade.objects.select_related("atividade_cronograma")
            .filter(rdc=rdc, sync_deleted_at__isnull=True)
            .order_by("codigo_atividade", "codigo_subatividade")
        )

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return MobileRDCAtividadeUpdateSerializer
        return MobileRDCAtividadeSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", request.method == "PATCH")
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read_serializer = MobileRDCAtividadeSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.marcar_excluido_sync()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MobileRDCApontamentoRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [PerfilRolePermission]
    allowed_roles_by_method = {
        "GET": ["admin", "supervisor", "operador"],
        "PUT": ["admin", "supervisor"],
        "PATCH": ["admin", "supervisor"],
        "DELETE": ["admin"],
    }
    lookup_url_kwarg = "item_pk"

    def get_queryset(self):
        rdc = get_object_or_404(RDC, pk=self.kwargs["pk"])
        return (
            RDCApontamento.objects.select_related("rdc_funcionario", "rdc_atividade")
            .filter(rdc=rdc, sync_deleted_at__isnull=True)
            .order_by("rdc_funcionario__nome", "id")
        )

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return MobileRDCApontamentoUpdateSerializer
        return MobileRDCApontamentoSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", request.method == "PATCH")
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        read_serializer = MobileRDCApontamentoSerializer(
            instance,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.marcar_excluido_sync()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _parse_sync_timestamp(value):
    if not value:
        return None

def _parse_client_timestamp(value):
    if not value:
        return None
    try:
        dt = timezone.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except Exception:
        return None


def _server_is_newer(instance, item):
    if not instance:
        return False

    client_dt = _parse_client_timestamp(item.get("client_changed_at"))
    server_dt = getattr(instance, "sync_updated_at", None)

    if not client_dt or not server_dt:
        return False

    if timezone.is_naive(server_dt):
        server_dt = timezone.make_aware(server_dt, timezone.get_current_timezone())

    return server_dt > client_dt


def _append_conflict(response_data, scope, item, instance, reason="server_newer"):
    response_data["conflicts"].append({
        "scope": scope,
        "reason": reason,
        "item": item,
        "server_id": getattr(instance, "pk", None),
        "server_mobile_uuid": getattr(instance, "mobile_uuid", None),
        "server_sync_updated_at": getattr(instance, "sync_updated_at", None),
    })
    try:
        dt = timezone.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except Exception:
        return None


class MobileSyncAPIView(APIView):
    permission_classes = [PerfilRolePermission]
    allowed_roles = ["admin", "supervisor"]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        payload = request.data or {}
        response_data = {
            "received": {
                "rdcs": 0,
                "funcionarios": 0,
                "atividades": 0,
                "apontamentos": 0,
            },
            "errors": [],
            "conflicts": [],
            "server_changes": {},
            "sync_time": timezone.now(),
        }

        self._sync_rdcs(payload.get("rdcs") or [], request, response_data)
        self._sync_funcionarios(payload.get("funcionarios") or [], request, response_data)
        self._sync_atividades(payload.get("atividades") or [], request, response_data)
        self._sync_apontamentos(payload.get("apontamentos") or [], request, response_data)

        response_data["server_changes"] = self._server_changes_since(
            _parse_sync_timestamp(payload.get("last_sync_at"))
        )
        return Response(response_data, status=status.HTTP_200_OK)

    def _server_changes_since(self, last_sync_at):
        rdcs_qs = RDC.objects.all()
        funcs_qs = RDCFuncionario.objects.all()
        atvs_qs = RDCAtividade.objects.all()
        aps_qs = RDCApontamento.objects.all()

        if last_sync_at:
            rdcs_qs = rdcs_qs.filter(sync_updated_at__gte=last_sync_at)
            funcs_qs = funcs_qs.filter(sync_updated_at__gte=last_sync_at)
            atvs_qs = atvs_qs.filter(sync_updated_at__gte=last_sync_at)
            aps_qs = aps_qs.filter(sync_updated_at__gte=last_sync_at)

        return {
            "rdcs": MobileRDCListSerializer(
                rdcs_qs.order_by("-sync_updated_at")[:200],
                many=True,
            ).data,
            "funcionarios": MobileRDCFuncionarioSerializer(
                funcs_qs.order_by("-sync_updated_at")[:500],
                many=True,
            ).data,
            "atividades": MobileRDCAtividadeSerializer(
                atvs_qs.order_by("-sync_updated_at")[:500],
                many=True,
            ).data,
            "apontamentos": MobileRDCApontamentoSerializer(
                aps_qs.order_by("-sync_updated_at")[:500],
                many=True,            ).data,
            "importacoes": MobileImportacaoSerializer(
                ImportacaoArquivo.objects.order_by("-created_at")[:200],
                many=True,
            ).data,
        }

    def _resolve_rdc(self, item):
        obj = None
        if item.get("rdc_mobile_uuid"):
            obj = RDC.objects.filter(mobile_uuid=item.get("rdc_mobile_uuid")).first()
        if not obj and item.get("rdc"):
            obj = RDC.objects.filter(pk=item.get("rdc")).first()
        return obj

    def _resolve_rdc_funcionario(self, item):
        obj = None
        if item.get("rdc_funcionario_mobile_uuid"):
            obj = RDCFuncionario.objects.filter(
                mobile_uuid=item.get("rdc_funcionario_mobile_uuid")
            ).first()
        if not obj and item.get("rdc_funcionario"):
            obj = RDCFuncionario.objects.filter(pk=item.get("rdc_funcionario")).first()
        return obj

    def _resolve_rdc_atividade(self, item):
        obj = None
        if item.get("rdc_atividade_mobile_uuid"):
            obj = RDCAtividade.objects.filter(
                mobile_uuid=item.get("rdc_atividade_mobile_uuid")
            ).first()
        if not obj and item.get("rdc_atividade"):
            obj = RDCAtividade.objects.filter(pk=item.get("rdc_atividade")).first()
        return obj

    def _sync_rdcs(self, items, request, response_data):
        for item in items:
            response_data["received"]["rdcs"] += 1
            try:
                mobile_uuid = item.get("mobile_uuid")
                op = item.get("op", "upsert")
                instance = (
                    RDC.objects.filter(mobile_uuid=mobile_uuid).first()
                    if mobile_uuid
                    else None
                )

                if op == "delete":
                    if instance:
                        instance.marcar_excluido_sync()
                    continue

                data = dict(item)
                data.pop("op", None)

                if instance:
                    serializer = MobileRDCUpdateSerializer(
                        instance,
                        data=data,
                        partial=True,
                        context={"request": request},
                    )
                else:
                    serializer = MobileRDCCreateSerializer(
                        data=data,
                        context={"request": request},
                    )

                serializer.is_valid(raise_exception=True)
                serializer.save()
            except Exception as exc:
                response_data["errors"].append(
                    {"scope": "rdcs", "item": item, "error": str(exc)}
                )

    def _sync_funcionarios(self, items, request, response_data):
        for item in items:
            response_data["received"]["funcionarios"] += 1
            try:
                mobile_uuid = item.get("mobile_uuid")
                op = item.get("op", "upsert")
                instance = (
                    RDCFuncionario.objects.filter(mobile_uuid=mobile_uuid).first()
                    if mobile_uuid
                    else None
                )

                if op == "delete":
                    if instance:
                        instance.marcar_excluido_sync()
                    continue

                rdc = self._resolve_rdc(item)
                if not rdc and not instance:
                    raise ValueError("RDC de referência não localizado para o funcionário.")

                data = dict(item)
                for key in ["op", "rdc", "rdc_mobile_uuid"]:
                    data.pop(key, None)

                if instance:
                    serializer = MobileRDCFuncionarioUpdateSerializer(
                        instance,
                        data=data,
                        partial=True,
                        context={"request": request, "rdc": instance.rdc},
                    )
                else:
                    serializer = MobileRDCFuncionarioCreateSerializer(
                        data=data,
                        context={"request": request, "rdc": rdc},
                    )

                serializer.is_valid(raise_exception=True)
                serializer.save()
            except Exception as exc:
                response_data["errors"].append(
                    {"scope": "funcionarios", "item": item, "error": str(exc)}
                )

    def _sync_atividades(self, items, request, response_data):
        for item in items:
            response_data["received"]["atividades"] += 1
            try:
                mobile_uuid = item.get("mobile_uuid")
                op = item.get("op", "upsert")
                instance = (
                    RDCAtividade.objects.filter(mobile_uuid=mobile_uuid).first()
                    if mobile_uuid
                    else None
                )

                if op == "delete":
                    if instance:
                        instance.marcar_excluido_sync()
                    continue

                rdc = self._resolve_rdc(item)
                if not rdc and not instance:
                    raise ValueError("RDC de referência não localizado para a atividade.")

                data = dict(item)
                for key in ["op", "rdc", "rdc_mobile_uuid"]:
                    data.pop(key, None)

                if instance:
                    serializer = MobileRDCAtividadeUpdateSerializer(
                        instance,
                        data=data,
                        partial=True,
                    )
                else:
                    serializer = MobileRDCAtividadeCreateSerializer(
                        data=data,
                        context={"request": request, "rdc": rdc},
                    )

                serializer.is_valid(raise_exception=True)
                serializer.save()
            except Exception as exc:
                response_data["errors"].append(
                    {"scope": "atividades", "item": item, "error": str(exc)}
                )

    def _sync_apontamentos(self, items, request, response_data):
        for item in items:
            response_data["received"]["apontamentos"] += 1
            try:
                mobile_uuid = item.get("mobile_uuid")
                op = item.get("op", "upsert")
                instance = (
                    RDCApontamento.objects.filter(mobile_uuid=mobile_uuid).first()
                    if mobile_uuid
                    else None
                )

                if op == "delete":
                    if instance:
                        instance.marcar_excluido_sync()
                    continue

                rdc = self._resolve_rdc(item)
                if not rdc and not instance:
                    raise ValueError("RDC de referência não localizado para o apontamento.")

                data = dict(item)
                for key in ["op", "rdc", "rdc_mobile_uuid"]:
                    data.pop(key, None)

                func = self._resolve_rdc_funcionario(item)
                atv = self._resolve_rdc_atividade(item)

                if func:
                    data["rdc_funcionario"] = func.pk
                if atv:
                    data["rdc_atividade"] = atv.pk

                if instance:
                    serializer = MobileRDCApontamentoUpdateSerializer(
                        instance,
                        data=data,
                        partial=True,
                    )
                else:
                    serializer = MobileRDCApontamentoCreateSerializer(
                        data=data,
                        context={"request": request, "rdc": rdc},
                    )

                serializer.is_valid(raise_exception=True)
                serializer.save()
            except Exception as exc:
                response_data["errors"].append(
                    {"scope": "apontamentos", "item": item, "error": str(exc)}
                )





from importacoes.models import ImportacaoArquivo
from .serializers import MobileImportacaoSerializer

class MobileImportacaoListAPIView(generics.ListAPIView):
    permission_classes = [PerfilRolePermission]
    serializer_class = MobileImportacaoSerializer
    allowed_roles = ["admin", "supervisor"]

    def get_queryset(self):
        return ImportacaoArquivo.objects.order_by("-created_at")[:100]






