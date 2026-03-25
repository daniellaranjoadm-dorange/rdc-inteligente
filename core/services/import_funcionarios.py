import csv

from core.services.import_base import BaseImportService


class ImportFuncionariosCSVService(BaseImportService):
    tipo_importacao = "funcionarios"

    def parse(self):
        if not self.import_job.arquivo:
            return []

        decoded_file = self.import_job.arquivo.read().decode("utf-8").splitlines()
        reader = csv.DictReader(decoded_file)

        return list(reader)

    def validate_row(self, row, index):
        errors = []

        if not row.get("matricula"):
            errors.append("Matrícula obrigatória.")

        if not row.get("nome"):
            errors.append("Nome obrigatório.")

        return errors

    def process_row(self, row, index):
        # Por enquanto só simula processamento
        # Depois aqui vamos integrar com model real

        return {
            "matricula": row.get("matricula"),
            "nome": row.get("nome"),
        }
