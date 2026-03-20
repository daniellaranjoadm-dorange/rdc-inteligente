
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC


User = get_user_model()


class RDCDetailFiltersUITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="supervisor_detail_ui",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user, role="supervisor")

        self.projeto = Projeto.objects.create(
            codigo="PRJDFUI",
            nome="Projeto Detail UI",
            cliente="Cliente Detail UI",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISDFUI",
            nome="Disciplina Detail UI",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREADFUI",
            descricao="?rea Detail UI",
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

        self.client.login(username="supervisor_detail_ui", password="123")

    def test_detalhe_exibe_filtros_e_resumos_das_abas(self):
        url = reverse("rdc-detail", kwargs={"pk": self.rdc.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Atividades filtradas")
        self.assertContains(response, "Funcion?rios filtrados")
        self.assertContains(response, "Apontamentos filtrados")
        self.assertContains(response, "Valida??es filtradas")
