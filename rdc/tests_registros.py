from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import PerfilAcesso
from cadastros.models import AreaLocal, Disciplina, Projeto
from core.choices import TurnoChoices
from rdc.models import RDC, RDCEquipamento, RDCOcorrencia

User = get_user_model()


class RegistrosBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_reg", "a@example.com", "x")
        projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="Transpetro")
        disc = Disciplina.objects.create(codigo="EST-R", nome="Estrutura R")
        area = AreaLocal.objects.create(projeto=projeto, codigo="D02P", descricao="Bloco D02P")
        self.rdc = RDC.objects.create(projeto=projeto, area_local=area, disciplina=disc, data=date(2026, 11, 23),
                                      turno=TurnoChoices.MANHA, criado_por=self.admin)
        self.client.force_login(self.admin)


class EquipamentoTests(RegistrosBase):
    def url(self, nome, **kw):
        return reverse(nome, kwargs={"pk": self.rdc.pk, **kw})

    def test_registra_equipamento_e_calcula_disponibilidade(self):
        r = self.client.post(self.url("rdc-equipamento-create"), {
            "tipo": "guindaste", "identificacao": "GD-03", "operador": "Fulano",
            "horas_trabalhadas": "6", "horas_paradas": "2", "motivo_parada": "clima",
        })
        self.assertEqual(r.status_code, 302)
        eq = RDCEquipamento.objects.get()
        self.assertEqual(eq.disponibilidade, Decimal("75.0"))
        self.assertEqual(eq.criado_por, self.admin)

    def test_horas_paradas_exigem_motivo(self):
        r = self.client.post(self.url("rdc-equipamento-create"), {"tipo": "portico", "horas_trabalhadas": "4", "horas_paradas": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Informe o motivo das horas paradas")
        self.assertFalse(RDCEquipamento.objects.exists())

    def test_nao_aceita_mais_de_24_horas(self):
        r = self.client.post(self.url("rdc-equipamento-create"), {"tipo": "compressor", "horas_trabalhadas": "20", "horas_paradas": "6", "motivo_parada": "quebra"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(RDCEquipamento.objects.exists())

    def test_edita_exclui_e_aparece_no_rdc(self):
        eq = RDCEquipamento.objects.create(rdc=self.rdc, tipo="maquina_solda", horas_trabalhadas=8)
        detalhe = self.client.get(reverse("rdc-detail", kwargs={"pk": self.rdc.pk}))
        self.assertContains(detalhe, 'id="equipamentos"')
        self.assertContains(detalhe, "Máquina de solda")
        self.client.post(self.url("rdc-equipamento-update", pk2=eq.pk), {"tipo": "maquina_solda", "horas_trabalhadas": "7", "horas_paradas": "0"})
        eq.refresh_from_db()
        self.assertEqual(eq.horas_trabalhadas, Decimal("7.00"))
        self.client.post(self.url("rdc-equipamento-delete", pk2=eq.pk))
        self.assertFalse(RDCEquipamento.objects.exists())


class OcorrenciaTests(RegistrosBase):
    def test_registra_ocorrencia_e_mostra_aberta_na_aba(self):
        r = self.client.post(reverse("rdc-ocorrencia-create", kwargs={"pk": self.rdc.pk}), {
            "tipo": "quase_acidente", "gravidade": "alta", "hora": "10:30", "local": "Anel 3 BB",
            "descricao": "Queda de ferramenta do andaime, sem atingir ninguém.", "acao_imediata": "Área isolada",
            "status": "aberta",
        })
        self.assertEqual(r.status_code, 302)
        oc = RDCOcorrencia.objects.get()
        self.assertTrue(oc.is_seguranca)
        detalhe = self.client.get(reverse("rdc-detail", kwargs={"pk": self.rdc.pk}))
        self.assertContains(detalhe, "Quase-acidente")
        self.assertContains(detalhe, "oc-alta")

    def test_encerrar_registra_data(self):
        oc = RDCOcorrencia.objects.create(rdc=self.rdc, tipo="nao_conformidade", descricao="Solda fora do procedimento")
        self.assertIsNone(oc.encerrada_em)
        oc.status = "encerrada"
        oc.save()
        self.assertIsNotNone(oc.encerrada_em)
        oc.status = "em_tratamento"
        oc.save()
        self.assertIsNone(oc.encerrada_em)

    def test_descricao_obrigatoria(self):
        r = self.client.post(reverse("rdc-ocorrencia-create", kwargs={"pk": self.rdc.pk}), {"tipo": "fiscalizacao", "gravidade": "baixa", "status": "aberta"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(RDCOcorrencia.objects.exists())

    def test_supervisor_bloqueado_em_rdc_fechado(self):
        sup = User.objects.create_user("sup_reg", password="x")
        PerfilAcesso.objects.create(user=sup, role="supervisor")
        self.rdc.status = "fechado"
        self.rdc.save()
        self.client.force_login(sup)
        self.assertEqual(self.client.get(reverse("rdc-ocorrencia-create", kwargs={"pk": self.rdc.pk})).status_code, 403)
        self.assertEqual(self.client.get(reverse("rdc-equipamento-create", kwargs={"pk": self.rdc.pk})).status_code, 403)
