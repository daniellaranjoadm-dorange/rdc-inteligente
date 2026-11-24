"""Regras do diário de solda e indicadores do painel."""
from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from core.audit import registrar_auditoria
from soldagem.models import (
    ExecucaoSolda, InspecaoEND, JuntaSolda, ResultadoEND, Soldador, StatusJunta,
)

LIMITE_TAXA_REPARO = 5.0   # % de metros reprovados sobre inspecionados; acima disso o soldador/bloco é destacado
DIAS_END_ATRASADO = 2      # chamada de END sem resultado há mais que isso vira alerta
ZERO = Decimal("0")


def _rdc_do_dia(junta, data):
    from rdc.models import RDC
    qs = RDC.objects.filter(projeto_id=junta.projeto_id, area_local_id=junta.area_local_id, data=data)
    return qs.filter(disciplina__nome__icontains="sold").first() or qs.first()


@transaction.atomic
def registrar_execucao(junta, *, soldador, data, metros, passe="completo", reparo=False, usuario=None, observacao=""):
    junta = JuntaSolda.objects.select_for_update().select_related("eps").get(pk=junta.pk)
    metros = Decimal(str(metros))
    if metros <= 0:
        raise ValidationError("Informe os metros soldados.")
    if not soldador.ativo:
        raise ValidationError(f"O soldador {soldador.sinete} está inativo.")
    if soldador.validade_qualificacao < data:
        raise ValidationError(
            f"Qualificação do soldador {soldador.sinete} venceu em {soldador.validade_qualificacao:%d/%m/%Y}. "
            "Renove a qualificação antes de lançar a solda.")
    if junta.eps and junta.eps.processo.upper() not in soldador.processos.upper():
        raise ValidationError(
            f"O soldador {soldador.sinete} não é qualificado no processo {junta.eps.processo} exigido pela EPS {junta.eps.codigo}.")

    if junta.status in (StatusJunta.APROVADA, StatusJunta.CONCLUIDA):
        raise ValidationError("Esta junta já está aprovada/concluída.")
    if reparo and junta.status != StatusJunta.REPROVADA:
        raise ValidationError("Reparo só pode ser lançado em junta reprovada no END.")
    if not reparo and junta.status == StatusJunta.REPROVADA:
        raise ValidationError("Junta reprovada: lance a solda como reparo.")
    if not reparo and junta.status == StatusJunta.AGUARDANDO_END:
        raise ValidationError("A junta está aguardando o resultado do END.")

    feito = junta.metros_soldados
    if not reparo and feito + metros > junta.comprimento_m:
        raise ValidationError(
            f"Passaria do comprimento da junta: {feito} m já soldados de {junta.comprimento_m} m.")

    execucao = ExecucaoSolda.objects.create(
        junta=junta, soldador=soldador, data=data, metros=metros, passe=passe, reparo=reparo,
        rdc=_rdc_do_dia(junta, data), observacao=observacao, criado_por=usuario)

    if reparo:
        ultimo = junta.inspecoes.aggregate(m=Max("ciclo"))["m"] or 1
        inspecao = InspecaoEND.objects.create(
            junta=junta, metodo=junta.metodo_end or "VS", ciclo=ultimo + 1, solicitado_em=data,
            metros_inspecionados=metros)
        inspecao.soldadores.add(soldador)
        junta.status = StatusJunta.AGUARDANDO_END
    elif feito + metros >= junta.comprimento_m:
        if junta.metodo_end:
            inspecao = InspecaoEND.objects.create(
                junta=junta, metodo=junta.metodo_end, ciclo=1, solicitado_em=data,
                metros_inspecionados=junta.comprimento_m)
            inspecao.soldadores.set(Soldador.objects.filter(execucoes__junta=junta, execucoes__reparo=False).distinct())
            junta.status = StatusJunta.AGUARDANDO_END
        else:
            junta.status = StatusJunta.CONCLUIDA
    else:
        junta.status = StatusJunta.EM_EXECUCAO
    junta.save(update_fields=["status", "updated_at"])
    registrar_auditoria(usuario, "registrar_solda", target_model="JuntaSolda", target_id=junta.pk,
                        detail=f"{junta.codigo}: {metros} m por {soldador.sinete}{' (reparo)' if reparo else ''}")
    return execucao


@transaction.atomic
def registrar_resultado_end(inspecao, *, resultado, data, metros_reprovados=ZERO, defeito="", inspetor="",
                            relatorio="", observacao="", usuario=None):
    inspecao = InspecaoEND.objects.select_for_update().select_related("junta").get(pk=inspecao.pk)
    if inspecao.resultado != ResultadoEND.PENDENTE:
        raise ValidationError("Este ensaio já tem resultado.")
    if resultado not in (ResultadoEND.APROVADO, ResultadoEND.REPROVADO):
        raise ValidationError("Resultado inválido.")
    metros_reprovados = Decimal(str(metros_reprovados or 0))
    if resultado == ResultadoEND.REPROVADO:
        if metros_reprovados <= 0:
            raise ValidationError("Informe quantos metros foram reprovados.")
        if metros_reprovados > inspecao.metros_inspecionados:
            raise ValidationError(f"Reprovado não pode passar do inspecionado ({inspecao.metros_inspecionados} m).")
        if not defeito:
            raise ValidationError("Informe o defeito encontrado.")
    else:
        metros_reprovados, defeito = ZERO, ""
    if data < inspecao.solicitado_em:
        raise ValidationError("A data do ensaio não pode ser antes da chamada de END.")

    inspecao.resultado = resultado
    inspecao.inspecionado_em = data
    inspecao.metros_reprovados = metros_reprovados
    inspecao.defeito = defeito
    inspecao.inspetor = inspetor
    inspecao.relatorio = relatorio
    inspecao.observacao = observacao
    inspecao.save()

    junta = inspecao.junta
    junta.status = StatusJunta.APROVADA if resultado == ResultadoEND.APROVADO else StatusJunta.REPROVADA
    junta.save(update_fields=["status", "updated_at"])
    registrar_auditoria(usuario, "resultado_end", target_model="JuntaSolda", target_id=junta.pk,
                        detail=f"{junta.codigo}: {inspecao.get_metodo_display()} {resultado}"
                               + (f" ({metros_reprovados} m, {inspecao.get_defeito_display()})" if metros_reprovados else ""))
    return inspecao


def _taxa(reprovado, inspecionado):
    return round(float(reprovado) / float(inspecionado) * 100, 1) if inspecionado else None


def montar_painel_solda(projeto_id=None, area_id=None):
    juntas = JuntaSolda.objects.select_related("area_local", "projeto", "eps")
    if projeto_id:
        juntas = juntas.filter(projeto_id=projeto_id)
    if area_id:
        juntas = juntas.filter(area_local_id=area_id)
    juntas = list(juntas)
    ids = [j.pk for j in juntas]

    soldado = defaultdict(lambda: ZERO)
    por_soldador_metros = defaultdict(lambda: ZERO)
    for jid, sid, metros, reparo in ExecucaoSolda.objects.filter(junta_id__in=ids).values_list(
            "junta_id", "soldador_id", "metros", "reparo"):
        if not reparo:
            soldado[jid] += metros
            por_soldador_metros[sid] += metros

    inspecoes = list(InspecaoEND.objects.filter(junta_id__in=ids).select_related("junta", "junta__area_local")
                     .prefetch_related("soldadores"))
    concluidas = [i for i in inspecoes if i.resultado != ResultadoEND.PENDENTE]

    blocos = defaultdict(lambda: {"juntas": 0, "previsto": ZERO, "soldado": ZERO, "aprovadas": 0, "aguardando": 0,
                                  "reprovadas": 0, "inspecionado": ZERO, "reprovado": ZERO})
    for j in juntas:
        b = blocos[j.area_local]
        b["juntas"] += 1
        b["previsto"] += j.comprimento_m
        b["soldado"] += min(soldado[j.pk], j.comprimento_m)
        b["aprovadas"] += j.status in (StatusJunta.APROVADA, StatusJunta.CONCLUIDA)
        b["aguardando"] += j.status == StatusJunta.AGUARDANDO_END
        b["reprovadas"] += j.status == StatusJunta.REPROVADA
    for i in concluidas:
        b = blocos[i.junta.area_local]
        b["inspecionado"] += i.metros_inspecionados
        b["reprovado"] += i.metros_reprovados

    soldadores = defaultdict(lambda: {"inspecionado": ZERO, "reprovado": ZERO, "ensaios": 0, "reprovacoes": 0})
    for i in concluidas:
        quem = list(i.soldadores.all())
        if not quem:
            continue
        parte = Decimal(len(quem))
        for s in quem:
            d = soldadores[s.pk]
            d["inspecionado"] += i.metros_inspecionados / parte
            d["reprovado"] += i.metros_reprovados / parte
            d["ensaios"] += 1
            d["reprovacoes"] += i.resultado == ResultadoEND.REPROVADO

    ids_soldadores = set(por_soldador_metros) | set(soldadores)
    linhas_soldador = []
    for s in Soldador.objects.filter(Q(pk__in=ids_soldadores) | Q(ativo=True)).select_related("funcionario"):
        d = soldadores.get(s.pk, {"inspecionado": ZERO, "reprovado": ZERO, "ensaios": 0, "reprovacoes": 0})
        taxa = _taxa(d["reprovado"], d["inspecionado"])
        linhas_soldador.append({
            "soldador": s, "metros": por_soldador_metros.get(s.pk, ZERO), "inspecionado": d["inspecionado"],
            "reprovado": d["reprovado"], "ensaios": d["ensaios"], "reprovacoes": d["reprovacoes"], "taxa": taxa,
            "acima_limite": taxa is not None and taxa > LIMITE_TAXA_REPARO,
        })
    linhas_soldador.sort(key=lambda l: (-(l["taxa"] or -1), l["soldador"].sinete))

    linhas_bloco = []
    for area, b in blocos.items():
        taxa = _taxa(b["reprovado"], b["inspecionado"])
        linhas_bloco.append({**b, "area": area, "taxa": taxa,
                             "percentual": round(float(b["soldado"] / b["previsto"]) * 100, 1) if b["previsto"] else 0,
                             "acima_limite": taxa is not None and taxa > LIMITE_TAXA_REPARO})
    linhas_bloco.sort(key=lambda l: l["area"].codigo)

    previsto = sum((j.comprimento_m for j in juntas), ZERO)
    feito = sum((min(soldado[j.pk], j.comprimento_m) for j in juntas), ZERO)
    inspecionado = sum((i.metros_inspecionados for i in concluidas), ZERO)
    reprovado = sum((i.metros_reprovados for i in concluidas), ZERO)
    pendentes = sorted((i for i in inspecoes if i.resultado == ResultadoEND.PENDENTE), key=lambda i: i.solicitado_em)
    hoje = timezone.localdate()
    return {
        "tem_dados": bool(juntas),
        "totais": {
            "juntas": len(juntas), "previsto": previsto, "soldado": feito,
            "percentual": round(float(feito / previsto) * 100, 1) if previsto else 0,
            "aprovadas": sum(j.status in (StatusJunta.APROVADA, StatusJunta.CONCLUIDA) for j in juntas),
            "end_pendentes": len(pendentes),
            "end_atrasados": sum((hoje - i.solicitado_em).days > DIAS_END_ATRASADO for i in pendentes),
            "reprovadas": sum(j.status == StatusJunta.REPROVADA for j in juntas),
            "taxa_reparo": _taxa(reprovado, inspecionado), "inspecionado": inspecionado, "reprovado": reprovado,
        },
        "pendentes": pendentes,
        "reprovadas": [j for j in juntas if j.status == StatusJunta.REPROVADA],
        "por_bloco": linhas_bloco,
        "por_soldador": linhas_soldador,
        "qualificacoes": [s for s in Soldador.objects.filter(ativo=True).select_related("funcionario")
                          if s.situacao_qualificacao != "valida"],
        "limite_taxa": LIMITE_TAXA_REPARO,
        "dias_end_atrasado": DIAS_END_ATRASADO,
    }


def alertas_solda(hoje, projeto_id=None):
    """Alertas no mesmo formato de rdc.services.alertas_service."""
    alertas = []
    pend = InspecaoEND.objects.filter(resultado=ResultadoEND.PENDENTE).select_related("junta", "junta__area_local")
    if projeto_id:
        pend = pend.filter(junta__projeto_id=projeto_id)
    atrasados = [i for i in pend if (hoje - i.solicitado_em).days > DIAS_END_ATRASADO]
    if atrasados:
        exemplos = ", ".join(i.junta.codigo for i in atrasados[:4])
        alertas.append({
            "nivel": "warning", "tipo": "end_atrasado",
            "titulo": f"{len(atrasados)} END aguardando resultado há mais de {DIAS_END_ATRASADO} dias",
            "detalhe": f"Juntas: {exemplos}{'…' if len(atrasados) > 4 else ''}. A montagem seguinte pode ficar travada.",
            "url": "/soldagem/#fila-end", "acao": "Abrir fila de END",
        })
    for s in Soldador.objects.filter(ativo=True).select_related("funcionario"):
        dias = (s.validade_qualificacao - hoje).days
        if dias < 0:
            alertas.append({"nivel": "danger", "tipo": "qualificacao_vencida",
                            "titulo": f"Qualificação vencida: {s.sinete} · {s.funcionario.nome}",
                            "detalhe": f"Venceu em {s.validade_qualificacao:%d/%m/%Y}. O sistema bloqueia novos lançamentos de solda.",
                            "url": f"/soldagem/soldadores/{s.pk}/editar/", "acao": "Atualizar qualificação"})
        elif dias <= 15:
            alertas.append({"nivel": "warning", "tipo": "qualificacao_vencendo",
                            "titulo": f"Qualificação vence em {dias} dia(s): {s.sinete} · {s.funcionario.nome}",
                            "detalhe": f"Validade {s.validade_qualificacao:%d/%m/%Y}. Programe a requalificação.",
                            "url": f"/soldagem/soldadores/{s.pk}/editar/", "acao": "Ver soldador"})
    return alertas
