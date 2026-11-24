from django.contrib import admin

from punchlist.models import PunchFoto, PunchItem


@admin.register(PunchItem)
class PunchItemAdmin(admin.ModelAdmin):
    list_display = ("codigo", "projeto", "area_local", "categoria", "status", "prazo", "responsavel")
    list_filter = ("status", "categoria", "projeto")
    search_fields = ("descricao", "compartimento", "responsavel")


admin.site.register(PunchFoto)
