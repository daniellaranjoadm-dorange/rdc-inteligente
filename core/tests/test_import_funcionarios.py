from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.models import ImportJob
from core.services.import_funcionarios import ImportFuncionariosCSVService


class ImportFuncionariosCSVTests(TestCase):
    def test_import_csv_basic(self):
        csv_content = "matricula,nome\n001,Fulano\n,SemMatricula\n"

        file = SimpleUploadedFile(
            "funcionarios.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        job = ImportJob.objects.create(
            tipo=ImportJob.TIPO_FUNCIONARIOS,
            arquivo=file,
        )

        result = ImportFuncionariosCSVService(job).run()

        self.assertEqual(result.total_linhas, 2)
        self.assertEqual(result.linhas_processadas, 1)
        self.assertEqual(result.linhas_com_erro, 1)
        self.assertEqual(result.status, ImportJob.STATUS_CONCLUIDO_PARCIAL)
