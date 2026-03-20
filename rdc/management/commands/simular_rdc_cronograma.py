from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from core.choices import TipoImportacaoChoices, TurnoChoices
from importacoes.models import ImportacaoArquivo
from importacoes.services import executar_importacao
from planejamento.models import AtividadeCronograma
from rdc.services.rdc_service import exportar_rdc_para_modelo_excel, montar_rdc_simulado_por_cronograma


class Command(BaseCommand):
    help = "Importa um cronograma local, monta um RDC simulado e exporta no modelo Excel."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Caminho do arquivo XLSX/CSV de cronograma")
        parser.add_argument("--usuario", default="admin", help="Usuário responsável pela simulAção")
        parser.add_argument("--data", help="Data do RDC no formato YYYY-MM-DD")
        parser.add_argument("--turno", default=TurnoChoices.INTEGRAL, choices=[c[0] for c in TurnoChoices.CHOICES])
        parser.add_argument("--projeto", help="Código do projeto já importado")
        parser.add_argument("--modelo", help="Caminho do modelo RDC .xlsx, opcional")

    def handle(self, *args, **options):
        caminho = Path(options["arquivo"])
        if not caminho.exists():
            raise CommandError(f"Arquivo não encontrado: {caminho}")

        User = get_user_model()
        usuario = User.objects.filter(username=options["usuario"]).first()
        if not usuario:
            raise CommandError(f"Usuário não encontrado: {options['usuario']}")

        projeto_codigo = options.get("projeto")
        if not projeto_codigo:
            importacao = self._criar_importacao(caminho, usuario)
            executar_importacao(importacao.pk)
            importacao.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(f"ImportAção #{importacao.pk} finalizada com status: {importacao.status}"))
            self.stdout.write(importacao.observacoes)

        projeto_id = None
        if projeto_codigo:
            atividade = AtividadeCronograma.objects.filter(projeto__codigo__iexact=projeto_codigo).select_related("projeto").first()
            if not atividade:
                raise CommandError(f"Projeto não encontrado no cronograma importado: {projeto_codigo}")
            projeto_id = atividade.projeto_id

        data_ref = parse_date(options["data"]) if options.get("data") else None
        if options.get("data") and not data_ref:
            raise CommandError("Data inválida. Use o formato YYYY-MM-DD.")

        modelo = options.get("modelo")
        if modelo:
            self._configurar_modelo(modelo)

        rdc, contexto = montar_rdc_simulado_por_cronograma(
            user=usuario,
            projeto_id=projeto_id,
            data=data_ref,
            turno=options["turno"],
        )
        arquivo_saida = exportar_rdc_para_modelo_excel(rdc)

        self.stdout.write(self.style.SUCCESS(f"RDC #{rdc.pk} montado e exportado com sucesso."))
        self.stdout.write(f"Projeto: {contexto['projeto'].codigo}")
        self.stdout.write(f"Data: {contexto['data']}")
        self.stdout.write(f"Disciplina: {contexto['disciplina'].nome}")
        self.stdout.write(f"Área/local: {contexto['area_local'].descricao}")
        self.stdout.write(f"Atividades no contexto: {contexto['total_atividades']}")
        self.stdout.write(f"Arquivo gerado: {arquivo_saida}")

    def _criar_importacao(self, caminho: Path, usuario):
        with caminho.open("rb") as fh:
            importacao = ImportacaoArquivo.objects.create(
                tipo=TipoImportacaoChoices.CRONOGRAMA,
                criado_por=usuario,
                observacoes="",
            )
            importacao.arquivo.save(caminho.name, File(fh), save=True)
        return importacao

    def _configurar_modelo(self, caminho_modelo: str):
        from django.conf import settings

        modelo_path = Path(caminho_modelo)
        if not modelo_path.exists():
            raise CommandError(f"Modelo RDC não encontrado: {modelo_path}")
        settings.RDC_TEMPLATE_PATH = modelo_path



