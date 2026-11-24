"""Regras do punch list: abrir, resolver, verificar, cancelar, e indicadores."""
from collections import defaultdict
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from cadastros.models import Projeto
from core.audit import registrar_auditoria
from punchlist.models import STATUS_EM_ABERTO, Categoria, PunchFoto, PunchItem, Status
from rdc.services.foto_service import processar_foto

MAX_FOTOS = 6


def _salvar_fotos(item, arquivos, momento, usuario):
    arquivos = [a for a in (arquivos or []) if a]
    if len(arquivos) > MAX_FOTOS:
        raise ValidationError(f"Envie no máximo {MAX_FOTOS} fotos por vez.")
    preparadas = [processar_foto(a) for a in arquivos]  # valida todas antes de gravar
    for dados in preparadas:
        foto = PunchFoto(item=item, momento=momento, criado_por=usuario)
        foto.imagem.save("f.jpg", dados["imagem"], save=False)
        foto.miniatura.save("m.jpg", dados["miniatura"], save=False)
        foto.save()
    return len(preparadas)


@transaction.atomic
def abrir_item(*, projeto, area_local, descricao, categoria, usuario=None, fotos=None, **campos):
    if area_local.projeto_id != projeto.pk:
        raise ValidationError("Este bloco/área é de outro projeto.")
    if not (descricao or "").strip():
        raise ValidationError("Descreva a pendência.")
    Projeto.objects.select_for_update(of=("self",)).get(pk=projeto.pk)  # numeração sem corrida
    numero = (PunchItem.objects.filter(projeto=projeto).aggregate(m=Max("numero"))["m"] or 0) + 1
    item = PunchItem.objects.create(projeto=projeto, area_local=area_local, descricao=descricao.strip(),
                                    categoria=categoria, numero=numero, aberta_por=usuario, **campos)
    _salvar_fotos(item, fotos, PunchFoto.Momento.ABERTURA, usuario)
    registrar_auditoria(usuario, "abrir_punch", target_model="PunchItem", target_id=item.pk,
                        detail=f"{item.codigo} ({item.categoria}) {area_local.codigo}: {item.descricao[:80]}")
    return item


@transaction.atomic
def iniciar_item(item, usuario=None):
    if item.status != Status.ABERTA:
        raise ValidationError("Só uma pendência aberta pode ser colocada em andamento.")
    item.status = Status.EM_ANDAMENTO
    item.save(update_fields=["status", "updated_at"])
    return item


@transaction.atomic
def resolver_item(item, *, nota="", fotos=None, usuario=None):
    if item.status not in (Status.ABERTA, Status.EM_ANDAMENTO):
        raise ValidationError("Esta pendência não está aberta.")
    fotos = [f for f in (fotos or []) if f]
    if not (nota or "").strip() and not fotos:
        raise ValidationError("Informe o que foi feito ou anexe uma foto da correção.")
    _salvar_fotos(item, fotos, PunchFoto.Momento.RESOLUCAO, usuario)
    item.status = Status.AGUARDANDO_VERIFICACAO
    item.nota_resolucao = (nota or "").strip()
    item.resolvida_em = timezone.now()
    item.resolvida_por = usuario
    item.save()
    registrar_auditoria(usuario, "resolver_punch", target_model="PunchItem", target_id=item.pk, detail=item.codigo)
    return item


@transaction.atomic
def verificar_item(item, *, aprovado, nota="", usuario=None):
    if item.status != Status.AGUARDANDO_VERIFICACAO:
        raise ValidationError("Só dá para verificar uma pendência marcada como resolvida.")
    if not aprovado and not (nota or "").strip():
        raise ValidationError("Explique por que a correção não foi aceita.")
    item.nota_verificacao = (nota or "").strip()
    if aprovado:
        item.status = Status.FECHADA
        item.fechada_em = timezone.now()
        item.fechada_por = usuario
    else:
        item.status = Status.EM_ANDAMENTO
        item.reaberturas += 1
    item.save()
    registrar_auditoria(usuario, "verificar_punch", target_model="PunchItem", target_id=item.pk,
                        detail=f"{item.codigo}: {'aceita' if aprovado else 'reaberta'}")
    return item


@transaction.atomic
def cancelar_item(item, *, motivo, usuario=None):
    if not item.em_aberto:
        raise ValidationError("Esta pendência já foi encerrada.")
    if not (motivo or "").strip():
        raise ValidationError("Informe o motivo do cancelamento.")
    item.status = Status.CANCELADA
    item.nota_verificacao = motivo.strip()
    item.fechada_em = timezone.now()
    item.fechada_por = usuario
    item.save()
    registrar_auditoria(usuario, "cancelar_punch", target_model="PunchItem", target_id=item.pk, detail=item.codigo)
    return item


def montar_painel_punch(projeto_id=None, area_id=None, hoje=None):
    hoje = hoje or timezone.localdate()
    itens = PunchItem.objects.select_related("area_local", "projeto", "disciplina", "responsavel_empresa")
    if projeto_id:
        itens = itens.filter(projeto_id=projeto_id)
    if area_id:
        itens = itens.filter(area_local_id=area_id)
    itens = list(itens)
    abertos = [i for i in itens if i.em_aberto]
    fechados = [i for i in itens if i.status == Status.FECHADA]
    semana = timezone.now() - timedelta(days=7)

    blocos = defaultdict(lambda: {"A": 0, "B": 0, "C": 0, "vencidas": 0, "verificar": 0, "fechadas": 0, "total": 0})
    for i in itens:
        b = blocos[i.area_local]
        if i.status == Status.CANCELADA:
            continue
        b["total"] += 1
        if i.em_aberto:
            b[i.categoria] += 1
            b["vencidas"] += i.vencida
            b["verificar"] += i.status == Status.AGUARDANDO_VERIFICACAO
        else:
            b["fechadas"] += 1
    linhas = []
    for area, b in blocos.items():
        abertos_bloco = b["A"] + b["B"] + b["C"]
        linhas.append({**b, "area": area, "abertas": abertos_bloco, "liberado": b["A"] == 0,
                       "percentual": round(b["fechadas"] / b["total"] * 100) if b["total"] else 100})
    linhas.sort(key=lambda l: (-l["A"], -l["vencidas"], l["area"].codigo))

    tempos = [(i.fechada_em - i.created_at).days for i in fechados if i.fechada_em]
    return {
        "tem_dados": bool(itens),
        "totais": {
            "abertas": len(abertos),
            "categoria_a": sum(i.categoria == Categoria.A for i in abertos),
            "vencidas": sum(i.vencida for i in abertos),
            "verificar": sum(i.status == Status.AGUARDANDO_VERIFICACAO for i in abertos),
            "fechadas_semana": sum(1 for i in fechados if i.fechada_em and i.fechada_em >= semana),
            "fechadas": len(fechados),
            "tempo_medio": round(sum(tempos) / len(tempos), 1) if tempos else None,
            "reabertas": sum(i.reaberturas > 0 for i in itens),
        },
        "por_bloco": linhas,
    }


def alertas_punch(hoje, projeto_id=None):
    qs = PunchItem.objects.filter(status__in=STATUS_EM_ABERTO).select_related("area_local")
    if projeto_id:
        qs = qs.filter(projeto_id=projeto_id)
    itens = list(qs)
    alertas = []
    cat_a = [i for i in itens if i.categoria == Categoria.A]
    if cat_a:
        blocos = sorted({i.area_local.codigo for i in cat_a})
        alertas.append({
            "nivel": "danger", "tipo": "punch_categoria_a",
            "titulo": f"{len(cat_a)} pendência(s) categoria A em aberto",
            "detalhe": f"Impedem concluir ou testar: blocos {', '.join(blocos[:6])}{'…' if len(blocos) > 6 else ''}.",
            "url": "/punch/?categoria=A", "acao": "Ver pendências A",
        })
    vencidas = [i for i in itens if i.prazo and i.prazo < hoje]
    if vencidas:
        alertas.append({
            "nivel": "warning", "tipo": "punch_vencida",
            "titulo": f"{len(vencidas)} pendência(s) do punch list com prazo vencido",
            "detalhe": "Cobre os responsáveis ou renegocie o prazo.",
            "url": "/punch/?situacao=vencidas", "acao": "Ver vencidas",
        })
    verificar = [i for i in itens if i.status == Status.AGUARDANDO_VERIFICACAO]
    if verificar:
        alertas.append({
            "nivel": "info", "tipo": "punch_verificar",
            "titulo": f"{len(verificar)} correção(ões) aguardando verificação do CQ",
            "detalhe": "O executante marcou como resolvido; falta conferir no local.",
            "url": "/punch/?status=aguardando_verificacao", "acao": "Verificar",
        })
    return alertas
