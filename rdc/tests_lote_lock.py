
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina, Funcao, Funcionario, Empresa
from core.choices import TurnoChoices
from rdc.models import RDC, RDCAtividade, RDCFuncionario, RDCValidacao, RDCApontamento


User = get_user_model()


class RDCLoteLockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supervisor_lote",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

        self.projeto = Projeto.objects.create(
            codigo="PRJLOT",
            nome="Projeto Lote",
            cliente="Cliente Lote",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISLOT",
            nome="Disciplina Lote",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREALOT",
            descricao="?rea Lote",
            disciplina_padrao=self.disciplina,
        )

        self.rdc = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date(),
            turno=TurnoChoices.MANHA,
            status="fechado",
            criado_por=self.user,
        )

        self.atividade = RDCAtividade.objects.create(
            rdc=self.rdc,
            codigo_atividade="ATVLOT1",
            descr_atividade="Atividade lote",
            origem="manual",
        )

        self.funcao = Funcao.objects.create(
            codigo="FUNLOT",
            nome="Fun??o Lote",
        )

        self.empresa = Empresa.objects.create(
            nome="Empresa Lote",
        )

        self.funcionario_base = Funcionario.objects.create(
            matricula="MATLOT1",
            nome="Funcion?rio Lote",
            cpf="00000000000",
            rg="0000000",
            funcao=self.funcao,
            empresa=self.empresa,
        )

        self.funcionario = RDCFuncionario.objects.create(
            rdc=self.rdc,
            funcionario=self.funcionario_base,
            funcao=self.funcao,
            matricula=self.funcionario_base.matricula,
            nome=self.funcionario_base.nome,
        )

        self.validacao = RDCValidacao.objects.create(
            rdc=self.rdc,
            tipo="teste_manual",
            status="alerta",
            mensagem="Valida??o lote",
            referencia="MANUAL:1",
        )

        self.apontamento = RDCApontamento.objects.create(
            rdc=self.rdc,
            rdc_funcionario=self.funcionario,
            rdc_atividade=self.atividade,
            horas="1.00",
        )

        self.client.login(username="supervisor_lote", password="123")

    def test_bloqueia_lote_atividade_com_rdc_fechado(self):
        url = reverse("rdc-atividade-lote", kwargs={"pk": self.rdc.pk})
        response = self.client.post(url, data={"ids": [self.atividade.pk], "acao": "excluir"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(RDCAtividade.objects.filter(pk=self.atividade.pk).exists())

    def test_bloqueia_lote_funcionario_com_rdc_fechado(self):
        url = reverse("rdc-funcionario-lote", kwargs={"pk": self.rdc.pk})
        response = self.client.post(url, data={"ids": [self.funcionario.pk], "acao": "excluir"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(RDCFuncionario.objects.filter(pk=self.funcionario.pk).exists())

    def test_bloqueia_lote_apontamento_com_rdc_fechado(self):
        url = reverse("rdc-apontamento-lote", kwargs={"pk": self.rdc.pk})
        response = self.client.post(url, data={"ids": [self.apontamento.pk], "acao": "excluir"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(RDCApontamento.objects.filter(pk=self.apontamento.pk).exists())

    def test_bloqueia_lote_validacao_com_rdc_fechado(self):
        url = reverse("rdc-validacao-lote", kwargs={"pk": self.rdc.pk})
        response = self.client.post(url, data={"ids": [self.validacao.pk], "acao": "excluir"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(RDCValidacao.objects.filter(pk=self.validacao.pk).exists())
