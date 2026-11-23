"""Acrescenta as disciplinas usuais de obra naval que ainda nao existirem.

So inclui: nao altera nem apaga disciplinas existentes. Compara pelo nome (sem
diferenciar maiusculas) e pelo codigo, para nao duplicar.
"""
from django.db import migrations

DISCIPLINAS_NAVAIS = [
    ("SOLDA", "Solda"),
    ("PINTURA", "Pintura e tratamento de superfície"),
    ("MECANICA", "Mecânica"),
    ("OUTFITTING", "Outfitting / acabamento"),
    ("ANDAIME", "Andaime"),
    ("INSTRUMENTACAO", "Instrumentação"),
    ("ICAMENTO", "Movimentação de carga e içamento"),
    ("ISOLAMENTO", "Isolamento térmico"),
    ("CQ", "Controle de qualidade"),
]


def incluir(apps, schema_editor):
    Disciplina = apps.get_model("cadastros", "Disciplina")
    for codigo, nome in DISCIPLINAS_NAVAIS:
        if Disciplina.objects.filter(nome__iexact=nome).exists() or Disciplina.objects.filter(codigo=codigo).exists():
            continue
        Disciplina.objects.create(codigo=codigo, nome=nome, ativo=True)


class Migration(migrations.Migration):
    dependencies = [
        ("cadastros", "0004_area_estrutura_naval"),
    ]

    # Reverter nao apaga nada: as disciplinas podem ja estar em uso em RDCs.
    operations = [migrations.RunPython(incluir, migrations.RunPython.noop)]
