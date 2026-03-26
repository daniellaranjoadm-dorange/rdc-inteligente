import csv

from cadastros.models import Empresa, Funcao, Funcionario
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

        if not row.get("empresa"):
            errors.append("Empresa obrigatória.")

        if not row.get("funcao"):
            errors.append("Função obrigatória.")

        return errors

    def process_row(self, row, index):
        empresa_nome = row.get("empresa").strip()
        funcao_nome = row.get("funcao").strip()

        try:
            empresa = Empresa.objects.get(nome=empresa_nome)
        except Empresa.DoesNotExist:
            raise ValueError(f'Empresa "{empresa_nome}" não cadastrada.')

        try:
            funcao = Funcao.objects.get(nome=funcao_nome)
        except Funcao.DoesNotExist:
            raise ValueError(f'Função "{funcao_nome}" não cadastrada.')

        matricula = row.get("matricula").strip()
        nome = row.get("nome").strip()

        funcionario = Funcionario.objects.filter(matricula=matricula).first()

        if not funcionario:
            Funcionario.objects.create(
                matricula=matricula,
                nome=nome,
                empresa=empresa,
                funcao=funcao,
            )
            return "created"

        changed = False

        if funcionario.nome != nome:
            funcionario.nome = nome
            changed = True

        if funcionario.empresa_id != empresa.id:
            funcionario.empresa = empresa
            changed = True

        if funcionario.funcao_id != funcao.id:
            funcionario.funcao = funcao
            changed = True

        if changed:
            funcionario.save()
            return "updated"

        return "unchanged"

