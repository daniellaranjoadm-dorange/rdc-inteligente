from django.contrib import admin

from rdc.models import RDC, RDCAtividade, RDCApontamento, RDCFuncionario, RDCValidacao, RDCAuditoria, PerfilOperacionalUsuario, CalendarioPlanejamento, ProgramacaoSemanal

class RDCAtividadeInline(admin.TabularInline):
    model = RDCAtividade
    extra = 0

class RDCFuncionarioInline(admin.TabularInline):
    model = RDCFuncionario
    extra = 0

class RDCValidacaoInline(admin.TabularInline):
    model = RDCValidacao
    extra = 0
    readonly_fields = ("tipo", "status", "mensagem", "referencia", "created_at")

@admin.register(RDC)
class RDCAdmin(admin.ModelAdmin):
    list_display = ("id", "projeto", "area_local", "disciplina", "data", "turno", "status", "criado_por")
    list_filter = ("status", "turno", "data", "projeto", "disciplina")
    search_fields = ("projeto__nome", "area_local__descricao", "disciplina__nome")
    autocomplete_fields = ("projeto", "area_local", "disciplina", "supervisor", "criado_por")
    inlines = [RDCAtividadeInline, RDCFuncionarioInline, RDCValidacaoInline]

@admin.register(RDCAtividade)
class RDCAtividadeAdmin(admin.ModelAdmin):
    list_display = ("rdc", "codigo_atividade", "descr_atividade", "origem", "obrigatoria", "ativa_no_dia")
    list_filter = ("origem", "obrigatoria", "ativa_no_dia")
    search_fields = ("codigo_atividade", "descr_atividade")
    autocomplete_fields = ("rdc", "atividade_cronograma")

@admin.register(RDCFuncionario)
class RDCFuncionarioAdmin(admin.ModelAdmin):
    list_display = ("rdc", "funcionario", "equipe", "funcao", "presente_catraca", "elegivel", "hh_total")
    list_filter = ("elegivel", "presente_catraca", "funcao", "equipe")
    search_fields = ("matricula", "nome")
    autocomplete_fields = ("rdc", "funcionario", "equipe", "funcao")

@admin.register(RDCApontamento)
class RDCApontamentoAdmin(admin.ModelAdmin):
    list_display = ("rdc", "rdc_funcionario", "rdc_atividade", "horas")
    list_filter = ("rdc",)
    search_fields = ("rdc_funcionario__nome", "rdc_atividade__descr_atividade")
    autocomplete_fields = ("rdc", "rdc_funcionario", "rdc_atividade")

@admin.register(RDCValidacao)
class RDCValidacaoAdmin(admin.ModelAdmin):
    list_display = ("rdc", "tipo", "status", "referencia", "created_at")
    list_filter = ("tipo", "status")
    search_fields = ("mensagem", "referencia")
    autocomplete_fields = ("rdc",)


@admin.register(PerfilOperacionalUsuario)
class PerfilOperacionalUsuarioAdmin(admin.ModelAdmin):
    list_display = ("user", "funcionario", "projeto_padrao", "disciplina_padrao", "equipe_padrao", "ativo")
    list_filter = ("ativo", "projeto_padrao", "disciplina_padrao", "equipe_padrao")
    search_fields = ("user__username", "funcionario__nome", "funcionario__matricula")
    autocomplete_fields = ("user", "funcionario", "projeto_padrao", "disciplina_padrao", "equipe_padrao")


@admin.register(CalendarioPlanejamento)
class CalendarioPlanejamentoAdmin(admin.ModelAdmin):
    list_display = ("projeto", "data", "semana_codigo", "semana_label", "dia_semana_nome", "eh_feriado")
    list_filter = ("projeto", "ano", "mes", "semana_codigo", "eh_feriado")
    search_fields = ("projeto__codigo", "semana_codigo", "semana_label", "descricao_evento")
    autocomplete_fields = ("projeto",)


@admin.register(ProgramacaoSemanal)
class ProgramacaoSemanalAdmin(admin.ModelAdmin):
    list_display = ("projeto", "semana_codigo", "data_programada", "disciplina", "area_local", "equipe", "codigo_atividade", "qtd_prevista", "hh_previsto")
    list_filter = ("projeto", "semana_codigo", "disciplina", "area_local", "equipe", "turno")
    search_fields = ("codigo_atividade", "descr_atividade", "codigo_subatividade", "descr_subatividade", "observacao")
    autocomplete_fields = ("projeto", "disciplina", "area_local", "equipe", "encarregado", "atividade_cronograma")


@admin.register(RDCAuditoria)
class RDCAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("rdc", "acao", "secao", "usuario", "created_at")
    list_filter = ("acao", "secao", "created_at")
    search_fields = ("resumo", "detalhe")
    autocomplete_fields = ("rdc", "usuario")
