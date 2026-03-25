from django.utils import timezone

from core.models import ImportJob


class BaseImportService:
    tipo_importacao = ImportJob.TIPO_OUTRO

    def __init__(self, import_job):
        self.import_job = import_job

    def parse(self):
        """
        Deve retornar uma lista de registros normalizados.
        """
        raise NotImplementedError

    def validate_row(self, row, index):
        """
        Deve retornar lista de erros da linha.
        """
        return []

    def process_row(self, row, index):
        """
        Processa a linha validada.
        """
        raise NotImplementedError

    def run(self):
        self.import_job.status = ImportJob.STATUS_PROCESSANDO
        self.import_job.iniciado_em = timezone.now()
        self.import_job.save(update_fields=["status", "iniciado_em", "atualizado_em"])

        registros = self.parse() or []
        self.import_job.total_linhas = len(registros)

        erros = []
        processadas = 0

        for index, row in enumerate(registros, start=1):
            row_errors = self.validate_row(row, index)
            if row_errors:
                erros.append(
                    {
                        "linha": index,
                        "erros": row_errors,
                        "dados": row,
                    }
                )
                continue

            self.process_row(row, index)
            processadas += 1

        self.import_job.linhas_processadas = processadas
        self.import_job.linhas_com_erro = len(erros)
        self.import_job.erros = erros
        self.import_job.finalizado_em = timezone.now()

        if erros and processadas:
            self.import_job.status = ImportJob.STATUS_CONCLUIDO_PARCIAL
        elif erros and not processadas:
            self.import_job.status = ImportJob.STATUS_ERRO
        else:
            self.import_job.status = ImportJob.STATUS_CONCLUIDO

        self.import_job.resumo = {
            "total_linhas": self.import_job.total_linhas,
            "linhas_processadas": self.import_job.linhas_processadas,
            "linhas_com_erro": self.import_job.linhas_com_erro,
        }

        self.import_job.save()
        return self.import_job
