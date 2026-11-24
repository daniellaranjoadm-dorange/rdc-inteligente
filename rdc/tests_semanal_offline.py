from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cadastros.models import Projeto
from rdc.services.relatorio_semanal import dados_semana, enviar_relatorios_semanais, gerar_pdf_semanal

User = get_user_model()


class OfflineTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_off", "a@example.com", "x")

    def test_service_worker_na_raiz_controla_o_site(self):
        r = self.client.get("/sw.js")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Service-Worker-Allowed"], "/")
        self.assertIn("javascript", r["Content-Type"])
        self.assertIn("rdc-mobile-cache-v8", r.content.decode())

    def test_lista_de_telas_offline_exige_login(self):
        self.assertEqual(self.client.get(reverse("mobile-offline-urls")).status_code, 302)
        self.client.force_login(self.admin)
        urls = self.client.get(reverse("mobile-offline-urls")).json()["urls"]
        self.assertIn("/punch/nova/", urls)
        self.assertIn("/m/", urls)

    def test_paginas_carregam_a_caixa_de_saida_e_formularios_marcados(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("punch-create"))
        self.assertContains(r, "js/offline.js")
        self.assertContains(r, 'register("/sw.js"')
        self.assertContains(r, 'data-offline="Nova pendência (punch)"')
        self.assertContains(self.client.get("/m/"), "js/offline.js")


class RelatorioSemanalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin_sem", "a@example.com", "x")
        call_command("criar_projeto_demo", stdout=StringIO())
        cls.projeto = Projeto.objects.get(codigo="DEMO-PSV")

    def test_dados_e_pdf(self):
        dados = dados_semana(self.projeto)
        self.assertEqual(dados["fim"] - dados["inicio"], timedelta(days=6))
        self.assertGreater(dados["rdcs"], 0)
        self.assertTrue(any("Avanço da semana" in d for d in dados["destaques"]))
        self.assertTrue(any("Blocos liberados" in d for d in dados["destaques"]))
        pdf, _ = gerar_pdf_semanal(self.projeto)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 5000)

    def test_download_pela_tela(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("rdc-relatorio-semanal") + f"?projeto={self.projeto.pk}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertContains(self.client.get(reverse("rdc-blocos") + f"?projeto={self.projeto.pk}"), "Relatório semanal (PDF)")

    @override_settings(EMAIL_CONFIGURADO=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                       ALERTAS_TOKEN="tok-semanal")
    def test_envio_automatico_e_endpoint(self):
        self.assertEqual(enviar_relatorios_semanais(), 0)  # demo sem e-mails cadastrados: não envia
        Projeto.objects.filter(pk=self.projeto.pk).update(emails_relatorio="armador@example.com")
        url = reverse("tarefa-relatorio-semanal")
        self.assertEqual(self.client.post(url, HTTP_X_TAREFA_TOKEN="errado").status_code, 403)
        r = self.client.post(url, HTTP_X_TAREFA_TOKEN="tok-semanal")
        self.assertEqual(r.json(), {"ok": True, "emails": 1})
        email = mail.outbox[-1]
        self.assertEqual(email.to, ["armador@example.com"])
        self.assertIn("Relatório semanal", email.subject)
        self.assertTrue(email.attachments[0][0].endswith(".pdf"))

    @override_settings(EMAIL_CONFIGURADO=False)
    def test_sem_email_configurado_avisa(self):
        Projeto.objects.filter(pk=self.projeto.pk).update(emails_relatorio="armador@example.com")
        self.client.force_login(self.admin)
        r = self.client.post(reverse("rdc-relatorio-semanal-enviar"), {"projeto": self.projeto.pk}, follow=True)
        self.assertContains(r, "RESEND_API_KEY")

    def test_semana_sem_dados_nao_quebra(self):
        vazio = Projeto.objects.create(codigo="VAZIO", nome="Vazio", cliente="T")
        pdf, dados = gerar_pdf_semanal(vazio, timezone.localdate())
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(dados["rdcs"], 0)
