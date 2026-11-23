from django.contrib.auth.models import User
from django.test import TestCase


class AnonymousRedirectsToLoginTests(TestCase):
    """Areas internas levam o visitante sem login para a tela de login."""

    def test_rdc_list_redirects_anonymous_to_login(self):
        response = self.client.get("/rdc/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/login/?next=/rdc/")

    def test_cadastros_redirects_anonymous_to_login(self):
        response = self.client.get("/cadastros/funcionarios/")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/accounts/login/?next="))

    def test_login_returns_to_requested_page(self):
        User.objects.create_superuser("admin_teste", "admin@example.com", "senha-teste-123")

        response = self.client.post(
            "/accounts/login/?next=/rdc/",
            {"username": "admin_teste", "password": "senha-teste-123"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/rdc/")
