from core.choices import StatusImportacaoChoices
from importacoes.models import ImportacaoArquivo

from .original_service import (
    ImportadorAlocacao,
    ImportadorCatraca,
    ImportadorCronograma,
    ImportadorFuncionarios,
)


def executar_importacao(importacao_id: int) -> None:
    importacao = ImportacaoArquivo.objects.get(pk=importacao_id)

    mapa_importadores = {
        "funcionarios": ImportadorFuncionarios,
        "catraca": ImportadorCatraca,
        "alocacoes": ImportadorAlocacao,
        "cronograma": ImportadorCronograma,
    }

    importador_cls = mapa_importadores.get(importacao.tipo)
    if not importador_cls:
        importacao.status = StatusImportacaoChoices.ERRO
        importacao.observacoes = f"Tipo de importação ainda não implementado: {importacao.tipo}"
        importacao.save(update_fields=["status", "observacoes"])
        return

    importador = importador_cls(importacao)
    importador.processar()
