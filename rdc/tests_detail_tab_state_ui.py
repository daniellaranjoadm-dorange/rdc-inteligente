
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC


User = get_user_model()


class RDCDetailTabStateUITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supervisor_tab_ui",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

        self.projeto = Projeto.objects.create(
            codigo="PRJTABUI",
            nome="Projeto Tab UI",
            cliente="Cliente Tab UI",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISTABUI",
            nome="Disciplina Tab UI",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREATABUI",
            descricao="?rea Tab UI",
            disciplina_padrao=self.disciplina,
        )

        self.rdc = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date(),
            turno=TurnoChoices.MANHA,
            status="rascunho",
            criado_por=self.user,
        )

        self.client.login(username="supervisor_tab_ui", password="123")

    def test_detalhe_renderiza_suporte_a_tab_por_querystring(self):
        url = reverse("rdc-detail", kwargs={"pk": self.rdc.pk}) + "?tab=funcionarios"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "const tabFromQuery = urlParams.get('tab');")
        self.assertContains(response, "#funcionarios")
