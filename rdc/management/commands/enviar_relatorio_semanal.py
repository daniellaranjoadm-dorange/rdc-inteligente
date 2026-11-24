from django.core.management.base import BaseCommand, CommandError

from rdc.services.relatorio_semanal import enviar_relatorios_semanais


class Command(BaseCommand):
    help = "Envia o relatório semanal (PDF) de cada projeto para os e-mails cadastrados."

    def handle(self, *args, **options):
        try:
            n = enviar_relatorios_semanais()
        except ValueError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"{n} relatório(s) semanal(is) enviado(s)."))
