from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from cadastros.models import AreaLocal, Empresa, Funcao, Funcionario, Projeto
from soldagem.models import EPS, InspecaoEND, JuntaSolda, ResultadoEND, Soldador, StatusJunta
from soldagem.services import alertas_solda, montar_painel_solda, registrar_execucao, registrar_resultado_end

User = get_user_model()
DIA = date(2026, 11, 10)


class Base(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_sd", "a@example.com", "x")
        self.projeto = Projeto.objects.create(codigo="P1", nome="PSV", cliente="T")
        self.bloco = AreaLocal.objects.create(projeto=self.projeto, codigo="B1", descricao="Bloco 1")
        emp = Empresa.objects.create(nome="E")
        fun = Funcao.objects.create(codigo="SOLD", nome="Soldador")
        self.eps = EPS.objects.create(codigo="EPS-1", processo="FCAW", material="AH36")
        self.s1 = self._soldador("S-1", emp, fun, "FCAW, SMAW")
        self.s2 = self._soldador("S-2", emp, fun, "SMAW")
        self.junta = JuntaSolda.objects.create(projeto=self.projeto, area_local=self.bloco, codigo="B1-C01",
                                               comprimento_m=Decimal("10"), eps=self.eps, metodo_end="UT")

    def _soldador(self, sinete, emp, fun, processos, validade=date(2027, 1, 1)):
        f = Funcionario.objects.create(matricula=sinete, nome=f"Nome {sinete}", funcao=fun, empresa=emp)
        return Soldador.objects.create(funcionario=f, sinete=sinete, processos=processos, validade_qualificacao=validade)


class RegrasTests(Base):
    def test_fluxo_completo_solda_end_reprovado_reparo_aprovado(self):
        registrar_execucao(self.junta, soldador=self.s1, data=DIA, metros=6)
        self.junta.refresh_from_db()
        self.assertEqual(self.junta.status, StatusJunta.EM_EXECUCAO)
        registrar_execucao(self.junta, soldador=self.s1, data=DIA + timedelta(days=1), metros=4)
        self.junta.refresh_from_db()
        self.assertEqual(self.junta.status, StatusJunta.AGUARDANDO_END)
        end = self.junta.inspecoes.get()
        self.assertEqual((end.metodo, end.ciclo, end.metros_inspecionados), ("UT", 1, Decimal("10")))
        self.assertEqual(list(end.soldadores.all()), [self.s1])

        with self.assertRaises(ValidationError):  # nao solda junta aguardando END
            registrar_execucao(self.junta, soldador=self.s1, data=DIA, metros=1)

        registrar_resultado_end(end, resultado=ResultadoEND.REPROVADO, data=DIA + timedelta(days=2),
                                metros_reprovados=Decimal("1.5"), defeito="porosidade")
        self.junta.refresh_from_db()
        self.assertEqual(self.junta.status, StatusJunta.REPROVADA)
        with self.assertRaises(ValidationError):  # reprovada so aceita reparo
            registrar_execucao(self.junta, soldador=self.s1, data=DIA, metros=1)

        registrar_execucao(self.junta, soldador=self.s1, data=DIA + timedelta(days=3), metros=Decimal("1.5"), reparo=True)
        self.junta.refresh_from_db()
        reteste = self.junta.inspecoes.get(ciclo=2)
        self.assertEqual(self.junta.status, StatusJunta.AGUARDANDO_END)
        registrar_resultado_end(reteste, resultado=ResultadoEND.APROVADO, data=DIA + timedelta(days=4))
        self.junta.refresh_from_db()
        self.assertEqual(self.junta.status, StatusJunta.APROVADA)
        self.assertEqual(self.junta.metros_soldados, Decimal("10"))  # reparo nao conta como metro novo

        painel = montar_painel_solda()
        self.assertEqual(painel["totais"]["taxa_reparo"], round(1.5 / 11.5 * 100, 1))
        linha = next(l for l in painel["por_soldador"] if l["soldador"] == self.s1)
        self.assertTrue(linha["acima_limite"])

    def test_qualificacao_vencida_e_processo_fora_da_eps_bloqueiam(self):
        self.s1.validade_qualificacao = DIA - timedelta(days=1)
        self.s1.save()
        with self.assertRaisesMessage(ValidationError, "venceu"):
            registrar_execucao(self.junta, soldador=self.s1, data=DIA, metros=2)
        with self.assertRaisesMessage(ValidationError, "processo FCAW"):
            registrar_execucao(self.junta, soldador=self.s2, data=DIA, metros=2)

    def test_nao_passa_do_comprimento_e_junta_sem_end_conclui(self):
        with self.assertRaises(ValidationError):
            registrar_execucao(self.junta, soldador=self.s1, data=DIA, metros=11)
        filete = JuntaSolda.objects.create(projeto=self.projeto, area_local=self.bloco, codigo="B1-F01",
                                           comprimento_m=Decimal("3"), tipo="filete")
        registrar_execucao(filete, soldador=self.s2, data=DIA, metros=3)
        filete.refresh_from_db()
        self.assertEqual(filete.status, StatusJunta.CONCLUIDA)
        self.assertFalse(InspecaoEND.objects.filter(junta=filete).exists())

    def test_resultado_reprovado_exige_metros_e_defeito(self):
        registrar_execucao(self.junta, soldador=self.s1, data=DIA, metros=10)
        end = self.junta.inspecoes.get()
        with self.assertRaises(ValidationError):
            registrar_resultado_end(end, resultado=ResultadoEND.REPROVADO, data=DIA, metros_reprovados=0, defeito="trinca")
        with self.assertRaises(ValidationError):
            registrar_resultado_end(end, resultado=ResultadoEND.REPROVADO, data=DIA, metros_reprovados=11, defeito="trinca")
        with self.assertRaises(ValidationError):
            registrar_resultado_end(end, resultado=ResultadoEND.REPROVADO, data=DIA, metros_reprovados=1)

    def test_alertas_de_end_atrasado_e_qualificacao(self):
        registrar_execucao(self.junta, soldador=self.s1, data=DIA, metros=10)
        self.s2.validade_qualificacao = DIA + timedelta(days=5)
        self.s2.save()
        tipos = [a["tipo"] for a in alertas_solda(DIA + timedelta(days=4))]
        self.assertIn("end_atrasado", tipos)
        self.assertIn("qualificacao_vencendo", tipos)
        self.assertIn("qualificacao_vencida", [a["tipo"] for a in alertas_solda(DIA + timedelta(days=6))])


class TelasTests(Base):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_paginas_abrem(self):
        for nome in ("solda-painel", "solda-juntas", "solda-soldadores", "solda-eps", "solda-junta-create",
                     "solda-soldador-create", "solda-eps-create"):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)
        self.assertContains(self.client.get(reverse("solda-junta-detail", args=[self.junta.pk])), "Lançar solda")

    def test_lancar_solda_e_resultado_pela_tela(self):
        url = reverse("solda-registrar", args=[self.junta.pk])
        r = self.client.post(url, {"soldador": self.s1.pk, "data": "2026-11-10", "metros": "10", "passe": "completo"})
        self.assertRedirects(r, reverse("solda-junta-detail", args=[self.junta.pk]), fetch_redirect_response=False)
        self.junta.refresh_from_db()
        self.assertEqual(self.junta.status, StatusJunta.AGUARDANDO_END)
        end = self.junta.inspecoes.get()
        self.client.post(reverse("solda-end-resultado", args=[end.pk]),
                         {"resultado": "aprovado", "data": "2026-11-11", "inspetor": "N2"})
        self.junta.refresh_from_db()
        self.assertEqual(self.junta.status, StatusJunta.APROVADA)
        painel = self.client.get(reverse("solda-painel"))
        self.assertContains(painel, "Taxa de reparo")

    def test_erro_de_regra_vira_mensagem_e_nao_grava(self):
        self.s1.validade_qualificacao = date(2026, 1, 1)
        self.s1.save()
        r = self.client.post(reverse("solda-registrar", args=[self.junta.pk]),
                             {"soldador": self.s1.pk, "data": "2026-11-10", "metros": "5", "passe": "completo"}, follow=True)
        self.assertContains(r, "venceu")
        self.assertFalse(self.junta.execucoes.exists())

    def test_operador_nao_lanca(self):
        comum = User.objects.create_user("op_sd", "o@example.com", "x")
        self.client.force_login(comum)
        r = self.client.post(reverse("solda-registrar", args=[self.junta.pk]),
                             {"soldador": self.s1.pk, "data": "2026-11-10", "metros": "5", "passe": "completo"})
        self.assertEqual(r.status_code, 403)
