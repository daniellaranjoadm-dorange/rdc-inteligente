
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC


User = get_user_model()


class RDCRevalidarLockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supervisor_revalidar",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

        self.user_sem_permissao = User.objects.create_user(
            username="viewer_revalidar",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user_sem_permissao, role="viewer")

        self.projeto = Projeto.objects.create(
            codigo="PRJREV",
            nome="Projeto Revalidar",
            cliente="Cliente Revalidar",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISREV",
            nome="Disciplina Revalidar",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREAREV",
            descricao="?rea Revalidar",
            disciplina_padrao=self.disciplina,
        )

        self.rdc_fechado = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date(),
            turno=TurnoChoices.MANHA,
            status="fechado",
            criado_por=self.user,
        )

        self.rdc_aberto = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date() + timezone.timedelta(days=1),
            turno=TurnoChoices.MANHA,
            status="aberto",
            criado_por=self.user,
        )

    def test_bloqueia_revalidar_rdc_fechado(self):
        self.client.login(username="supervisor_revalidar", password="123")
        url = reverse("rdc-revalidar", kwargs={"pk": self.rdc_fechado.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_bloqueia_revalidar_para_usuario_sem_permissao(self):
        self.client.login(username="viewer_revalidar", password="123")
        url = reverse("rdc-revalidar", kwargs={"pk": self.rdc_aberto.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)


