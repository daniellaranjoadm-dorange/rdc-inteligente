import re

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings


class BloqueioLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user("ana", "ana@example.com", "Senha-Forte-123")

    def _tentar(self, senha):
        return self.client.post("/accounts/login/", {"username": "ana", "password": senha})

    def test_bloqueia_apos_cinco_erros_ate_com_a_senha_certa(self):
        for _ in range(4):
            self.assertEqual(self._tentar("errada").status_code, 200)
        r = self._tentar("errada")
        self.assertContains(r, "bloqueado por 15 minutos")
        r = self._tentar("Senha-Forte-123")
        self.assertEqual(r.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_avisa_quando_faltam_poucas_tentativas(self):
        for _ in range(3):
            r = self._tentar("errada")
        self.assertContains(r, "Restam 2 tentativa(s)")

    def test_login_certo_zera_o_contador(self):
        for _ in range(3):
            self._tentar("errada")
        self.assertEqual(self._tentar("Senha-Forte-123").status_code, 302)
        self.client.logout()
        for _ in range(4):
            self._tentar("errada")
        self.assertEqual(self._tentar("Senha-Forte-123").status_code, 302)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RecuperarSenhaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ana", "ana@example.com", "Senha-Forte-123")

    def test_fluxo_completo_de_nova_senha(self):
        self.assertContains(self.client.get("/accounts/login/"), "Esqueci minha senha")
        r = self.client.post("/accounts/senha/esqueci/", {"email": "ana@example.com"})
        self.assertRedirects(r, "/accounts/senha/enviado/")
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r"https?://[^/]+(/accounts/senha/nova/\S+)", mail.outbox[0].body).group(1)

        r = self.client.get(link, follow=True)
        url_form = r.redirect_chain[-1][0] if r.redirect_chain else link
        r = self.client.post(url_form, {"new_password1": "Outra-Senha-456", "new_password2": "Outra-Senha-456"})
        self.assertRedirects(r, "/accounts/senha/pronto/")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Outra-Senha-456"))

    def test_email_desconhecido_nao_revela_nada(self):
        r = self.client.post("/accounts/senha/esqueci/", {"email": "naoexiste@example.com"})
        self.assertRedirects(r, "/accounts/senha/enviado/")
        self.assertEqual(len(mail.outbox), 0)

    def test_senha_fraca_e_recusada(self):
        self.client.post("/accounts/senha/esqueci/", {"email": "ana@example.com"})
        link = re.search(r"https?://[^/]+(/accounts/senha/nova/\S+)", mail.outbox[0].body).group(1)
        r = self.client.get(link, follow=True)
        url_form = r.redirect_chain[-1][0] if r.redirect_chain else link
        r = self.client.post(url_form, {"new_password1": "12345678", "new_password2": "12345678"})
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Senha-Forte-123"))
