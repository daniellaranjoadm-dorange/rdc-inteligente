from django.contrib import admin

from soldagem.models import EPS, ExecucaoSolda, InspecaoEND, JuntaSolda, Soldador


@admin.register(Soldador)
class SoldadorAdmin(admin.ModelAdmin):
    list_display = ("sinete", "funcionario", "processos", "validade_qualificacao", "ativo")
    search_fields = ("sinete", "funcionario__nome")


@admin.register(EPS)
class EPSAdmin(admin.ModelAdmin):
    list_display = ("codigo", "processo", "material", "ativo")


@admin.register(JuntaSolda)
class JuntaSoldaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "projeto", "area_local", "comprimento_m", "metodo_end", "status")
    list_filter = ("status", "metodo_end", "projeto")
    search_fields = ("codigo", "descricao")


admin.site.register(ExecucaoSolda)
admin.site.register(InspecaoEND)
