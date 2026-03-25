
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC, RDCAtividade


User = get_user_model()


class RDCRoleForbiddenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="usuario_sem_permissao",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="viewer")

        self.projeto = Projeto.objects.create(
            codigo="PRJROLE",
            nome="Projeto Role",
            cliente="Cliente Role",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISROLE",
            nome="Disciplina Role",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREAROLE",
            descricao="?rea Role",
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
            codigo_atividade="ATVROLE1",
            descr_atividade="Atividade role",
            origem="manual",
        )

        self.client.login(username="usuario_sem_permissao", password="123")

    def test_bloqueia_get_edicao_de_atividade_para_usuario_sem_permissao(self):
        url = reverse(
            "rdc-atividade-update",
            kwargs={"pk": self.rdc.pk, "pk2": self.atividade.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_bloqueia_get_nova_atividade_para_usuario_sem_permissao(self):
        url = reverse("rdc-atividade-create", kwargs={"pk": self.rdc.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_bloqueia_get_novo_apontamento_para_usuario_sem_permissao(self):
        url = reverse("rdc-apontamento-create", kwargs={"pk": self.rdc.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

