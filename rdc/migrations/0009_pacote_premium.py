from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('rdc', '0002_rdc_fechamento_controlado'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RDCAuditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(max_length=40)),
                ('secao', models.CharField(blank=True, max_length=40)),
                ('referencia_id', models.PositiveIntegerField(blank=True, null=True)),
                ('resumo', models.CharField(max_length=255)),
                ('detalhe', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'rdc',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='auditorias',
                        to='rdc.rdc',
                    ),
                ),
                (
                    'usuario',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='rdc_auditorias',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ('-created_at', '-id'),
            },
        ),
    ]