"""Relatorio fotografico do RDC em PDF (A4, 2 x 3 fotos por pagina)."""
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

NAVY = colors.HexColor("#172432")
ORANGE = colors.HexColor("#f07a12")
MUTED = colors.HexColor("#5b6b7d")
LINE = colors.HexColor("#d5dce4")

MARGEM = 14 * mm
COLUNAS, LINHAS = 2, 3
ALTURA_CABECALHO = 30 * mm
ALTURA_RODAPE = 10 * mm
ALTURA_LEGENDA = 15 * mm
ESPACO = 6 * mm


def _logo_path():
    for base in (Path(settings.BASE_DIR) / "static" / "img", Path(settings.STATIC_ROOT or "") / "img"):
        caminho = base / "dorange-mark.png"
        if caminho.exists():
            return str(caminho)
    return None


def _cabecalho(c, rdc, largura, altura, pagina, total):
    topo = altura - MARGEM
    c.setFillColor(NAVY)
    c.rect(MARGEM, topo - ALTURA_CABECALHO + 6 * mm, largura - 2 * MARGEM, ALTURA_CABECALHO - 6 * mm, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(MARGEM, topo - ALTURA_CABECALHO + 6 * mm, largura - 2 * MARGEM, 1.2 * mm, stroke=0, fill=1)

    x_texto = MARGEM + 6 * mm
    logo = _logo_path()
    if logo:
        c.drawImage(logo, MARGEM + 4 * mm, topo - 20 * mm, 14 * mm, 14 * mm, mask="auto")
        x_texto = MARGEM + 22 * mm

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x_texto, topo - 11 * mm, f"Relatório fotográfico · RDC #{rdc.pk}")
    c.setFont("Helvetica", 8.5)
    area = rdc.area_local.descricao
    naval = getattr(rdc.area_local, "resumo_naval", "")
    linha = f"{rdc.projeto.nome} · {area}{(' (' + naval + ')') if naval else ''} · {rdc.disciplina.nome}"
    c.drawString(x_texto, topo - 16 * mm, linha[:120])
    c.drawString(x_texto, topo - 20.5 * mm, f"{rdc.data:%d/%m/%Y} · Turno {rdc.get_turno_display()}")
    c.setFont("Helvetica", 8)
    c.drawRightString(largura - MARGEM - 5 * mm, topo - 11 * mm, f"Página {pagina} de {total}")


def _rodape(c, largura, gerado_por, gerado_em):
    c.setStrokeColor(LINE)
    c.line(MARGEM, MARGEM + ALTURA_RODAPE - 3 * mm, largura - MARGEM, MARGEM + ALTURA_RODAPE - 3 * mm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    quem = getattr(gerado_por, "username", "") or "Sistema"
    c.drawString(MARGEM, MARGEM + 2 * mm, f"RDC Inteligente · D'OR@NGE · gerado por {quem} em {gerado_em:%d/%m/%Y %H:%M}")


def _celula(c, foto, numero, x, y, w, h):
    """Desenha a foto (mantendo proporcao) dentro da celula e a legenda abaixo."""
    area_img_h = h - ALTURA_LEGENDA
    with foto.imagem.open("rb") as arquivo:
        imagem = ImageReader(BytesIO(arquivo.read()))
    iw, ih = imagem.getSize()
    escala = min(w / iw, area_img_h / ih)
    dw, dh = iw * escala, ih * escala
    dx, dy = x + (w - dw) / 2, y + ALTURA_LEGENDA + (area_img_h - dh) / 2

    c.setFillColor(colors.HexColor("#eef1f5"))
    c.rect(x, y + ALTURA_LEGENDA, w, area_img_h, stroke=0, fill=1)
    c.drawImage(imagem, dx, dy, dw, dh)
    c.setStrokeColor(LINE)
    c.rect(x, y, w, h, stroke=1, fill=0)

    momento = timezone.localtime(foto.momento) if foto.momento else None
    titulo = f"Foto {numero}" + (f" · {momento:%d/%m %H:%M}" if momento else "") + f" · {foto.get_categoria_display()}"
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 2.5 * mm, y + ALTURA_LEGENDA - 4.5 * mm, titulo[:80])

    detalhes = foto.legenda or ""
    if foto.rdc_atividade_id:
        detalhes += f" [Atividade {foto.rdc_atividade.codigo_atividade}]"
    if foto.paralisacao_id:
        detalhes += f" [Paralisação: {foto.paralisacao.get_motivo_display()}]"
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    for i, linha in enumerate(simpleSplit(detalhes.strip() or "Sem legenda.", "Helvetica", 7.5, w - 5 * mm)[:2]):
        c.drawString(x + 2.5 * mm, y + ALTURA_LEGENDA - 8.5 * mm - i * 3.4 * mm, linha)


def gerar_pdf_fotografico(rdc, fotos, *, gerado_por=None, gerado_em=None):
    gerado_em = gerado_em or timezone.localtime()
    buffer = BytesIO()
    largura, altura = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Relatório fotográfico RDC {rdc.pk}")
    c.setAuthor("RDC Inteligente · D'OR@NGE")

    por_pagina = COLUNAS * LINHAS
    total_paginas = (len(fotos) + por_pagina - 1) // por_pagina
    area_w = largura - 2 * MARGEM
    area_h = altura - 2 * MARGEM - ALTURA_CABECALHO - ALTURA_RODAPE
    cel_w = (area_w - (COLUNAS - 1) * ESPACO) / COLUNAS
    cel_h = (area_h - (LINHAS - 1) * ESPACO) / LINHAS
    topo_grade = altura - MARGEM - ALTURA_CABECALHO

    for indice, foto in enumerate(fotos):
        posicao = indice % por_pagina
        if posicao == 0:
            if indice:
                c.showPage()
            pagina = indice // por_pagina + 1
            _cabecalho(c, rdc, largura, altura, pagina, total_paginas)
            _rodape(c, largura, gerado_por, gerado_em)
        col, lin = posicao % COLUNAS, posicao // COLUNAS
        x = MARGEM + col * (cel_w + ESPACO)
        y = topo_grade - (lin + 1) * cel_h - lin * ESPACO
        _celula(c, foto, indice + 1, x, y, cel_w, cel_h)

    c.save()
    return buffer.getvalue()
