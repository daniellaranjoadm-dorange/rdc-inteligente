from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import ImportJob
from core.services.import_base import BaseImportService


class DummyImportService(BaseImportService):
    def parse(self):
        return [
            {"matricula": "001", "nome": "Fulano"},
            {"matricula": "", "nome": "Sem Matricula"},
        ]

    def validate_row(self, row, index):
        errors = []
        if not row.get("matricula"):
            errors.append("Matrícula obrigatória.")
        return errors

    def process_row(self, row, index):
        return row


class ImportJobTests(TestCase):
    def test_import_job_str(self):
        job = ImportJob.objects.create(
            tipo=ImportJob.TIPO_FUNCIONARIOS,
            status=ImportJob.STATUS_PENDENTE,
        )
        self.assertIn("Funcionários", str(job))

    def test_base_import_service_marks_partial_success(self):
        User = get_user_model()
        user = User.objects.create(username="tester")

        job = ImportJob.objects.create(
            tipo=ImportJob.TIPO_FUNCIONARIOS,
            usuario=user,
            status=ImportJob.STATUS_PENDENTE,
        )

        result = DummyImportService(job).run()

        self.assertEqual(result.status, ImportJob.STATUS_CONCLUIDO_PARCIAL)
        self.assertEqual(result.total_linhas, 2)
        self.assertEqual(result.linhas_processadas, 1)
        self.assertEqual(result.linhas_com_erro, 1)
        self.assertEqual(len(result.erros), 1)
