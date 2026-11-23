from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cadastros.models import AreaLocal, Disciplina, Funcao, Funcionario, Empresa, Projeto
from core.choices import TurnoChoices
from rdc.models import RDC, RDCFuncionario, RDCParalisacao
from rdc.services.hh_service import montar_painel_hh, normalizar_periodo

User = get_user_model()


class PainelHHTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin_hh", "a@example.com", "x")
        self.hmx = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="Transpetro")
        self.g7k = Projeto.objects.create(codigo="G7K", nome="Gaseiros 7k", cliente="Transpetro")
        self.est = Disciplina.objects.create(codigo="EST-T", nome="Estrutura T")
        self.tub = Disciplina.objects.create(codigo="TUB-T", nome="Tubulação T")
        self.bloco = AreaLocal.objects.create(
            projeto=self.hmx, codigo="D02P", descricao="Bloco D02P", tipo="bloco", casco="Handymax 01", etapa="montagem_bloco"
        )
        self.dique = AreaLocal.objects.create(projeto=self.g7k, codigo="DQ1", descricao="Dique 1", tipo="dique")
        self.empresa = Empresa.objects.create(nome="Empresa T")
        self.funcao = Funcao.objects.create(codigo="SOLD", nome="Soldador")
        self.dia = date(2026, 11, 18)

        self.rdc1 = self._rdc(self.hmx, self.bloco, self.est, self.dia)
        self.rdc2 = self._rdc(self.g7k, self.dique, self.tub, self.dia + timedelta(days=1))
        self._func(self.rdc1, "001", Decimal("8"), Decimal("2"))   # 10 HH
        self._func(self.rdc1, "002", Decimal("8"), Decimal("0"))   # 8 HH
        self._func(self.rdc2, "003", Decimal("8"), Decimal("0"))   # 8 HH
        RDCParalisacao.objects.create(rdc=self.rdc1, motivo="chuva", inicio=time(9), fim=time(10), pessoas_afetadas=2)  # 2 HH

    def _rdc(self, projeto, area, disciplina, dia):
        return RDC.objects.create(projeto=projeto, area_local=area, disciplina=disciplina, data=dia,
                                  turno=TurnoChoices.MANHA, criado_por=self.user)

    def _func(self, rdc, matricula, hn, he):
        f = Funcionario.objects.create(matricula=matricula, nome=f"Func {matricula}", funcao=self.funcao, empresa=self.empresa)
        return RDCFuncionario.objects.create(rdc=rdc, funcionario=f, funcao=self.funcao, matricula=matricula,
                                             nome=f.nome, hora_normal=hn, hora_extra=he)

    def test_totais_do_periodo(self):
        painel = montar_painel_hh(self.dia, self.dia + timedelta(days=1))
        self.assertEqual(painel["totais"]["hh_trabalhado"], Decimal("26.00"))
        self.assertEqual(painel["totais"]["hh_perdido"], Decimal("2.00"))
        self.assertEqual(painel["totais"]["percentual_perdido"], Decimal("7.1"))  # 2 / 28
        self.assertEqual(painel["totais"]["rdcs"], 2)

    def test_agrupa_por_bloco_disciplina_casco_e_etapa(self):
        painel = montar_painel_hh(self.dia, self.dia + timedelta(days=1))
        bloco = next(l for l in painel["por_area"] if l["rotulo"] == "Bloco D02P")
        self.assertEqual((bloco["hh_trabalhado"], bloco["hh_perdido"], bloco["efetivo"]), (Decimal("18.00"), Decimal("2.00"), 2))
        self.assertIn("Bloco", bloco["detalhe"])

        self.assertEqual({l["rotulo"] for l in painel["por_disciplina"]}, {"Estrutura T", "Tubulação T"})
        self.assertEqual({l["rotulo"] for l in painel["por_casco"]}, {"Handymax 01", "Casco não informado"})
        self.assertEqual({l["rotulo"] for l in painel["por_etapa"]}, {"Montagem de bloco", "Etapa não informada"})

    def test_filtra_por_projeto(self):
        painel = montar_painel_hh(self.dia, self.dia + timedelta(days=1), projeto_id=self.g7k.pk)
        self.assertEqual(painel["totais"]["hh_trabalhado"], Decimal("8.00"))
        self.assertEqual(painel["totais"]["hh_perdido"], Decimal("0.00"))
        self.assertEqual(painel["totais"]["percentual_perdido"], Decimal("0.0"))  # trabalhou e nao perdeu: 0%

    def test_evolucao_diaria_e_semanal(self):
        diario = montar_painel_hh(self.dia, self.dia + timedelta(days=6))["evolucao"]
        self.assertFalse(diario["por_semana"])
        self.assertEqual(len(diario["pontos"]), 7)
        self.assertEqual(diario["pontos"][0]["hh_trabalhado"], Decimal("18.00"))

        semanal = montar_painel_hh(self.dia - timedelta(days=90), self.dia + timedelta(days=1))["evolucao"]
        self.assertTrue(semanal["por_semana"])
        self.assertEqual(sum(p["hh_trabalhado"] for p in semanal["pontos"]), Decimal("26.00"))

    def test_periodo_invertido_e_limitado(self):
        ini, fim = normalizar_periodo(date(2026, 12, 31), date(2026, 1, 1))
        self.assertLessEqual(ini, fim)
        ini, fim = normalizar_periodo(date(2020, 1, 1), date(2026, 1, 1))
        self.assertEqual((fim - ini).days, 365)

    def test_pagina_abre_com_filtros(self):
        self.client.force_login(self.user)
        url = reverse("rdc-painel-hh")
        r = self.client.get(url, {"inicio": "2026-11-18", "fim": "2026-11-19", "projeto": str(self.hmx.pk)})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Painel de HH")
        self.assertContains(r, "Bloco D02P")
        self.assertNotContains(r, "Dique 1")

    def test_parametros_invalidos_nao_quebram(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("rdc-painel-hh"), {"inicio": "xx", "fim": "2026-13-45", "projeto": "999999"})
        self.assertEqual(r.status_code, 200)

    def test_exige_login(self):
        r = self.client.get(reverse("rdc-painel-hh"))
        self.assertEqual(r.status_code, 302)
