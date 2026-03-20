from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from cadastros.models import AreaLocal, Disciplina, Projeto
from rdc.models import RDC
from rdc.services.rdc_service import montar_rdc_pre_preenchido


class Command(BaseCommand):
    help = "Monta um RDC pré-preenchido para o contexto informado."

    def add_arguments(self, parser):
        parser.add_argument("--projeto", required=True, help="Código do projeto")
        parser.add_argument("--area", required=True, help="Código da área/local")
        parser.add_argument("--disciplina", required=True, help="Código da disciplina")
        parser.add_argument("--data", required=True, help="Data no formato YYYY-MM-DD")
        parser.add_argument("--turno", default="integral", help="manha, tarde, noite ou integral")
        parser.add_argument("--usuario", default="admin", help="Usuário responsável")

    def handle(self, *args, **options):
        projeto = Projeto.objects.filter(codigo__iexact=options["projeto"]).first()
        if not projeto:
            raise CommandError(f"Projeto não encontrado: {options['projeto']}")

        area = AreaLocal.objects.filter(projeto=projeto, codigo__iexact=options["area"]).first()
        if not area:
            raise CommandError(f"Área/local não encontrada: {options['area']}")

        disciplina = Disciplina.objects.filter(codigo__iexact=options["disciplina"]).first()
        if not disciplina:
            raise CommandError(f"Disciplina não encontrada: {options['disciplina']}")

        User = get_user_model()
        usuario = User.objects.filter(username=options["usuario"]).first()
        if not usuario:
            raise CommandError(f"Usuário não encontrado: {options['usuario']}")

        data = datetime.strptime(options["data"], "%Y-%m-%d").date()
        existente = RDC.objects.filter(
            projeto=projeto,
            area_local=area,
            disciplina=disciplina,
            data=data,
            turno=options["turno"],
        ).first()
        if existente:
            self.stdout.write(self.style.WARNING(f"RDC já existe: #{existente.pk}"))
            return

        rdc = montar_rdc_pre_preenchido(
            projeto_id=projeto.id,
            area_local_id=area.id,
            disciplina_id=disciplina.id,
            data=data,
            turno=options["turno"],
            user=usuario,
        )
        self.stdout.write(self.style.SUCCESS(f"RDC criado com sucesso: #{rdc.pk}"))



