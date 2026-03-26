from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.views import View

from core.exceptions import ContextualPermissionDenied
from core.mixins import RDCEditableMixin, RoleRequiredMixin


class _BaseOkView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("ok")


class _RoleAdminView(RoleRequiredMixin, _BaseOkView):
    allowed_roles = ["admin"]


class _AuditPermissionView(RoleRequiredMixin, _BaseOkView):
    required_permission = "rdc.audit.export"


class _WorkflowPermissionView(RoleRequiredMixin, _BaseOkView):
    required_permission = "rdc.workflow.execute"


class _RDCClosedByAttrView(RDCEditableMixin, _BaseOkView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rdc = SimpleNamespace(is_fechado=True)


class _RDCClosedByObjectView(RDCEditableMixin, _BaseOkView):
    def get_object(self):
        return SimpleNamespace(is_fechado=True)


class _RDCClosedByNestedObjectView(RDCEditableMixin, _BaseOkView):
    def get_object(self):
        return SimpleNamespace(rdc=SimpleNamespace(is_fechado=True))


class _RDCOpenView(RDCEditableMixin, _BaseOkView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rdc = SimpleNamespace(is_fechado=False)


class RoleRequiredMixinTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_allows_superuser(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=True,
            is_authenticated=True,
            perfil_acesso=None,
        )

        response = _RoleAdminView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_allows_unauthenticated_to_fall_through(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=False,
            perfil_acesso=None,
        )

        response = _RoleAdminView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_denies_user_without_profile(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
            perfil_acesso=None,
        )

        with self.assertRaises(ContextualPermissionDenied) as exc:
            _RoleAdminView.as_view()(request)

        self.assertEqual(exc.exception.code, "missing_profile")
        self.assertEqual(str(exc.exception), "Usuário sem perfil operacional definido.")

    def test_denies_user_with_insufficient_role(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
            perfil_acesso=SimpleNamespace(role="apontador"),
        )

        with self.assertRaises(ContextualPermissionDenied) as exc:
            _RoleAdminView.as_view()(request)

        self.assertEqual(exc.exception.code, "insufficient_role")
        self.assertEqual(
            str(exc.exception),
            "Você não tem permissão para acessar esta funcionalidade.",
        )

    def test_allows_user_with_required_role(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
            perfil_acesso=SimpleNamespace(role="admin"),
        )

        response = _RoleAdminView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_denies_when_audit_permission_is_missing(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
            perfil_acesso=SimpleNamespace(
                role="admin",
                permissions={"rdc.view"},
            ),
        )

        with self.assertRaises(ContextualPermissionDenied) as exc:
            _AuditPermissionView.as_view()(request)

        self.assertEqual(exc.exception.code, "permission_denied")
        self.assertEqual(
            str(exc.exception),
            "Seu perfil não possui a permissão necessária para executar esta ação.",
        )

    def test_allows_when_audit_permission_exists_in_permissions(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
            perfil_acesso=SimpleNamespace(
                role="admin",
                permissions={"rdc.audit.export", "rdc.view"},
            ),
        )

        response = _AuditPermissionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_allows_when_audit_permission_exists_in_permissoes(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
            perfil_acesso=SimpleNamespace(
                role="admin",
                permissoes={"rdc.audit.export"},
            ),
        )

        response = _AuditPermissionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_denies_when_workflow_permission_is_missing(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
            perfil_acesso=SimpleNamespace(
                role="admin",
                permissions={"rdc.audit.export"},
            ),
        )

        with self.assertRaises(ContextualPermissionDenied) as exc:
            _WorkflowPermissionView.as_view()(request)

        self.assertEqual(exc.exception.code, "permission_denied")

    def test_allows_when_workflow_permission_exists(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
            perfil_acesso=SimpleNamespace(
                role="admin",
                permissions={"rdc.workflow.execute"},
            ),
        )

        response = _WorkflowPermissionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")


class RDCEditableMixinTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_allows_superuser_even_when_rdc_is_closed(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=True,
            is_authenticated=True,
        )

        response = _RDCClosedByAttrView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_denies_when_self_rdc_is_closed(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
        )

        with self.assertRaises(ContextualPermissionDenied) as exc:
            _RDCClosedByAttrView.as_view()(request)

        self.assertEqual(exc.exception.code, "rdc_closed")
        self.assertEqual(str(exc.exception), "RDC está fechado e não pode ser alterado.")

    def test_denies_when_get_object_itself_is_closed(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
        )

        with self.assertRaises(ContextualPermissionDenied) as exc:
            _RDCClosedByObjectView.as_view()(request)

        self.assertEqual(exc.exception.code, "rdc_closed")

    def test_denies_when_nested_rdc_is_closed(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
        )

        with self.assertRaises(ContextualPermissionDenied) as exc:
            _RDCClosedByNestedObjectView.as_view()(request)

        self.assertEqual(exc.exception.code, "rdc_closed")

    def test_allows_when_rdc_is_open(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(
            is_superuser=False,
            is_authenticated=True,
        )

        response = _RDCOpenView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

