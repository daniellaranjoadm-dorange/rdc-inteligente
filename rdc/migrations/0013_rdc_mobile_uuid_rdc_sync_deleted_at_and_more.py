import uuid

from django.db import migrations, models
from django.utils import timezone


def preencher_sync_fields(apps, schema_editor):
    modelos = [
        apps.get_model("rdc", "RDC"),
        apps.get_model("rdc", "RDCAtividade"),
        apps.get_model("rdc", "RDCFuncionario"),
        apps.get_model("rdc", "RDCApontamento"),
    ]

    for Model in modelos:
        for obj in Model.objects.all():
            mudou = False

            if not getattr(obj, "mobile_uuid", None):
                obj.mobile_uuid = uuid.uuid4()
                mudou = True

            if not getattr(obj, "sync_updated_at", None):
                obj.sync_updated_at = timezone.now()
                mudou = True

            if mudou:
                obj.save(update_fields=["mobile_uuid", "sync_updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("rdc", "0012_rdcfuncionario_justificativa_liberacao_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="rdc",
            name="mobile_uuid",
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="rdc",
            name="sync_deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="rdc",
            name="sync_updated_at",
            field=models.DateTimeField(default=timezone.now, db_index=True),
        ),

        migrations.AddField(
            model_name="rdcapontamento",
            name="mobile_uuid",
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="rdcapontamento",
            name="sync_deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="rdcapontamento",
            name="sync_updated_at",
            field=models.DateTimeField(default=timezone.now, db_index=True),
        ),

        migrations.AddField(
            model_name="rdcatividade",
            name="mobile_uuid",
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="rdcatividade",
            name="sync_deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="rdcatividade",
            name="sync_updated_at",
            field=models.DateTimeField(default=timezone.now, db_index=True),
        ),

        migrations.AddField(
            model_name="rdcfuncionario",
            name="mobile_uuid",
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="rdcfuncionario",
            name="sync_deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="rdcfuncionario",
            name="sync_updated_at",
            field=models.DateTimeField(default=timezone.now, db_index=True),
        ),

        migrations.RunPython(preencher_sync_fields, migrations.RunPython.noop),

        migrations.AlterField(
            model_name="rdc",
            name="mobile_uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="rdcapontamento",
            name="mobile_uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="rdcatividade",
            name="mobile_uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="rdcfuncionario",
            name="mobile_uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                db_index=True,
            ),
        ),
    ]
