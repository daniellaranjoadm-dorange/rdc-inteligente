from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cadastros.models import AreaLocal, Disciplina, Projeto
from core.choices import TurnoChoices
from planejamento.models import AtividadeCronograma
from rdc.models import RDC, RDCAtividade
from rdc.services.avanco_service import fracao_prevista, montar_avanco, situacao

User = get_user_model()


class AvancoServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_av", "a@example.com", "x")
        self.projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="T")
        self.est = Disciplina.objects.create(codigo="EST-AV", nome="Estrutura")
        self.sol = Disciplina.objects.create(codigo="SOL-AV", nome="Solda")
        self.b1 = AreaLocal.objects.create(projeto=self.projeto, codigo="B01", descricao="Bloco 01", casco="Casco 1")
        self.b2 = AreaLocal.objects.create(projeto=self.projeto, codigo="B02", descricao="Bloco 02", casco="Casco 2")
        # 10 dias: 01 a 10/11
        self.a1 = self._crono(self.b1, self.est, "A1", Decimal("100"), "t", peso=Decimal("300"))
        self.a2 = self._crono(self.b1, self.sol, "A2", Decimal("50"), "m", peso=Decimal("100"))
        self.a3 = self._crono(self.b2, self.est, "A3", Decimal("10"), "t", peso=Decimal("0"))

    def _crono(self, area, disc, codigo, escopo, unidade, peso):
        return AtividadeCronograma.objects.create(
            projeto=self.projeto, area_local=area, disciplina=disc, codigo_atividade=codigo, descr_atividade=codigo,
            qtd_escopo=escopo, unidade=unidade, data_inicio=date(2026, 11, 1), data_fim=date(2026, 11, 10),
            status_planejado="Planejada", peso=peso,
        )

    def _lancar(self, area, disc, dia, codigo, qtd, vincular=None):
        rdc, _ = RDC.objects.get_or_create(projeto=self.projeto, area_local=area, disciplina=disc, data=dia,
                                           turno=TurnoChoices.MANHA, defaults={"criado_por": self.admin})
        RDCAtividade.objects.create(rdc=rdc, atividade_cronograma=vincular, codigo_atividade=codigo,
                                    descr_atividade=codigo, qtd_executada=qtd)

    def test_previsto_linear_e_situacao(self):
        self.assertEqual(fracao_prevista(date(2026, 11, 1), date(2026, 11, 10), date(2026, 10, 31)), 0.0)
        self.assertAlmostEqual(fracao_prevista(date(2026, 11, 1), date(2026, 11, 10), date(2026, 11, 5)), 0.5)
        self.assertEqual(fracao_prevista(date(2026, 11, 1), date(2026, 11, 10), date(2026, 11, 30)), 1.0)
        self.assertEqual(situacao(50, 30)[0], "atrasado")
        self.assertEqual(situacao(50, 52)[0], "no_prazo")
        self.assertEqual(situacao(50, 60)[0], "adiantado")
        self.assertEqual(situacao(80, 100)[0], "concluido")

    def test_realizado_soma_rdcs_ate_o_corte_por_vinculo_ou_codigo(self):
        self._lancar(self.b1, self.est, date(2026, 11, 2), "A1", Decimal("30"), vincular=self.a1)
        self._lancar(self.b1, self.est, date(2026, 11, 4), "A1", Decimal("20"))  # sem vinculo: casa pelo codigo
        self._lancar(self.b1, self.est, date(2026, 11, 8), "A1", Decimal("40"), vincular=self.a1)  # depois do corte
        dados = montar_avanco(date(2026, 11, 5), area_id=self.b1.pk)
        item = next(i for i in dados["detalhe"]["itens"] if i["id"] == self.a1.pk)
        self.assertEqual(item["executado"], Decimal("50"))
        self.assertEqual(item["realizado"], 50.0)
        self.assertEqual(item["previsto"], 50.0)

    def test_agregacao_ponderada_pelo_peso_e_peso_vazio_usa_media(self):
        self._lancar(self.b1, self.est, date(2026, 11, 2), "A1", Decimal("100"), vincular=self.a1)
        dados = montar_avanco(date(2026, 11, 30))
        # pesos: A1=300, A2=100, A3=media(300,100)=200 -> realizado = 300/600 = 50%
        self.assertTrue(dados["usa_peso"])
        self.assertEqual(dados["total"]["realizado"], 50.0)
        self.assertEqual(dados["total"]["previsto"], 100.0)
        bloco1 = next(l for l in dados["por_area"] if l["codigo"] == "B01")
        self.assertEqual(bloco1["realizado"], 75.0)
        self.assertEqual(dados["por_area"][0]["codigo"], "B02")  # pior desvio primeiro
        unidades = {u["unidade"]: u for u in dados["por_unidade"]}
        self.assertEqual(unidades["T"]["escopo"], Decimal("110"))
        self.assertEqual(unidades["T"]["executado"], Decimal("100"))

    def test_realizado_tem_teto_de_100_e_curva_s(self):
        self._lancar(self.b2, self.est, date(2026, 11, 3), "A3", Decimal("25"))
        dados = montar_avanco(date(2026, 11, 6), casco="Casco 2")
        self.assertEqual(dados["total"]["realizado"], 100.0)
        curva = dados["curva"]
        self.assertEqual(curva[0]["data"], date(2026, 11, 1))
        self.assertEqual(curva[-1]["previsto"], 100.0)
        self.assertIsNone(curva[-1]["realizado"])  # futuro nao tem realizado
        ponto_corte = next(p for p in curva if p["data"] == date(2026, 11, 6))
        self.assertEqual(ponto_corte["realizado"], 100.0)

    def test_sem_cronograma(self):
        self.assertFalse(montar_avanco(date(2026, 11, 5), projeto_id=999)["tem_dados"])


class AvancoTelasTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_avt", "a@example.com", "x")
        self.client.force_login(self.admin)
        self.projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="T")
        self.disc = Disciplina.objects.create(codigo="EST-T", nome="Estrutura")
        self.area = AreaLocal.objects.create(projeto=self.projeto, codigo="B01", descricao="Bloco 01", disciplina_padrao=self.disc)

    def test_tela_vazia_explica_o_que_fazer(self):
        r = self.client.get(reverse("rdc-avanco"))
        self.assertContains(r, "Ainda não há atividades planejadas")

    def test_cadastrar_atividade_e_ver_no_avanco(self):
        url = reverse("rdc-atividade-planejada-create") + f"?area={self.area.pk}"
        self.assertContains(self.client.get(url), "Nova atividade planejada")
        r = self.client.post(url, {
            "projeto": self.projeto.pk, "area_local": self.area.pk, "disciplina": self.disc.pk,
            "codigo_atividade": "MONT-B01", "descr_atividade": "Montagem do bloco", "qtd_escopo": "120",
            "unidade": "t", "data_inicio": "2026-11-01", "data_fim": "2026-11-30", "peso": "800",
        })
        ativ = AtividadeCronograma.objects.get(codigo_atividade="MONT-B01")
        self.assertRedirects(r, f"{reverse('rdc-avanco')}?projeto={self.projeto.pk}&area={self.area.pk}#detalhe",
                             fetch_redirect_response=False)
        tela = self.client.get(reverse("rdc-avanco") + f"?projeto={self.projeto.pk}&area={self.area.pk}&corte=2026-11-15")
        self.assertContains(tela, "Curva S")
        self.assertContains(tela, "Atividades do bloco B01")
        self.assertContains(tela, reverse("rdc-atividade-planejada-update", args=[ativ.pk]))

    def test_validacoes_do_formulario(self):
        outro = Projeto.objects.create(codigo="OUT", nome="Outro", cliente="T")
        r = self.client.post(reverse("rdc-atividade-planejada-create"), {
            "projeto": outro.pk, "area_local": self.area.pk, "disciplina": self.disc.pk,
            "codigo_atividade": "X", "descr_atividade": "X", "qtd_escopo": "0", "unidade": "t",
            "data_inicio": "2026-11-10", "data_fim": "2026-11-01", "peso": "0",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "outro projeto")
        self.assertContains(r, "antes do início")
        self.assertContains(r, "quantidade total")
        self.assertFalse(AtividadeCronograma.objects.exists())

    def test_data_de_corte_invalida_nao_quebra(self):
        self.assertEqual(self.client.get(reverse("rdc-avanco") + "?corte=2026-13-45&area=abc").status_code, 200)

    def test_operador_nao_cadastra(self):
        comum = User.objects.create_user("op_av", "o@example.com", "x")
        self.client.force_login(comum)
        self.assertIn(self.client.get(reverse("rdc-atividade-planejada-create")).status_code, (403,))
