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

    def test_mobile_home_requires_login(self):
        response = self.client.get("/m/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/login/?next=/m/")

    def test_root_sends_visitor_to_single_login_page(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/login/?next=/m/")


class BrandedPagesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin_teste", "admin@example.com", "senha-teste-123")

    def test_login_page_uses_brand(self):
        response = self.client.get("/accounts/login/")

        self.assertContains(response, "css/dorange.css")
        self.assertContains(response, "RDC Inteligente")

    def test_wrong_password_shows_friendly_error(self):
        response = self.client.post("/accounts/login/", {"username": "admin_teste", "password": "errada"})

        self.assertContains(response, "Usuário ou senha incorretos")

    def test_logged_user_sees_mobile_home_with_working_links(self):
        self.client.force_login(self.user)

        response = self.client.get("/m/")

        self.assertContains(response, 'href="/rdc/novo/"')
        self.assertContains(response, 'href="/cadastros/funcionarios/"')
        self.assertContains(response, 'href="/rdc/dashboard/"')
        self.assertNotContains(response, 'href="/cadastros/"')

    def test_logout_works_and_returns_to_login(self):
        self.client.force_login(self.user)

        response = self.client.post("/accounts/logout/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/login/")
        self.assertEqual(self.client.get("/m/").status_code, 302)
