from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC, RDCValidacao


User = get_user_model()


class RDCInlineValidacaoUpdateTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user(
            username="supervisor_inline_val",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.supervisor, role="supervisor")

        self.sem_permissao = User.objects.create_user(
            username="consulta_inline_val",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.sem_permissao, role="consulta")

        self.projeto = Projeto.objects.create(
            codigo="PRJIVL",
            nome="Projeto Inline Validacao",
            cliente="Cliente Inline Validacao",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISIVL",
            nome="Disciplina Inline Validacao",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREAIVL",
            descricao="Area Inline Validacao",
            disciplina_padrao=self.disciplina,
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

        self.validacao_aberta = RDCValidacao.objects.create(
            rdc=self.rdc_aberto,
            tipo="teste_manual",
            status="alerta",
            mensagem="Mensagem inicial",
            referencia="REF-INI",
        )

        self.validacao_fechada = RDCValidacao.objects.create(
            rdc=self.rdc_fechado,
            tipo="teste_manual",
            status="alerta",
            mensagem="Mensagem fechada",
            referencia="REF-FECH",
        )

    def test_supervisor_atualiza_status_com_rdc_aberto(self):
        self.client.login(username="supervisor_inline_val", password="123")
        url = reverse("rdc-validacao-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.validacao_aberta.pk})
        response = self.client.post(url, data={"field": "status", "value": "bloqueio"})
        self.assertEqual(response.status_code, 200)
        self.validacao_aberta.refresh_from_db()
        self.assertEqual(self.validacao_aberta.status, "bloqueio")

    def test_supervisor_atualiza_mensagem_com_rdc_aberto(self):
        self.client.login(username="supervisor_inline_val", password="123")
        url = reverse("rdc-validacao-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.validacao_aberta.pk})
        response = self.client.post(url, data={"field": "mensagem", "value": "Mensagem alterada"})
        self.assertEqual(response.status_code, 200)
        self.validacao_aberta.refresh_from_db()
        self.assertEqual(self.validacao_aberta.mensagem, "Mensagem alterada")

    def test_bloqueia_usuario_sem_permissao(self):
        self.client.login(username="consulta_inline_val", password="123")
        url = reverse("rdc-validacao-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.validacao_aberta.pk})
        response = self.client.post(url, data={"field": "status", "value": "info"})
        self.assertEqual(response.status_code, 403)

    def test_bloqueia_rdc_fechado(self):
        self.client.login(username="supervisor_inline_val", password="123")
        url = reverse("rdc-validacao-inline-update", kwargs={"pk": self.rdc_fechado.pk, "pk2": self.validacao_fechada.pk})
        response = self.client.post(url, data={"field": "status", "value": "bloqueio"})
        self.assertEqual(response.status_code, 403)

    def test_rejeita_campo_nao_permitido(self):
        self.client.login(username="supervisor_inline_val", password="123")
        url = reverse("rdc-validacao-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.validacao_aberta.pk})
        response = self.client.post(url, data={"field": "tipo", "value": "tentativa"})
        self.assertEqual(response.status_code, 400)
