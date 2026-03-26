from django.core.management.base import BaseCommand

from importacoes.models import ImportacaoArquivo


class Command(BaseCommand):
    help = "Normaliza o campo resumo das importações antigas que ainda estão vazio."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Somente mostra quantos registros seriam atualizados, sem salvar.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        queryset = ImportacaoArquivo.objects.all().order_by("id")

        total = 0
        atualizadas = 0

        for item in queryset:
            total += 1
            resumo = item.resumo or {}

            if resumo:
                continue

            novo_resumo = {
                "created": 0,
                "updated": 0,
                "unchanged": 0,
                "erros": item.total_erros,
            }

            atualizadas += 1

            if not dry_run:
                item.resumo = novo_resumo
                item.save(update_fields=["resumo", "updated_at"])

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY-RUN: {atualizadas} importação(ões) seriam atualizadas de um total de {total}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{atualizadas} importação(ões) atualizadas de um total de {total}."
                )
            )
