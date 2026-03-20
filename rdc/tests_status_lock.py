
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC, RDCAtividade


User = get_user_model()


class RDCStatusLockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supervisor_teste",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

        self.projeto = Projeto.objects.create(
            codigo="PRJLOCK",
            nome="Projeto Lock",
            cliente="Cliente Lock",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISCLOCK",
            nome="Disciplina Lock",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREALOCK",
            descricao="?rea Lock",
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
            codigo_atividade="ATV1",
            descr_atividade="Atividade teste",
            origem="manual",
        )

        self.client.login(username="supervisor_teste", password="123")

    def test_bloqueia_edicao_de_atividade_com_rdc_fechado(self):
        url = reverse("rdc-atividade-update", kwargs={"pk": self.rdc.pk, "pk2": self.atividade.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_bloqueia_nova_atividade_com_rdc_fechado(self):
        url = reverse("rdc-atividade-create", kwargs={"pk": self.rdc.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_bloqueia_novo_apontamento_com_rdc_fechado(self):
        url = reverse("rdc-apontamento-create", kwargs={"pk": self.rdc.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
