
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import PerfilAcesso
from cadastros.models import Projeto, AreaLocal, Disciplina
from core.choices import TurnoChoices
from rdc.models import RDC
from rdc.services.workflow_service import process_rdc_workflow_action


User = get_user_model()


class RDCWorkflowServiceTests(TestCase):
    def setUp(self):
        self.user_admin = User.objects.create_user(
            username="admin_teste",
            password="123",
            is_staff=True,
        )
        PerfilAcesso.objects.create(user=self.user_admin, role="admin")

        self.projeto = Projeto.objects.create(
            codigo="PRJ1",
            nome="Projeto Teste",
            cliente="Cliente Teste",
        )

        self.disciplina = Disciplina.objects.create(
            codigo="DISC1",
            nome="Disciplina Teste",
        )

        self.area = AreaLocal.objects.create(
            projeto=self.projeto,
            codigo="AREA1",
            descricao="?rea Teste",
            disciplina_padrao=self.disciplina,
        )

        self.rdc = RDC.objects.create(
            projeto=self.projeto,
            area_local=self.area,
            disciplina=self.disciplina,
            data=timezone.now().date(),
            turno=TurnoChoices.MANHA,
            status="rascunho",
            criado_por=self.user_admin,
        )

    def test_fechar_rdc(self):
        result = process_rdc_workflow_action(
            self.rdc,
            action="fechar",
            user=self.user_admin,
            observacao="Fechamento de teste",
        )

        self.rdc.refresh_from_db()

        self.assertTrue(result["ok"])
        self.assertEqual(self.rdc.status, "fechado")

    def test_reabrir_rdc(self):
        self.rdc.status = "fechado"
        self.rdc.save()

        result = process_rdc_workflow_action(
            self.rdc,
            action="reabrir",
            user=self.user_admin,
            observacao="Reabertura de teste",
        )

        self.rdc.refresh_from_db()

        self.assertTrue(result["ok"])
        self.assertEqual(self.rdc.status, "rascunho")


    def test_operador_nao_pode_fechar_rdc(self):
        user_operador = User.objects.create_user(
            username="operador_teste",
            password="123",
            is_staff=False,
        )
        PerfilAcesso.objects.create(user=user_operador, role="operador")

        result = process_rdc_workflow_action(
            self.rdc,
            action="fechar",
            user=user_operador,
            observacao="Tentativa sem permiss?o",
        )

        self.rdc.refresh_from_db()

        self.assertFalse(result["ok"])
        self.assertEqual(self.rdc.status, "rascunho")

