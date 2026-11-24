"""Status do bloco e checklist de liberação para edificação.

Junta o que já existe nos módulos (avanço, solda, punch, ocorrências e RDCs) e responde:
"esse bloco pode subir?". Critério sem dados no bloco não bloqueia (aparece como "não se aplica").
"""
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from cadastros.models import AreaLocal
from planejamento.models import AtividadeCronograma
from rdc.models import RDC, RDCFuncionario, RDCOcorrencia, RDCParalisacao
from rdc.services.avanco_service import montar_avanco

STATUS_RDC_OK = ("aprovado", "fechado")
GRAVIDADES_BLOQUEIAM = ("alta", "critica")


def _criterio(chave, titulo, ok, detalhe, url=""):
    return {"chave": chave, "titulo": titulo, "ok": ok, "detalhe": detalhe, "url": url}


def liberacao_blocos(projeto_id=None, area_id=None, hoje=None):
    """Lista de blocos com indicadores e checklist. Uma consulta agregada por módulo, não por bloco."""
    from punchlist.models import STATUS_EM_ABERTO, PunchItem
    from soldagem.models import InspecaoEND, JuntaSolda, ResultadoEND, StatusJunta

    hoje = hoje or timezone.localdate()
    areas = AreaLocal.objects.select_related("projeto").filter(ativo=True)
    if projeto_id:
        areas = areas.filter(projeto_id=projeto_id)
    if area_id:
        areas = areas.filter(pk=area_id)
    areas = list(areas)
    ids = [a.pk for a in areas]

    avanco = {}
    for pid in {a.projeto_id for a in areas}:
        dados = montar_avanco(hoje, projeto_id=pid)
        for linha in dados["por_area"]:
            avanco[linha["area"].pk] = linha
    tem_cronograma = set(AtividadeCronograma.objects.filter(area_local_id__in=ids).values_list("area_local_id", flat=True))

    juntas = defaultdict(lambda: defaultdict(int))
    for aid, status, n in JuntaSolda.objects.filter(area_local_id__in=ids).values_list("area_local_id", "status").annotate(n=Count("id")):
        juntas[aid][status] = n
    end_pend = dict(InspecaoEND.objects.filter(junta__area_local_id__in=ids, resultado=ResultadoEND.PENDENTE)
                    .values_list("junta__area_local_id").annotate(n=Count("id")))

    punch = defaultdict(lambda: defaultdict(int))
    for aid, cat, n in (PunchItem.objects.filter(area_local_id__in=ids, status__in=STATUS_EM_ABERTO)
                        .values_list("area_local_id", "categoria").annotate(n=Count("id"))):
        punch[aid][cat] = n
    punch_total = dict(PunchItem.objects.filter(area_local_id__in=ids).exclude(status="cancelada")
                       .values_list("area_local_id").annotate(n=Count("id")))

    ocorr = dict(RDCOcorrencia.objects.filter(rdc__area_local_id__in=ids, gravidade__in=GRAVIDADES_BLOQUEIAM)
                 .exclude(status="encerrada").values_list("rdc__area_local_id").annotate(n=Count("id")))
    rdc_abertos = dict(RDC.objects.filter(area_local_id__in=ids, data__lt=hoje).exclude(status__in=STATUS_RDC_OK)
                       .values_list("area_local_id").annotate(n=Count("id")))
    rdc_total = dict(RDC.objects.filter(area_local_id__in=ids).values_list("area_local_id").annotate(n=Count("id")))
    hh = dict(RDCFuncionario.objects.filter(rdc__area_local_id__in=ids).values_list("rdc__area_local_id")
              .annotate(t=Sum("hh_total")))
    hh_perdido = dict(RDCParalisacao.objects.filter(rdc__area_local_id__in=ids).values_list("rdc__area_local_id")
                      .annotate(t=Sum("hh_perdido")))

    blocos = []
    for area in areas:
        aid = area.pk
        av = avanco.get(aid)
        j = juntas.get(aid, {})
        total_juntas = sum(j.values())
        nao_soldadas = j.get(StatusJunta.PLANEJADA, 0) + j.get(StatusJunta.EM_EXECUCAO, 0)
        p = punch.get(aid, {})
        q = f"?projeto={area.projeto_id}&area={aid}"
        criterios = [
            _criterio("avanco", "Avanço físico concluído",
                      None if aid not in tem_cronograma else (av is not None and av["realizado"] >= 99.95),
                      "sem cronograma cadastrado" if aid not in tem_cronograma
                      else f"{str(av['realizado'] if av else 0).replace('.', ',')}% realizado", f"/rdc/avanco/{q}#detalhe"),
            _criterio("solda", "Todas as juntas soldadas",
                      None if not total_juntas else nao_soldadas == 0,
                      "sem juntas cadastradas" if not total_juntas else
                      (f"{nao_soldadas} de {total_juntas} junta(s) faltando" if nao_soldadas else f"{total_juntas} junta(s) soldadas"),
                      f"/soldagem/juntas/?area={aid}"),
            _criterio("end", "Nenhum END pendente",
                      None if not total_juntas else not end_pend.get(aid),
                      "sem juntas cadastradas" if not total_juntas else
                      (f"{end_pend[aid]} ensaio(s) aguardando resultado" if end_pend.get(aid) else "todos os ensaios com resultado"),
                      f"/soldagem/{q}#fila-end"),
            _criterio("reparo", "Nenhuma junta reprovada em aberto",
                      None if not total_juntas else not j.get(StatusJunta.REPROVADA),
                      "sem juntas cadastradas" if not total_juntas else
                      (f"{j[StatusJunta.REPROVADA]} junta(s) aguardando reparo" if j.get(StatusJunta.REPROVADA) else "nenhuma"),
                      f"/soldagem/juntas/?area={aid}&status=reprovada"),
            _criterio("punch", "Nenhuma pendência categoria A",
                      None if not punch_total.get(aid) else not p.get("A"),
                      "sem punch list no bloco" if not punch_total.get(aid) else
                      (f"{p['A']} pendência(s) A em aberto" if p.get("A") else
                       f"{p.get('B', 0) + p.get('C', 0)} pendência(s) B/C podem seguir após a edificação"),
                      f"/punch/?area={aid}&categoria=A"),
            _criterio("seguranca", "Nenhuma ocorrência grave aberta",
                      not ocorr.get(aid),
                      f"{ocorr[aid]} ocorrência(s) alta/crítica sem encerrar" if ocorr.get(aid) else "nenhuma",
                      f"/rdc/blocos/{aid}/#ocorrencias"),
            _criterio("rdc", "RDCs dos dias anteriores fechados",
                      None if not rdc_total.get(aid) else not rdc_abertos.get(aid),
                      "sem RDCs no bloco" if not rdc_total.get(aid) else
                      (f"{rdc_abertos[aid]} RDC(s) ainda em aberto" if rdc_abertos.get(aid) else "todos fechados ou aprovados"),
                      f"/rdc/blocos/{aid}/#rdcs"),
        ]
        aplicaveis = [c for c in criterios if c["ok"] is not None]
        atendidos = sum(1 for c in aplicaveis if c["ok"])
        tem_dados = bool(aplicaveis) and any(c["chave"] != "seguranca" for c in aplicaveis)
        if not tem_dados:
            continue
        liberado = atendidos == len(aplicaveis)
        blocos.append({
            "area": area, "criterios": criterios, "atendidos": atendidos, "aplicaveis": len(aplicaveis),
            "liberado": liberado, "pendencias": [c for c in aplicaveis if not c["ok"]],
            "avanco": av, "juntas": total_juntas, "juntas_ok": j.get(StatusJunta.APROVADA, 0) + j.get(StatusJunta.CONCLUIDA, 0),
            "punch_a": p.get("A", 0), "punch_aberto": sum(p.values()),
            "hh": hh.get(aid) or Decimal("0"), "hh_perdido": hh_perdido.get(aid) or Decimal("0"),
            "rdcs": rdc_total.get(aid, 0),
        })
    blocos.sort(key=lambda b: (b["liberado"], -(b["aplicaveis"] - b["atendidos"]), b["area"].codigo))
    return blocos


def detalhe_bloco(area, hoje=None):
    """Tudo do bloco numa página: checklist + listas curtas de cada módulo."""
    from punchlist.models import STATUS_EM_ABERTO, PunchItem
    from soldagem.services import montar_painel_solda

    hoje = hoje or timezone.localdate()
    resumo = (liberacao_blocos(area_id=area.pk, hoje=hoje) or [None])[0]
    avanco = montar_avanco(hoje, projeto_id=area.projeto_id, area_id=area.pk)
    solda = montar_painel_solda(area_id=area.pk)
    motivos = (RDCParalisacao.objects.filter(rdc__area_local=area).values("motivo")
               .annotate(hh=Sum("hh_perdido"), n=Count("id")).order_by("-hh")[:5])
    from core.choices import MotivoParalisacaoChoices
    rotulos = dict(MotivoParalisacaoChoices.CHOICES)
    return {
        "resumo": resumo,
        "atividades": (avanco["detalhe"] or {}).get("itens", []),
        "solda": solda,
        "punch": list(PunchItem.objects.filter(area_local=area, status__in=STATUS_EM_ABERTO)
                      .order_by("categoria", "prazo", "numero")[:12]),
        "ocorrencias": list(RDCOcorrencia.objects.filter(rdc__area_local=area).exclude(status="encerrada")
                            .select_related("rdc").order_by("-rdc__data")[:8]),
        "paralisacoes": [{"motivo": rotulos.get(m["motivo"], m["motivo"]), "hh": m["hh"], "n": m["n"]} for m in motivos],
        "rdcs": list(RDC.objects.filter(area_local=area).select_related("disciplina").order_by("-data", "-id")[:8]),
    }
