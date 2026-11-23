from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cadastros.models import AreaLocal, Disciplina, Projeto
from core.choices import TurnoChoices
from rdc.models import RDC, RDCLinkAceite, RDCOcorrencia
from rdc.services.alertas_service import gerar_alertas

User = get_user_model()
TERCA = date(2026, 11, 24)


class AlertasTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_al", "a@example.com", "x")
        self.projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="T", emails_relatorio="plan@example.com")
        self.disc = Disciplina.objects.create(codigo="EST-AL", nome="Estrutura AL")
        self.area = AreaLocal.objects.create(projeto=self.projeto, codigo="D02P", descricao="Bloco D02P")

    def _rdc(self, dia, **kw):
        return RDC.objects.create(projeto=self.projeto, area_local=self.area, disciplina=self.disc, data=dia,
                                  turno=TurnoChoices.MANHA, criado_por=self.admin, **kw)

    def tipos(self, hoje=TERCA):
        return [a["tipo"] for a in gerar_alertas(hoje=hoje)]

    def test_frente_ativa_sem_rdc_hoje_gera_alerta_com_atalho_de_copia(self):
        ontem = self._rdc(TERCA - timedelta(days=1))
        alertas = gerar_alertas(hoje=TERCA)
        pendente = next(a for a in alertas if a["tipo"] == "rdc_pendente")
        self.assertIn("Bloco D02P", pendente["titulo"])
        self.assertEqual(pendente["url"], f"/rdc/{ontem.pk}/copiar/")
        self._rdc(TERCA)
        self.assertNotIn("rdc_pendente", self.tipos())

    def test_domingo_nao_cobra_rdc(self):
        self._rdc(date(2026, 11, 28))
        self.assertNotIn("rdc_pendente", self.tipos(hoje=date(2026, 11, 29)))

    def test_ocorrencia_grave_e_ocorrencia_antiga(self):
        r_hoje = self._rdc(TERCA)
        RDCOcorrencia.objects.create(rdc=r_hoje, tipo="quase_acidente", gravidade="alta", descricao="x")
        velho = self._rdc(TERCA - timedelta(days=6))
        RDCOcorrencia.objects.create(rdc=velho, tipo="nao_conformidade", gravidade="baixa", descricao="y")
        RDCOcorrencia.objects.create(rdc=velho, tipo="condicao_insegura", gravidade="baixa", descricao="z", status="encerrada")
        alertas = [a for a in gerar_alertas(hoje=TERCA) if a["tipo"] == "ocorrencia"]
        self.assertEqual(len(alertas), 2)
        self.assertEqual(alertas[0]["nivel"], "danger")

    def test_revisao_parada_e_aceite_expirando(self):
        r = self._rdc(TERCA, status="em_revisao")
        RDC.objects.filter(pk=r.pk).update(updated_at=timezone.now() - timedelta(days=3))
        RDCLinkAceite.objects.create(rdc=r, expira_em=timezone.now() + timedelta(hours=5))
        tipos = self.tipos()
        self.assertIn("revisao_parada", tipos)
        self.assertIn("aceite_expirando", tipos)

    def test_painel_mostra_alertas(self):
        self._rdc(timezone.localdate() - timedelta(days=1))
        self.client.force_login(self.admin)
        r = self.client.get(reverse("rdc-dashboard"))
        self.assertContains(r, "Alertas do dia")

    @override_settings(EMAIL_CONFIGURADO=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", ALERTAS_TOKEN="segredo-teste")
    def test_endpoint_do_agendador_exige_token_e_envia(self):
        self._rdc(timezone.localdate() - timedelta(days=1))
        url = reverse("tarefa-alertas")
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(self.client.post(url, HTTP_X_TAREFA_TOKEN="errado").status_code, 403)
        r = self.client.post(url, HTTP_X_TAREFA_TOKEN="segredo-teste")
        self.assertEqual(r.status_code, 200)
        if timezone.localdate().weekday() != 6:
            self.assertEqual(r.json()["emails"], 1)
            self.assertEqual(mail.outbox[0].to, ["plan@example.com"])

    @override_settings(ALERTAS_TOKEN="")
    def test_sem_token_configurado_nada_roda(self):
        self.assertEqual(self.client.post(reverse("tarefa-alertas"), HTTP_X_TAREFA_TOKEN="").status_code, 403)
