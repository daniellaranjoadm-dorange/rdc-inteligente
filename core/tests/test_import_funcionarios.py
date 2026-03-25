from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from cadastros.models import Empresa, Funcao, Funcionario
from core.models import ImportJob
from core.services.import_funcionarios import ImportFuncionariosCSVService


class ImportFuncionariosCSVTests(TestCase):
    def test_import_csv_basic(self):
        Empresa.objects.create(nome="Empresa X", ativa=True)
        Empresa.objects.create(nome="Empresa Y", ativa=True)

        Funcao.objects.create(nome="Eletricista", codigo="ELETRICISTA", ativa=True)
        Funcao.objects.create(nome="Encanador", codigo="ENCANADOR", ativa=True)

        csv_content = (
            "matricula,nome,empresa,funcao\n"
            "001,Fulano,Empresa X,Eletricista\n"
            "002,Ciclano,Empresa Y,Encanador\n"
        )

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
        self.assertEqual(result.linhas_processadas, 2)
        self.assertEqual(result.linhas_com_erro, 0)
        self.assertEqual(result.status, ImportJob.STATUS_CONCLUIDO)

        self.assertEqual(Funcionario.objects.count(), 2)
        self.assertEqual(Empresa.objects.count(), 2)  # pré-cadastradas
        self.assertEqual(Funcao.objects.count(), 2)  # pré-cadastradas

    def test_import_csv_requires_empresa_and_funcao(self):
        csv_content = (
            "matricula,nome,empresa,funcao\n"
            "001,Fulano,,\n"
        )

        file = SimpleUploadedFile(
            "funcionarios_invalidos.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        job = ImportJob.objects.create(
            tipo=ImportJob.TIPO_FUNCIONARIOS,
            arquivo=file,
        )

        result = ImportFuncionariosCSVService(job).run()

        self.assertEqual(result.total_linhas, 1)
        self.assertEqual(result.linhas_processadas, 0)
        self.assertEqual(result.linhas_com_erro, 1)
        self.assertEqual(result.status, ImportJob.STATUS_ERRO)
