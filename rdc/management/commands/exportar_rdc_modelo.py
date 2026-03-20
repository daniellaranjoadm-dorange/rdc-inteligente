from django.core.management.base import BaseCommand, CommandError

from rdc.models import RDC
from rdc.services.rdc_service import exportar_rdc_para_modelo_excel


class Command(BaseCommand):
    help = "Exporta um RDC já criado para o modelo Excel."

    def add_arguments(self, parser):
        parser.add_argument("rdc_id", type=int)

    def handle(self, *args, **options):
        rdc = RDC.objects.filter(pk=options["rdc_id"]).first()
        if not rdc:
            raise CommandError(f"RDC não encontrado: {options['rdc_id']}")
        caminho = exportar_rdc_para_modelo_excel(rdc)
        self.stdout.write(self.style.SUCCESS(f"Arquivo gerado em: {caminho}"))


