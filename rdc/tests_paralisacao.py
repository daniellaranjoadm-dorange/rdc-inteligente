from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import PerfilAcesso
from cadastros.models import AreaLocal, Disciplina, Projeto
from core.choices import TurnoChoices
from rdc.models import RDC, RDCParalisacao
from rdc.services.paralisacao_service import resumir_paralisacoes, texto_paralisacoes_excel

User = get_user_model()


class _Base(TestCase):
    def setUp(self):
        self.autor = User.objects.create_user("autor_rdc", password="x")
        self.projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="Transpetro")
        self.disciplina = Disciplina.objects.create(codigo="EST", nome="Estrutura")
        self.area = AreaLocal.objects.create(
            projeto=self.projeto, codigo="D02P", descricao="Bloco D02P", disciplina_padrao=self.disciplina
        )
        self.rdc = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=date(2026, 11, 23),
            turno=TurnoChoices.MANHA,
            criado_por=self.autor,
        )

    def paralisacao(self, **kw):
        dados = {"rdc": self.rdc, "motivo": "chuva", "inicio": time(9, 0), "fim": time(11, 30), "pessoas_afetadas": 4}
        dados.update(kw)
        return RDCParalisacao.objects.create(**dados)


class CalculoParalisacaoTests(_Base):
    def test_calcula_horas_e_hh_perdido(self):
        p = self.paralisacao()
        self.assertEqual(p.horas, Decimal("2.50"))
        self.assertEqual(p.hh_perdido, Decimal("10.00"))

    def test_parada_que_passa_da_meia_noite(self):
        p = self.paralisacao(inicio=time(22, 0), fim=time(1, 0), pessoas_afetadas=2)
        self.assertEqual(p.horas, Decimal("3.00"))
        self.assertEqual(p.hh_perdido, Decimal("6.00"))

    def test_responsabilidade_sugerida_pelo_motivo(self):
        self.assertEqual(self.paralisacao(motivo="chuva").responsabilidade, "clima")
        self.assertEqual(self.paralisacao(motivo="falta_liberacao").responsabilidade, "contratante")
        self.assertEqual(self.paralisacao(motivo="falta_material").responsabilidade, "contratada")

    def test_responsabilidade_informada_prevalece(self):
        p = self.paralisacao(motivo="chuva", responsabilidade="contratante")
        self.assertEqual(p.responsabilidade, "contratante")

    def test_resumo_agrupa_por_motivo_e_calcula_percentual(self):
        self.paralisacao(motivo="chuva", inicio=time(8, 0), fim=time(10, 0), pessoas_afetadas=5)  # 10 HH
        self.paralisacao(motivo="falta_material", inicio=time(13, 0), fim=time(14, 0), pessoas_afetadas=2)  # 2 HH
        resumo = resumir_paralisacoes(self.rdc.paralisacoes.all(), hh_trabalhado=Decimal("108"))
        self.assertEqual(resumo["qtd"], 2)
        self.assertEqual(resumo["hh_perdido"], Decimal("12.00"))
        self.assertEqual(resumo["por_motivo"][0]["codigo"], "chuva")
        self.assertEqual(resumo["percentual_perdido"], Decimal("10.0"))  # 12 / (108 + 12)

    def test_texto_do_excel(self):
        self.assertIn("nenhuma", texto_paralisacoes_excel(self.rdc))
        self.paralisacao()
        texto = texto_paralisacoes_excel(self.rdc)
        self.assertIn("HH perdido 10,00", texto)
        self.assertIn("Chuva", texto)


class TelasParalisacaoTests(_Base):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser("admin_pz", "a@example.com", "x")
        self.client.force_login(self.admin)

    def test_registra_paralisacao_pelo_formulario(self):
        url = reverse("rdc-paralisacao-create", kwargs={"pk": self.rdc.pk})
        self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(
            url, {"motivo": "vento", "inicio": "14:00", "fim": "15:30", "pessoas_afetadas": "6", "descricao": "Rajadas no dique"}
        )

        self.assertEqual(response.status_code, 302)
        p = RDCParalisacao.objects.get(rdc=self.rdc)
        self.assertEqual(p.hh_perdido, Decimal("9.00"))
        self.assertEqual(p.responsabilidade, "clima")
        self.assertEqual(p.criado_por, self.admin)

    def test_rejeita_inicio_igual_ao_fim(self):
        url = reverse("rdc-paralisacao-create", kwargs={"pk": self.rdc.pk})
        response = self.client.post(url, {"motivo": "chuva", "inicio": "10:00", "fim": "10:00", "pessoas_afetadas": "3"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RDCParalisacao.objects.exists())

    def test_detalhe_mostra_aba_e_hh_perdido(self):
        self.paralisacao()
        response = self.client.get(reverse("rdc-detail", kwargs={"pk": self.rdc.pk}))
        self.assertContains(response, 'id="paralisacoes"')
        self.assertContains(response, "HH perdido")
        self.assertContains(response, "10,00")  # formato pt-BR

    def test_edita_e_exclui(self):
        p = self.paralisacao()
        url = reverse("rdc-paralisacao-update", kwargs={"pk": self.rdc.pk, "pk2": p.pk})
        self.client.post(url, {"motivo": "chuva", "inicio": "09:00", "fim": "10:00", "pessoas_afetadas": "4"})
        p.refresh_from_db()
        self.assertEqual(p.hh_perdido, Decimal("4.00"))

        self.client.post(reverse("rdc-paralisacao-delete", kwargs={"pk": self.rdc.pk, "pk2": p.pk}))
        self.assertFalse(RDCParalisacao.objects.exists())

    def test_nao_edita_paralisacao_de_outro_rdc(self):
        outro = RDC.objects.create(
            projeto=self.projeto, area_local=self.area, disciplina=self.disciplina,
            data=date(2026, 11, 24), turno=TurnoChoices.MANHA, criado_por=self.autor,
        )
        p = self.paralisacao(rdc=outro)
        url = reverse("rdc-paralisacao-update", kwargs={"pk": self.rdc.pk, "pk2": p.pk})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_painel_mostra_bloco_de_paralisacoes(self):
        response = self.client.get(reverse("rdc-dashboard"))
        self.assertContains(response, "Paralisações e HH perdido")


class PermissaoParalisacaoTests(_Base):
    def setUp(self):
        super().setUp()
        self.supervisor = User.objects.create_user("sup_pz", password="x")
        PerfilAcesso.objects.create(user=self.supervisor, role="supervisor")
        self.client.force_login(self.supervisor)

    def test_supervisor_registra_em_rdc_aberto(self):
        url = reverse("rdc-paralisacao-create", kwargs={"pk": self.rdc.pk})
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_bloqueia_com_rdc_fechado(self):
        self.rdc.status = "fechado"
        self.rdc.save()
        url = reverse("rdc-paralisacao-create", kwargs={"pk": self.rdc.pk})
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_visitante_vai_para_login(self):
        self.client.logout()
        url = reverse("rdc-paralisacao-create", kwargs={"pk": self.rdc.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])


class PercentualSemHorasTests(_Base):
    def test_sem_hh_trabalhado_nao_mostra_percentual(self):
        self.paralisacao()
        resumo = resumir_paralisacoes(self.rdc.paralisacoes.all(), hh_trabalhado=Decimal("0"))
        self.assertIsNone(resumo["percentual_perdido"])
