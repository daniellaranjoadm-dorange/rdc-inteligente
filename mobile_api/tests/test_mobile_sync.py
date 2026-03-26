from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import PerfilAcesso

class MobileSyncTests(TestCase):

    def setUp(self):
        self.url = "/api/mobile/sync/"
        self.User = get_user_model()

        self.user = self.User.objects.create_user(
            username="testuser",
            password="123456"
        )

        # 🔥 CRÍTICO: cria perfil com role válida
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

    def _payload(self):
        return {
            "rdcs": [],
            "funcionarios": [],
            "atividades": [],
            "apontamentos": [],
            "last_sync_at": None,
        }

    def test_sync_requires_authentication(self):
        response = self.client.post(self.url, data=self._payload(), content_type="application/json")
        self.assertIn(response.status_code, [401, 403])

    def test_sync_requires_role(self):
        user = self.User.objects.create_user(username="sem_role", password="123456")
        self.client.login(username="sem_role", password="123456")

        response = self.client.post(self.url, data=self._payload(), content_type="application/json")

        self.assertEqual(response.status_code, 403)

    def test_sync_success_with_valid_role(self):
        self.client.login(username="testuser", password="123456")

        response = self.client.post(self.url, data=self._payload(), content_type="application/json")

        self.assertEqual(response.status_code, 200)

    def test_sync_response_structure(self):
        self.client.login(username="testuser", password="123456")

        response = self.client.post(self.url, data=self._payload(), content_type="application/json")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("received", data)
        self.assertIn("server_changes", data)
        self.assertIn("sync_time", data)

    def test_sync_empty_payload_safe(self):
        self.client.login(username="testuser", password="123456")

        response = self.client.post(self.url, data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)

