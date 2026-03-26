
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC, RDCAtividade


User = get_user_model()


class RDCStatusLockPostTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supervisor_post",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

        self.projeto = Projeto.objects.create(
            codigo="PRJPOST",
            nome="Projeto Post",
            cliente="Cliente Post",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISPOST",
            nome="Disciplina Post",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREAPOST",
            descricao="?rea Post",
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
            codigo_atividade="ATVPOST1",
            descr_atividade="Atividade original",
            origem="manual",
        )

        self.client.login(username="supervisor_post", password="123")

    def test_bloqueia_post_edicao_de_atividade_com_rdc_fechado(self):
        url = reverse(
            "rdc-atividade-update",
            kwargs={"pk": self.rdc.pk, "pk2": self.atividade.pk},
        )
        response = self.client.post(
            url,
            data={
                "codigo_atividade": "ATVPOST1",
                "descr_atividade": "Atividade alterada",
                "origem": "manual",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.atividade.refresh_from_db()
        self.assertEqual(self.atividade.descr_atividade, "Atividade original")

    def test_bloqueia_post_nova_atividade_com_rdc_fechado(self):
        url = reverse("rdc-atividade-create", kwargs={"pk": self.rdc.pk})
        response = self.client.post(
            url,
            data={
                "codigo_atividade": "ATVPOST2",
                "descr_atividade": "Nova atividade",
                "origem": "manual",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            RDCAtividade.objects.filter(
                rdc=self.rdc,
                codigo_atividade="ATVPOST2",
            ).exists()
        )

    def test_bloqueia_post_novo_apontamento_com_rdc_fechado(self):
        url = reverse("rdc-apontamento-create", kwargs={"pk": self.rdc.pk})
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 403)


