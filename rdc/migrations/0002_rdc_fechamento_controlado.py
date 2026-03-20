from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rdc', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='rdc',
            name='fechado_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rdc',
            name='fechado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rdcs_fechados', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='rdc',
            name='justificativa_fechamento',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='rdc',
            name='permite_edicao_pos_fechamento',
            field=models.BooleanField(default=False),
        ),
    ]
