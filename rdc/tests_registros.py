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


class CopiarRDCTests(RegistrosBase):
    def test_copia_equipe_atividades_e_equipamentos_zerando_o_dia(self):
        from cadastros.models import Empresa, Funcao, Funcionario
        from rdc.models import RDCAtividade, RDCFuncionario
        emp = Empresa.objects.create(nome="Emp")
        fun = Funcao.objects.create(codigo="SOL", nome="Soldador")
        f = Funcionario.objects.create(matricula="M1", nome="Fulano", funcao=fun, empresa=emp)
        RDCFuncionario.objects.create(rdc=self.rdc, funcionario=f, funcao=fun, matricula="M1", nome="Fulano",
                                      hora_normal=8, hora_extra=2, presente_catraca=True, confirmado_supervisor=True)
        RDCAtividade.objects.create(rdc=self.rdc, codigo_atividade="A1", descr_atividade="Solda anel 3",
                                    qtd_escopo=10, qtd_executada=4, origem="manual")
        RDCEquipamento.objects.create(rdc=self.rdc, tipo="guindaste", identificacao="GD-03", horas_trabalhadas=6)
        RDCOcorrencia.objects.create(rdc=self.rdc, tipo="quase_acidente", descricao="x")

        r = self.client.post(reverse("rdc-copiar", kwargs={"pk": self.rdc.pk}), {
            "data": "2026-11-24", "turno": "manha", "funcionarios": "on", "atividades": "on", "equipamentos": "on"})
        self.assertEqual(r.status_code, 302)
        novo = RDC.objects.exclude(pk=self.rdc.pk).get()
        self.assertEqual(novo.status, "rascunho")
        nf = novo.funcionarios.get()
        self.assertEqual((nf.hh_total, nf.presente_catraca, nf.confirmado_supervisor), (Decimal("10.00"), False, False))
        self.assertEqual(novo.atividades.get().qtd_executada, Decimal("0"))
        self.assertEqual(novo.equipamentos.get().horas_trabalhadas, Decimal("0"))
        self.assertFalse(novo.ocorrencias.exists())
        self.assertNotEqual(nf.mobile_uuid, self.rdc.funcionarios.get().mobile_uuid)

    def test_nao_duplica_rdc_do_mesmo_dia_e_turno(self):
        r = self.client.post(reverse("rdc-copiar", kwargs={"pk": self.rdc.pk}), {"data": "2026-11-23", "turno": "manha"})
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "Já existe RDC", status_code=400)

    def test_tela_sugere_o_dia_seguinte(self):
        r = self.client.get(reverse("rdc-copiar", kwargs={"pk": self.rdc.pk}))
        self.assertContains(r, 'value="2026-11-24"')


class EditarRDCDataTests(RegistrosBase):
    def test_editar_rdc_mostra_a_data_preenchida(self):
        r = self.client.get(reverse("rdc-update", kwargs={"pk": self.rdc.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'value="2026-11-23"')

    def test_editar_rdc_salva_e_volta_para_o_detalhe(self):
        r = self.client.post(reverse("rdc-update", kwargs={"pk": self.rdc.pk}), {
            "projeto": self.rdc.projeto_id, "area_local": self.rdc.area_local_id, "disciplina": self.rdc.disciplina_id,
            "data": "2026-11-23", "turno": "manha", "observacoes": "Ajuste de teste", "status": self.rdc.status,
        })
        self.assertEqual(r.status_code, 302, getattr(r, "context", {}) and r.context["form"].errors)
        self.assertEqual(r["Location"], reverse("rdc-detail", kwargs={"pk": self.rdc.pk}))
        self.rdc.refresh_from_db()
        self.assertEqual(self.rdc.observacoes, "Ajuste de teste")
