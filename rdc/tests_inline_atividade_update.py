
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC, RDCAtividade


User = get_user_model()


class RDCInlineAtividadeUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supervisor_inline_atividade",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

        self.user_sem_permissao = User.objects.create_user(
            username="consulta_inline_atividade",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user_sem_permissao, role="consulta")

        self.projeto = Projeto.objects.create(
            codigo="PRJINLA",
            nome="Projeto Inline Atividade",
            cliente="Cliente Inline Atividade",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISINLA",
            nome="Disciplina Inline Atividade",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREAINLA",
            descricao="?rea Inline Atividade",
            disciplina_padrao=self.disciplina,
        )

        self.rdc_aberto = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date(),
            turno=TurnoChoices.MANHA,
            status="rascunho",
            criado_por=self.user,
        )

        self.rdc_fechado = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date(),
            turno=TurnoChoices.TARDE,
            status="fechado",
            criado_por=self.user,
        )

        self.atividade_aberta = RDCAtividade.objects.create(
            rdc=self.rdc_aberto,
            codigo_atividade="ATVINLA1",
            descr_atividade="Atividade aberta",
            origem="manual",
            qtd_executada="0.00",
        )

        self.atividade_fechada = RDCAtividade.objects.create(
            rdc=self.rdc_fechado,
            codigo_atividade="ATVINLA2",
            descr_atividade="Atividade fechada",
            origem="manual",
            qtd_executada="0.00",
        )

    def test_supervisor_atualiza_qtd_executada_com_rdc_aberto(self):
        self.client.login(username="supervisor_inline_atividade", password="123")
        url = reverse("rdc-atividade-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.atividade_aberta.pk})

        response = self.client.post(
            url,
            data={"field": "qtd_executada", "value": "12.50"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.atividade_aberta.refresh_from_db()
        self.assertEqual(str(self.atividade_aberta.qtd_executada), "12.50")
        self.assertJSONEqual(
            response.content,
            {"ok": True, "display": "12.50", "field": "qtd_executada", "value": "12.50"},
        )

    def test_bloqueia_usuario_sem_permissao(self):
        self.client.login(username="consulta_inline_atividade", password="123")
        url = reverse("rdc-atividade-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.atividade_aberta.pk})

        response = self.client.post(
            url,
            data={"field": "qtd_executada", "value": "8.00"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 403)

    def test_bloqueia_rdc_fechado(self):
        self.client.login(username="supervisor_inline_atividade", password="123")
        url = reverse("rdc-atividade-inline-update", kwargs={"pk": self.rdc_fechado.pk, "pk2": self.atividade_fechada.pk})

        response = self.client.post(
            url,
            data={"field": "qtd_executada", "value": "3.00"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 403)
        self.atividade_fechada.refresh_from_db()
        self.assertEqual(str(self.atividade_fechada.qtd_executada), "0.00")

    def test_rejeita_campo_nao_permitido(self):
        self.client.login(username="supervisor_inline_atividade", password="123")
        url = reverse("rdc-atividade-inline-update", kwargs={"pk": self.rdc_aberto.pk, "pk2": self.atividade_aberta.pk})

        response = self.client.post(
            url,
            data={"field": "descr_atividade", "value": "Hack"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        self.atividade_aberta.refresh_from_db()
        self.assertEqual(self.atividade_aberta.descr_atividade, "Atividade aberta")
