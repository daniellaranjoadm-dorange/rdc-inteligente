"""Apaga os dados operacionais (RDCs, cronograma, cadastros) para começar do zero.

Mantém: usuários, perfis de acesso e o histórico de auditoria de acesso.
Antes de apagar, grava um backup JSON (dumpdata) que permite restaurar com loaddata.

Uso:
    python manage.py reiniciar_dados              -> só mostra o que seria apagado
    python manage.py reiniciar_dados --confirmar  -> faz o backup e apaga
"""
import os
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

# Ordem importa: filhos antes dos pais (vários vínculos são PROTECT).
MODELOS = [
    "soldagem.InspecaoEND",
    "soldagem.ExecucaoSolda",
    "soldagem.JuntaSolda",
    "soldagem.Soldador",
    "soldagem.EPS",
    "rdc.RDC",                       # leva atividades, equipe, apontamentos, fotos, aceites, paralisações...
    "rdc.ProgramacaoSemanal",
    "rdc.PerfilOperacionalUsuario",  # vínculo do usuário com um funcionário (modo campo)
    "rdc.CalendarioPlanejamento",
    "planejamento.AtividadeCronograma",
    "alocacao.HistogramaPlanejado",
    "alocacao.FuncionarioProjeto",
    "acesso.RegistroCatraca",
    "importacoes.ImportacaoArquivo",
    "core.ImportJob",
    "cadastros.Equipe",
    "cadastros.Funcionario",
    "cadastros.Funcao",
    "cadastros.Empresa",
    "cadastros.AreaLocal",
    "cadastros.Disciplina",
    "cadastros.Projeto",
]
APPS_BACKUP = ["cadastros", "planejamento", "alocacao", "acesso", "importacoes", "core", "rdc", "soldagem"]


def _modelos():
    for label in MODELOS:
        try:
            yield label, apps.get_model(label)
        except LookupError:
            continue


def pasta_backup():
    if os.getenv("BACKUP_DIR"):
        return Path(os.getenv("BACKUP_DIR"))
    return Path(settings.MEDIA_ROOT).parent / "backups"


class Command(BaseCommand):
    help = "Apaga RDCs, cronograma e cadastros (mantém usuários). Sem --confirmar só lista."

    def add_arguments(self, parser):
        parser.add_argument("--confirmar", action="store_true", help="Faz o backup e apaga de verdade.")
        parser.add_argument("--sem-backup", action="store_true", help="Não grava o backup JSON (não recomendado).")

    def handle(self, *args, **options):
        contagem = [(label, model.objects.count()) for label, model in _modelos()]
        for label, n in contagem:
            self.stdout.write(f"  {label:<36} {n:>7}")
        total = sum(n for _, n in contagem)
        if not options["confirmar"]:
            self.stdout.write(self.style.WARNING(f"{total} registro(s) seriam apagados. Rode com --confirmar para apagar."))
            return

        if not options["sem_backup"]:
            pasta = pasta_backup()
            pasta.mkdir(parents=True, exist_ok=True)
            arquivo = pasta / f"rdc_antes_reinicio_{timezone.now():%Y%m%d_%H%M%S}.json"
            with open(arquivo, "w", encoding="utf-8") as saida:
                call_command("dumpdata", *APPS_BACKUP, indent=0, stdout=saida)
            if arquivo.stat().st_size == 0:
                raise CommandError("Backup saiu vazio; nada foi apagado.")
            self.stdout.write(self.style.SUCCESS(f"Backup gravado: {arquivo}"))
            self.stdout.write(f"Para desfazer: python manage.py loaddata {arquivo}")

        with transaction.atomic():
            for label, model in _modelos():
                model.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Pronto: {total} registro(s) apagados. Usuários e perfis de acesso mantidos."))
