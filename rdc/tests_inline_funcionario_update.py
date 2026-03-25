
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina, Funcao, Funcionario, Empresa
from core.choices import TurnoChoices
from rdc.models import RDC, RDCFuncionario


User = get_user_model()


class RDCInlineFuncionarioUpdateTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user(
            username="supervisor_inline_func",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.supervisor, role="supervisor")

        self.sem_permissao = User.objects.create_user(
            username="consulta_inline_func",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.sem_permissao, role="consulta")

        self.projeto = Projeto.objects.create(
            codigo="PRJIFU",
            nome="Projeto Inline Funcionario",
            cliente="Cliente Inline Funcionario",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISIFU",
            nome="Disciplina Inline Funcionario",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREAIFU",
            descricao="?rea Inline Funcionario",
            disciplina_padrao=self.disciplina,
        )

        self.funcao = Funcao.objects.create(
            codigo="FUNIFU",
            nome="Fun??o Inline Funcionario",
        )

        self.empresa = Empresa.objects.create(
            nome="Empresa Inline Funcionario",
        )

        self.funcionario_base = Funcionario.objects.create(
            matricula="MATIFU1",
            nome="Funcionario Base Inline",
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

        self.funcionario_aberto = RDCFuncionario.objects.create(
            rdc=self.rdc_aberto,
            funcionario=self.funcionario_base,
            funcao=self.funcao,
            matricula=self.funcionario_base.matricula,
            nome=self.funcionario_base.nome,
            presente_catraca=False,
            hora_normal=8,
            hora_extra=0,
        )

        self.funcionario_fechado = RDCFuncionario.objects.create(
            rdc=self.rdc_fechado,
            funcionario=self.funcionario_base,
            funcao=self.funcao,
            matricula="MATIFU2",
            nome="Funcionario Fechado",
            presente_catraca=False,
            hora_normal=8,
            hora_extra=0,
        )

    def test_supervisor_atualiza_presente_catraca_com_rdc_aberto(self):
        self.client.login(username="supervisor_inline_func", password="123")
        url = reverse("rdc-funcionario-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.funcionario_aberto.pk})
        response = self.client.post(url, data={"field": "presente_catraca", "value": "true"})
        self.assertEqual(response.status_code, 200)
        self.funcionario_aberto.refresh_from_db()
        self.assertTrue(self.funcionario_aberto.presente_catraca)

    def test_bloqueia_usuario_sem_permissao(self):
        self.client.login(username="consulta_inline_func", password="123")
        url = reverse("rdc-funcionario-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.funcionario_aberto.pk})
        response = self.client.post(url, data={"field": "presente_catraca", "value": "true"})
        self.assertEqual(response.status_code, 403)

    def test_bloqueia_rdc_fechado(self):
        self.client.login(username="supervisor_inline_func", password="123")
        url = reverse("rdc-funcionario-inline-update", kwargs={"pk": self.rdc_fechado.pk, "pk2": self.funcionario_fechado.pk})
        response = self.client.post(url, data={"field": "presente_catraca", "value": "true"})
        self.assertEqual(response.status_code, 403)

    def test_rejeita_campo_nao_permitido(self):
        self.client.login(username="supervisor_inline_func", password="123")
        url = reverse("rdc-funcionario-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.funcionario_aberto.pk})
        response = self.client.post(url, data={"field": "nome", "value": "Tentativa indevida"})
        self.assertEqual(response.status_code, 400)

