from django.test import RequestFactory, SimpleTestCase

from core.error_views import erro_403
from core.exceptions import ContextualPermissionDenied


class Error403Tests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_missing_profile_context(self):
        request = self.factory.get("/rota-protegida/")
        response = erro_403(
            request,
            ContextualPermissionDenied(
                code="missing_profile",
                message="Usuário sem perfil operacional definido.",
            ),
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Perfil operacional não configurado", status_code=403)
        self.assertContains(
            response,
            "Seu usuário ainda não possui perfil operacional ativo para executar esta ação.",
            status_code=403,
        )
        self.assertContains(
            response,
            "Solicite ao administrador a configuração do seu acesso.",
            status_code=403,
        )
        self.assertContains(response, "missing_profile", status_code=403)

    def test_rdc_closed_context(self):
        request = self.factory.get("/rdc/1/editar/")
        response = erro_403(
            request,
            ContextualPermissionDenied(
                code="rdc_closed",
                message="RDC está fechado e não pode ser alterado.",
            ),
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "RDC fechado", status_code=403)
        self.assertContains(
            response,
            "Este RDC está fechado e não aceita novas alterações.",
            status_code=403,
        )
        self.assertContains(
            response,
            "Consulte um responsável caso seja necessário reabrir o fluxo.",
            status_code=403,
        )
        self.assertContains(response, "rdc_closed", status_code=403)

    def test_unknown_code_falls_back_to_default_forbidden(self):
        request = self.factory.get("/qualquer/")
        response = erro_403(
            request,
            ContextualPermissionDenied(
                code="codigo_desconhecido",
                message="Mensagem irrelevante para fallback.",
            ),
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso negado", status_code=403)
        self.assertContains(
            response,
            "Você não tem permissão para acessar esta área.",
            status_code=403,
        )
        self.assertContains(
            response,
            "Se isso parece incorreto, fale com o administrador do sistema.",
            status_code=403,
        )
        self.assertContains(response, "codigo_desconhecido", status_code=403)

    def test_logs_access_denied_event(self):
        request = self.factory.get("/rota-protegida/")
        request.user = type(
            "User",
            (),
            {"id": 99, "username": "daniel"},
        )()

        with self.assertLogs("core.error_views", level="WARNING") as captured:
            response = erro_403(
                request,
                ContextualPermissionDenied(
                    code="missing_profile",
                    message="Usuário sem perfil operacional definido.",
                ),
            )

        self.assertEqual(response.status_code, 403)
        joined = "\n".join(captured.output)
        self.assertIn("access_denied", joined)
