from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from rdc.models import PerfilOperacionalUsuario
from cadastros.models import Funcionario


class Command(BaseCommand):
    help = "Garante que um usuario tenha PerfilOperacionalUsuario ativo."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("--funcionario-id", type=int, dest="funcionario_id", default=None)

    def handle(self, *args, **options):
        username = options["username"]
        funcionario_id = options["funcionario_id"]
        User = get_user_model()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Usuario nao encontrado: {username}")

        if funcionario_id is not None:
            try:
                funcionario = Funcionario.objects.get(pk=funcionario_id)
            except Funcionario.DoesNotExist:
                raise CommandError(f"Funcionario nao encontrado: {funcionario_id}")
        else:
            funcionario = Funcionario.objects.first()

        if not funcionario:
            raise CommandError("Nenhum funcionario encontrado no sistema.")

        perfil, created = PerfilOperacionalUsuario.objects.get_or_create(
            user=user,
            defaults={
                "ativo": True,
                "funcionario": funcionario,
            },
        )

        campos_para_atualizar = []

        if perfil.funcionario_id != funcionario.id:
            perfil.funcionario = funcionario
            campos_para_atualizar.append("funcionario")

        if not perfil.ativo:
            perfil.ativo = True
            campos_para_atualizar.append("ativo")

        if campos_para_atualizar:
            perfil.save(update_fields=campos_para_atualizar)

        acao = "criado" if created else "atualizado"

        self.stdout.write(
            self.style.SUCCESS(
                f"Perfil operacional {acao} com sucesso para: {username} (funcionario_id={funcionario.id})"
            )
        )


