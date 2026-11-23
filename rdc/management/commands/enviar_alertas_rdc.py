from django.core.management.base import BaseCommand, CommandError

from rdc.services.email_service import enviar_alertas_por_email


class Command(BaseCommand):
    help = "Envia por e-mail, para a lista de cada projeto, os alertas do dia do RDC."

    def handle(self, *args, **options):
        try:
            n = enviar_alertas_por_email()
        except ValueError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"{n} e-mail(s) de alerta enviado(s)."))
