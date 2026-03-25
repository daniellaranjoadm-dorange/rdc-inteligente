from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from core.choices import TipoImportacaoChoices
from importacoes.models import ImportacaoArquivo
from importacoes.services import executar_importacao


class Command(BaseCommand):
    help = "Cria uma importAção de cronograma a partir de um arquivo local e processa imediatamente."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Caminho do arquivo XLSX/CSV de cronograma")
        parser.add_argument("--usuario", default="admin", help="Usuário responsável pela importAção")

    def handle(self, *args, **options):
        caminho = Path(options["arquivo"])
        if not caminho.exists():
            raise CommandError(f"Arquivo não encontrado: {caminho}")

        User = get_user_model()
        usuario = User.objects.filter(username=options["usuario"]).first()
        if not usuario:
            raise CommandError(f"Usuário não encontrado: {options['usuario']}")

        with caminho.open("rb") as fh:
            importacao = ImportacaoArquivo.objects.create(
                tipo=TipoImportacaoChoices.CRONOGRAMA,
                criado_por=usuario,
                observacoes="",
            )
            importacao.arquivo.save(caminho.name, File(fh), save=True)

        executar_importacao(importacao.pk)
        importacao.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f"ImportAção #{importacao.pk} finalizada com status: {importacao.status}"))
        self.stdout.write(importacao.observacoes)


