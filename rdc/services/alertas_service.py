"""Alertas operacionais do dia: RDC nao lancado, ocorrencias abertas, revisao parada, aceite expirando."""
from datetime import timedelta

from django.utils import timezone

PERIODO_REFERENCIA_DIAS = 7
OCORRENCIA_VELHA_DIAS = 3
REVISAO_PARADA_DIAS = 2


def gerar_alertas(hoje=None, projeto_id=None):
    from rdc.models import RDC, RDCLinkAceite, RDCOcorrencia

    hoje = hoje or timezone.localdate()
    agora = timezone.now()
    alertas = []

    rdcs = RDC.objects.select_related("projeto", "area_local", "disciplina")
    ocorrencias = RDCOcorrencia.objects.exclude(status="encerrada").select_related("rdc", "rdc__area_local", "rdc__projeto")
    links = RDCLinkAceite.objects.filter(usado_em__isnull=True, revogado_em__isnull=True).select_related("rdc", "rdc__area_local")
    if projeto_id:
        rdcs = rdcs.filter(projeto_id=projeto_id)
        ocorrencias = ocorrencias.filter(rdc__projeto_id=projeto_id)
        links = links.filter(rdc__projeto_id=projeto_id)

    # 1) Frentes ativas na ultima semana sem RDC hoje (domingo nao cobra)
    if hoje.weekday() != 6:
        recentes = rdcs.filter(data__gte=hoje - timedelta(days=PERIODO_REFERENCIA_DIAS), data__lt=hoje)
        frentes = {}
        for r in recentes:
            frentes[(r.projeto_id, r.area_local_id, r.disciplina_id)] = r
        com_rdc_hoje = set(rdcs.filter(data=hoje).values_list("projeto_id", "area_local_id", "disciplina_id"))
        for chave, ultimo in sorted(frentes.items(), key=lambda kv: (kv[1].projeto.nome, kv[1].area_local.descricao)):
            if chave not in com_rdc_hoje:
                alertas.append({
                    "nivel": "warning", "tipo": "rdc_pendente",
                    "titulo": f"RDC de hoje não lançado: {ultimo.area_local.descricao} · {ultimo.disciplina.nome}",
                    "detalhe": f"{ultimo.projeto.nome}. Último RDC desta frente: {ultimo.data:%d/%m}.",
                    "url": f"/rdc/{ultimo.pk}/copiar/", "acao": "Copiar o último RDC",
                })

    # 2) Ocorrencias graves abertas e 3) ocorrencias antigas
    for o in ocorrencias.order_by("rdc__data"):
        dias = (hoje - o.rdc.data).days
        if o.gravidade in ("alta", "critica"):
            nivel, titulo = "danger", f"Ocorrência {o.get_gravidade_display().lower()} em aberto: {o.get_tipo_display()}"
        elif dias > OCORRENCIA_VELHA_DIAS:
            nivel, titulo = "warning", f"Ocorrência aberta há {dias} dias: {o.get_tipo_display()}"
        else:
            continue
        alertas.append({
            "nivel": nivel, "tipo": "ocorrencia",
            "titulo": titulo,
            "detalhe": f"{o.rdc.area_local.descricao} · RDC #{o.rdc_id} de {o.rdc.data:%d/%m}. {o.descricao[:90]}",
            "url": f"/rdc/{o.rdc_id}/#ocorrencias", "acao": "Abrir ocorrência",
        })

    # 4) RDC parado em revisao
    for r in rdcs.filter(status="em_revisao", updated_at__lt=agora - timedelta(days=REVISAO_PARADA_DIAS)).order_by("data"):
        alertas.append({
            "nivel": "warning", "tipo": "revisao_parada",
            "titulo": f"RDC #{r.pk} em revisão há mais de {REVISAO_PARADA_DIAS} dias",
            "detalhe": f"{r.area_local.descricao} · {r.disciplina.nome} · {r.data:%d/%m}",
            "url": f"/rdc/{r.pk}/", "acao": "Revisar",
        })

    # 5) Aceite do fiscal expirando sem assinatura
    for l in links.filter(expira_em__gt=agora, expira_em__lte=agora + timedelta(hours=24)):
        alertas.append({
            "nivel": "info", "tipo": "aceite_expirando",
            "titulo": f"Aceite do fiscal expira em menos de 24 h (RDC #{l.rdc_id})",
            "detalhe": f"{l.destinatario or 'Fiscal'} · {l.rdc.area_local.descricao} · expira {timezone.localtime(l.expira_em):%d/%m %H:%M}",
            "url": f"/rdc/{l.rdc_id}/#aceite-fiscal", "acao": "Gerar novo link",
        })

    from soldagem.services import alertas_solda
    alertas.extend(alertas_solda(hoje, projeto_id=projeto_id))

    ordem = {"danger": 0, "warning": 1, "info": 2}
    alertas.sort(key=lambda a: ordem.get(a["nivel"], 3))
    return alertas
