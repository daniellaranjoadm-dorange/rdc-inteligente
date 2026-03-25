import csv

from core.services.import_base import BaseImportService


class ImportFuncionariosCSVService(BaseImportService):
    tipo_importacao = "funcionarios"

    def parse(self):
        if not self.import_job.arquivo:
            return []

        raw_content = self.import_job.arquivo.read()

        try:
            text = raw_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw_content.decode("latin1")

        content = text.splitlines()

        sample = "\n".join(content[:5])
        try:
            dialect = csv.Sniffer().sniff(sample)
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ","

        reader = csv.DictReader(content, delimiter=delimiter)

        rows = []
        for row in reader:
            normalized_row = {}
            for key, value in row.items():
                normalized_key = (key or "").replace("\ufeff", "").strip().lower()
                normalized_row[normalized_key] = value.strip() if isinstance(value, str) else value
            rows.append(normalized_row)

        return rows

    def validate_row(self, row, index):
        errors = []

        if not row.get("matricula"):
            errors.append("Matrícula obrigatória.")

        if not row.get("nome"):
            errors.append("Nome obrigatório.")

        return errors

    def process_row(self, row, index):
        return {
            "matricula": row.get("matricula"),
            "nome": row.get("nome"),
        }
