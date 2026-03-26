
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC, RDCAtividade


User = get_user_model()


class RDCOpenAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supervisor_open",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

        self.projeto = Projeto.objects.create(
            codigo="PRJOPEN",
            nome="Projeto Open",
            cliente="Cliente Open",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISOPEN",
            nome="Disciplina Open",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREAOPEN",
            descricao="?rea Open",
            disciplina_padrao=self.disciplina,
        )

        self.rdc = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date(),
            turno=TurnoChoices.MANHA,
            status="aberto",
            criado_por=self.user,
        )

        self.atividade = RDCAtividade.objects.create(
            rdc=self.rdc,
            codigo_atividade="ATVOPEN1",
            descr_atividade="Atividade open",
            origem="manual",
        )

        self.client.login(username="supervisor_open", password="123")

    def test_permite_get_edicao_de_atividade_com_rdc_aberto(self):
        url = reverse(
            "rdc-atividade-update",
            kwargs={"pk": self.rdc.pk, "pk2": self.atividade.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_permite_get_nova_atividade_com_rdc_aberto(self):
        url = reverse("rdc-atividade-create", kwargs={"pk": self.rdc.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_permite_get_novo_apontamento_com_rdc_aberto(self):
        url = reverse("rdc-apontamento-create", kwargs={"pk": self.rdc.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


