from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from rdc.models import PerfilOperacionalUsuario


class Command(BaseCommand):
    help = "Garante que um usuário tenha PerfilOperacionalUsuario ativo."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)

    def handle(self, *args, **options):
        username = options["username"]
        User = get_user_model()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"Usuário não encontrado: {username}")

        perfil, created = PerfilOperacionalUsuario.objects.get_or_create(
            user=user,
            defaults={"ativo": True},
        )

        if not perfil.ativo:
            perfil.ativo = True
            perfil.save(update_fields=["ativo"])

        acao = "criado" if created else "atualizado"
        self.stdout.write(self.style.SUCCESS(
            f"Perfil operacional {acao} com sucesso para: {username}"
        ))
