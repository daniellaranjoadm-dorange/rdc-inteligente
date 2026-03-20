from django.contrib import admin

from acesso.models import RegistroCatraca

@admin.register(RegistroCatraca)
class RegistroCatracaAdmin(admin.ModelAdmin):
    list_display = ("data", "matricula", "funcionario", "projeto", "presente", "origem_arquivo")
    list_filter = ("data", "presente", "projeto")
    search_fields = ("matricula", "funcionario__nome", "origem_arquivo")
    autocomplete_fields = ("funcionario", "projeto")
