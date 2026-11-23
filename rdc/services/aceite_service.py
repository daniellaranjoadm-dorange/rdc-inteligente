"""Aceite do fiscal: link de uso unico, retrato do RDC, assinatura desenhada e registro."""
import base64
import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from core.audit import registrar_auditoria

DIAS_VALIDADE_PADRAO = 7
TAMANHO_MAX_ASSINATURA = 600 * 1024
MIN_PIXELS_TRACO = 150  # abaixo disso a "assinatura" e so um ponto ou esta em branco


def criar_link(rdc, *, usuario, destinatario="", dias=DIAS_VALIDADE_PADRAO):
    from rdc.models import RDCLinkAceite

    link = RDCLinkAceite.objects.create(
        rdc=rdc,
        destinatario=(destinatario or "").strip()[:120],
        expira_em=timezone.now() + timedelta(days=dias),
        criado_por=usuario,
    )
    registrar_auditoria(usuario, "gerar_link_aceite", target_model="RDC", target_id=rdc.pk,
                        detail=f"Para: {link.destinatario or '-'}; validade {dias} dia(s)")
    return link


def retrato_rdc(rdc):
    """Numeros que o fiscal viu e assinou. Ordem e formato fixos para o hash ser reprodutivel."""
    hh = rdc.funcionarios.aggregate(t=Sum("hh_total"))["t"] or Decimal("0")
    hh_perdido = rdc.paralisacoes.aggregate(t=Sum("hh_perdido"))["t"] or Decimal("0")
    return {
        "rdc": rdc.pk,
        "projeto": rdc.projeto.codigo,
        "area": rdc.area_local.codigo,
        "disciplina": rdc.disciplina.nome,
        "data": rdc.data.isoformat(),
        "turno": rdc.turno,
        "status": rdc.status,
        "funcionarios": rdc.funcionarios.count(),
        "hh_trabalhado": f"{Decimal(hh):.2f}",
        "atividades": rdc.atividades.count(),
        "paralisacoes": rdc.paralisacoes.count(),
        "hh_perdido": f"{Decimal(hh_perdido):.2f}",
        "fotos": rdc.fotos.count(),
    }


def hash_do_retrato(retrato):
    bruto = json.dumps(retrato, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def assinatura_de_data_url(data_url):
    """Converte o desenho do canvas (data:image/png;base64,...) em arquivo PNG valido."""
    prefixo = "data:image/png;base64,"
    if not data_url or not data_url.startswith(prefixo):
        raise ValidationError("Assine no quadro antes de enviar.")
    try:
        bruto = base64.b64decode(data_url[len(prefixo):], validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValidationError("Assinatura inválida. Limpe o quadro e assine de novo.")
    if len(bruto) > TAMANHO_MAX_ASSINATURA:
        raise ValidationError("Assinatura muito grande. Limpe o quadro e assine de novo.")
    try:
        img = Image.open(BytesIO(bruto))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise ValidationError("Assinatura inválida. Limpe o quadro e assine de novo.")
    if img.format != "PNG":
        raise ValidationError("Assinatura inválida.")

    alfa = img.convert("RGBA").getchannel("A")
    tracos = sum(1 for valor in alfa.getdata() if valor > 40)
    if tracos < MIN_PIXELS_TRACO:
        raise ValidationError("A assinatura está em branco. Assine com o dedo ou o mouse no quadro.")
    return ContentFile(bruto)


@transaction.atomic
def registrar_aceite(link_id, *, decisao, nome, cargo, empresa, observacao, assinatura_arquivo, ip, navegador):
    """Grava o aceite e marca o link como usado. O bloqueio da linha impede dois aceites no mesmo link."""
    from rdc.models import RDCAceite, RDCAuditoria, RDCLinkAceite

    link = RDCLinkAceite.objects.select_for_update().select_related("rdc").get(pk=link_id)
    if not link.ativo:
        raise ValidationError("Este link não está mais disponível (já usado, revogado ou expirado).")

    rdc = link.rdc
    retrato = retrato_rdc(rdc)
    aceite = RDCAceite(
        rdc=rdc, link=link, decisao=decisao, nome=nome.strip(), cargo=cargo.strip(), empresa=empresa.strip(),
        observacao=observacao.strip(), ip=ip or None, navegador=(navegador or "")[:255],
        retrato=retrato, hash_retrato=hash_do_retrato(retrato), assinado_em=timezone.now(),
    )
    aceite.assinatura.save("assinatura.png", assinatura_arquivo, save=False)
    aceite.save()

    link.usado_em = aceite.assinado_em
    link.save(update_fields=["usado_em", "updated_at"])

    resumo = f"Aceite do fiscal: {aceite.get_decisao_display()} por {aceite.nome}"
    RDCAuditoria.objects.create(rdc=rdc, usuario=None, acao="aceite_fiscal", secao="aceite",
                                resumo=resumo[:255], detalhe=aceite.observacao)
    registrar_auditoria(None, "aceite_fiscal", target_model="RDC", target_id=rdc.pk,
                        detail=f"{resumo}{(' (' + aceite.empresa + ')') if aceite.empresa else ''}")
    return aceite
