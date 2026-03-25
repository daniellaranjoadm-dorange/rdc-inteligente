
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC, RDCAtividade, RDCFuncionario, RDCApontamento


User = get_user_model()


class RDCDeleteLockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supervisor_delete",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

        self.projeto = Projeto.objects.create(
            codigo="PRJDEL",
            nome="Projeto Delete",
            cliente="Cliente Delete",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISDEL",
            nome="Disciplina Delete",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREADEL",
            descricao="?rea Delete",
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
            codigo_atividade="ATVDEL1",
            descr_atividade="Atividade delete",
            origem="manual",
        )

        self.client.login(username="supervisor_delete", password="123")

    def test_bloqueia_get_delete_atividade_com_rdc_fechado(self):
        url = reverse("rdc-atividade-delete", kwargs={"pk": self.rdc.pk, "pk2": self.atividade.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_bloqueia_post_delete_atividade_com_rdc_fechado(self):
        url = reverse("rdc-atividade-delete", kwargs={"pk": self.rdc.pk, "pk2": self.atividade.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(RDCAtividade.objects.filter(pk=self.atividade.pk).exists())

