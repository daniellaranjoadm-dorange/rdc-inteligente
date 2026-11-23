from datetime import date, time
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from cadastros.models import AreaLocal, Disciplina, Projeto
from core.choices import TurnoChoices
from rdc.models import RDC, RDCEquipamento, RDCOcorrencia, RDCParalisacao
from rdc.services.email_service import separar_emails
from rdc.services.relatorio_rdc import gerar_pdf_rdc
from rdc.services.workflow_service import process_rdc_workflow_action

User = get_user_model()
EMAIL_OK = dict(EMAIL_CONFIGURADO=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")


class EmailRDCTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_em", "a@example.com", "x")
        self.projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="Transpetro",
                                              emails_relatorio="plan@example.com, fiscal@example.com")
        disc = Disciplina.objects.create(codigo="EST-E", nome="Estrutura E")
        area = AreaLocal.objects.create(projeto=self.projeto, codigo="D02P", descricao="Bloco D02P", tipo="bloco")
        self.rdc = RDC.objects.create(projeto=self.projeto, area_local=area, disciplina=disc, data=date(2026, 11, 23),
                                      turno=TurnoChoices.MANHA, criado_por=self.admin)
        RDCParalisacao.objects.create(rdc=self.rdc, motivo="chuva", inicio=time(9), fim=time(10), pessoas_afetadas=3)
        RDCEquipamento.objects.create(rdc=self.rdc, tipo="guindaste", horas_trabalhadas=6, horas_paradas=2, motivo_parada="clima")
        RDCOcorrencia.objects.create(rdc=self.rdc, tipo="quase_acidente", hora=time(11), local="Anel 3", descricao="Queda de ferramenta")
        self.client.force_login(self.admin)

    def test_pdf_do_rdc(self):
        pdf = gerar_pdf_rdc(self.rdc, gerado_por=self.admin)
        self.assertTrue(pdf.startswith(b"%PDF"))
        r = self.client.get(reverse("rdc-pdf", kwargs={"pk": self.rdc.pk}), {"ver": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("inline", r["Content-Disposition"])

    def test_separar_emails(self):
        ok, ruins = separar_emails("a@x.com; b@y.com,\n a@x.com  nao-e-email")
        self.assertEqual(ok, ["a@x.com", "b@y.com"])
        self.assertEqual(ruins, ["nao-e-email"])

    @override_settings(**EMAIL_OK)
    def test_envio_manual_com_pdf_anexo(self):
        r = self.client.post(reverse("rdc-enviar-email", kwargs={"pk": self.rdc.pk}), {"destinatarios": "chefe@example.com"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["chefe@example.com"])
        self.assertIn(f"RDC #{self.rdc.pk}", msg.subject)
        self.assertTrue(any(nome.endswith(".pdf") for nome, _, _ in msg.attachments))

    @override_settings(**EMAIL_OK)
    def test_email_invalido_nao_envia(self):
        self.client.post(reverse("rdc-enviar-email", kwargs={"pk": self.rdc.pk}), {"destinatarios": "isso nao"})
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_CONFIGURADO=False, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_sem_configuracao_avisa_e_nao_envia(self):
        r = self.client.post(reverse("rdc-enviar-email", kwargs={"pk": self.rdc.pk}), {"destinatarios": "a@example.com"}, follow=True)
        self.assertContains(r, "não está configurado")
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(**EMAIL_OK)
    def test_fechar_rdc_envia_para_os_emails_do_projeto(self):
        with self.captureOnCommitCallbacks(execute=True):
            resultado = process_rdc_workflow_action(self.rdc, action="fechar", user=self.admin)
        self.assertNotEqual(resultado.get("ok"), False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["plan@example.com", "fiscal@example.com"])

    @override_settings(**EMAIL_OK)
    def test_falha_no_email_nao_impede_fechar(self):
        with mock.patch("rdc.services.email_service.enviar_rdc_por_email", side_effect=RuntimeError("smtp fora")):
            with self.captureOnCommitCallbacks(execute=True):
                process_rdc_workflow_action(self.rdc, action="fechar", user=self.admin)
        self.rdc.refresh_from_db()
        self.assertEqual(self.rdc.status, "fechado")

    def test_projeto_valida_emails_no_cadastro(self):
        r = self.client.post(reverse("projeto-create"), {"codigo": "G7", "nome": "G7", "cliente": "T", "emails_relatorio": "ok@x.com, ruim", "ativo": "on"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "E-mail inválido")
