
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina, Funcao, Funcionario, Empresa
from core.choices import TurnoChoices
from rdc.models import RDC, RDCAtividade, RDCFuncionario, RDCApontamento


User = get_user_model()


class RDCInlineApontamentoUpdateTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user(
            username="supervisor_inline_ap",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.supervisor, role="supervisor")

        self.sem_permissao = User.objects.create_user(
            username="consulta_inline_ap",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.sem_permissao, role="consulta")

        self.projeto = Projeto.objects.create(
            codigo="PRJIAP",
            nome="Projeto Inline Apontamento",
            cliente="Cliente Inline Apontamento",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISIAP",
            nome="Disciplina Inline Apontamento",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREAIAP",
            descricao="?rea Inline Apontamento",
            disciplina_padrao=self.disciplina,
        )

        self.funcao = Funcao.objects.create(
            codigo="FUNIAP",
            nome="Fun??o Inline Apontamento",
        )

        self.empresa = Empresa.objects.create(
            nome="Empresa Inline Apontamento",
        )

        self.funcionario_base = Funcionario.objects.create(
            matricula="MATIAP1",
            nome="Funcionario Base Inline Apontamento",
            cpf="12345678901",
            rg="1234567",
            funcao=self.funcao,
            empresa=self.empresa,
        )

        self.rdc_aberto = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date(),
            turno=TurnoChoices.MANHA,
            status="rascunho",
            criado_por=self.supervisor,
        )

        self.rdc_fechado = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date() + timezone.timedelta(days=1),
            turno=TurnoChoices.MANHA,
            status="fechado",
            criado_por=self.supervisor,
        )

        self.atividade_aberta = RDCAtividade.objects.create(
            rdc=self.rdc_aberto,
            codigo_atividade="ATVIAP1",
            descr_atividade="Atividade Inline Apontamento Aberto",
            origem="manual",
        )

        self.atividade_fechada = RDCAtividade.objects.create(
            rdc=self.rdc_fechado,
            codigo_atividade="ATVIAP2",
            descr_atividade="Atividade Inline Apontamento Fechado",
            origem="manual",
        )

        self.funcionario_aberto = RDCFuncionario.objects.create(
            rdc=self.rdc_aberto,
            funcionario=self.funcionario_base,
            funcao=self.funcao,
            matricula=self.funcionario_base.matricula,
            nome=self.funcionario_base.nome,
            presente_catraca=True,
            hora_normal=Decimal("8.00"),
            hora_extra=Decimal("0.00"),
        )

        self.funcionario_fechado = RDCFuncionario.objects.create(
            rdc=self.rdc_fechado,
            funcionario=self.funcionario_base,
            funcao=self.funcao,
            matricula="MATIAP2",
            nome="Funcionario Fechado Apontamento",
            presente_catraca=True,
            hora_normal=Decimal("8.00"),
            hora_extra=Decimal("0.00"),
        )

        self.apontamento_aberto = RDCApontamento.objects.create(
            rdc=self.rdc_aberto,
            rdc_funcionario=self.funcionario_aberto,
            rdc_atividade=self.atividade_aberta,
            horas=Decimal("1.00"),
            observacao="Inicial",
        )

        self.apontamento_fechado = RDCApontamento.objects.create(
            rdc=self.rdc_fechado,
            rdc_funcionario=self.funcionario_fechado,
            rdc_atividade=self.atividade_fechada,
            horas=Decimal("1.00"),
            observacao="Fechado",
        )

    def test_supervisor_atualiza_horas_com_rdc_aberto(self):
        self.client.login(username="supervisor_inline_ap", password="123")
        url = reverse("rdc-apontamento-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.apontamento_aberto.pk})
        response = self.client.post(url, data={"field": "horas", "value": "2.50"})
        self.assertEqual(response.status_code, 200)
        self.apontamento_aberto.refresh_from_db()
        self.assertEqual(self.apontamento_aberto.horas, Decimal("2.50"))

    def test_supervisor_atualiza_observacao_com_rdc_aberto(self):
        self.client.login(username="supervisor_inline_ap", password="123")
        url = reverse("rdc-apontamento-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.apontamento_aberto.pk})
        response = self.client.post(url, data={"field": "observacao", "value": "Observa??o alterada"})
        self.assertEqual(response.status_code, 200)
        self.apontamento_aberto.refresh_from_db()
        self.assertEqual(self.apontamento_aberto.observacao, "Observa??o alterada")

    def test_bloqueia_usuario_sem_permissao(self):
        self.client.login(username="consulta_inline_ap", password="123")
        url = reverse("rdc-apontamento-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.apontamento_aberto.pk})
        response = self.client.post(url, data={"field": "horas", "value": "3.00"})
        self.assertEqual(response.status_code, 403)

    def test_bloqueia_rdc_fechado(self):
        self.client.login(username="supervisor_inline_ap", password="123")
        url = reverse("rdc-apontamento-inline-update", kwargs={"pk": self.rdc_fechado.pk, "pk2": self.apontamento_fechado.pk})
        response = self.client.post(url, data={"field": "horas", "value": "4.00"})
        self.assertEqual(response.status_code, 403)

    def test_rejeita_campo_nao_permitido(self):
        self.client.login(username="supervisor_inline_ap", password="123")
        url = reverse("rdc-apontamento-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.apontamento_aberto.pk})
        response = self.client.post(url, data={"field": "rdc_atividade", "value": "999"})
        self.assertEqual(response.status_code, 400)

