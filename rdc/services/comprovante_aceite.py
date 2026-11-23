"""Comprovante de aceite do fiscal em PDF (1 pagina A4)."""
from io import BytesIO

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

from rdc.services.relatorio_fotografico import LINE, MARGEM, MUTED, NAVY, ORANGE, _logo_path

COR_DECISAO = {"aprovado": colors.HexColor("#166534"), "ressalvas": colors.HexColor("#92400e"), "reprovado": colors.HexColor("#991b1b")}
ROTULOS = [
    ("funcionarios", "Efetivo"), ("hh_trabalhado", "HH trabalhado"), ("atividades", "Atividades"),
    ("paralisacoes", "Paralisações"), ("hh_perdido", "HH perdido"), ("fotos", "Fotos"), ("status", "Status do RDC"),
]


STATUS = {"rascunho": "Em elaboração", "pre_preenchido": "Pré-preenchido", "em_revisao": "Em revisão",
          "aprovado": "Aprovado", "fechado": "Fechado"}


def _exibir(chave, valor):
    """So formata para leitura; o retrato guardado (base do codigo de verificacao) nao muda."""
    if chave == "status":
        return STATUS.get(str(valor), str(valor))
    if chave in ("hh_trabalhado", "hh_perdido"):
        return str(valor).replace(".", ",")
    return str(valor)


def gerar_pdf_comprovante(aceite, *, gerado_por=None):
    rdc = aceite.rdc
    buffer = BytesIO()
    largura, altura = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Comprovante de aceite RDC {rdc.pk}")

    # Cabecalho
    topo = altura - MARGEM
    c.setFillColor(NAVY)
    c.rect(MARGEM, topo - 24 * mm, largura - 2 * MARGEM, 24 * mm, stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.rect(MARGEM, topo - 24 * mm, largura - 2 * MARGEM, 1.2 * mm, stroke=0, fill=1)
    x = MARGEM + 6 * mm
    logo = _logo_path()
    if logo:
        c.drawImage(logo, MARGEM + 4 * mm, topo - 19 * mm, 14 * mm, 14 * mm, mask="auto")
        x = MARGEM + 22 * mm
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, topo - 11 * mm, f"Comprovante de aceite · RDC #{rdc.pk}")
    c.setFont("Helvetica", 9)
    c.drawString(x, topo - 17 * mm, f"{rdc.projeto.nome} · {rdc.area_local.descricao} · {rdc.disciplina.nome} · {rdc.data:%d/%m/%Y} ({rdc.get_turno_display()})"[:110])

    y = topo - 36 * mm
    c.setFillColor(COR_DECISAO.get(aceite.decisao, NAVY))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGEM, y, aceite.get_decisao_display().upper())

    assinado = timezone.localtime(aceite.assinado_em)
    linhas = [
        ("Assinado por", aceite.nome),
        ("Cargo / empresa", " · ".join(p for p in (aceite.cargo, aceite.empresa) if p) or "-"),
        ("Data e hora", f"{assinado:%d/%m/%Y %H:%M:%S} (horário de Brasília)"),
        ("IP de origem", aceite.ip or "-"),
    ]
    y -= 10 * mm
    for rotulo, valor in linhas:
        c.setFillColor(MUTED); c.setFont("Helvetica", 8.5); c.drawString(MARGEM, y, rotulo)
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 10); c.drawString(MARGEM + 38 * mm, y, str(valor)[:90])
        y -= 6.5 * mm

    if aceite.observacao:
        y -= 2 * mm
        c.setFillColor(MUTED); c.setFont("Helvetica", 8.5); c.drawString(MARGEM, y, "Observações")
        c.setFillColor(NAVY); c.setFont("Helvetica", 9.5)
        for linha in simpleSplit(aceite.observacao, "Helvetica", 9.5, largura - 2 * MARGEM - 38 * mm)[:8]:
            c.drawString(MARGEM + 38 * mm, y, linha); y -= 5 * mm
        y -= 2 * mm

    # Retrato do RDC no momento da assinatura
    y -= 4 * mm
    c.setStrokeColor(LINE); c.line(MARGEM, y, largura - MARGEM, y); y -= 7 * mm
    c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 10.5); c.drawString(MARGEM, y, "Números do RDC no momento da assinatura")
    y -= 7 * mm
    col_w = (largura - 2 * MARGEM) / 4
    for i, (chave, rotulo) in enumerate(ROTULOS):
        cx, cy = MARGEM + (i % 4) * col_w, y - (i // 4) * 13 * mm
        c.setFillColor(MUTED); c.setFont("Helvetica", 8); c.drawString(cx, cy, rotulo)
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 12); c.drawString(cx, cy - 5.5 * mm, _exibir(chave, aceite.retrato.get(chave, "-")))
    y -= 30 * mm

    # Assinatura
    c.setFillColor(MUTED); c.setFont("Helvetica", 8.5); c.drawString(MARGEM, y, "Assinatura")
    y -= 3 * mm
    caixa_w, caixa_h = 90 * mm, 34 * mm
    c.setStrokeColor(LINE); c.rect(MARGEM, y - caixa_h, caixa_w, caixa_h, stroke=1, fill=0)
    with aceite.assinatura.open("rb") as arquivo:
        img = ImageReader(BytesIO(arquivo.read()))
    iw, ih = img.getSize()
    esc = min((caixa_w - 6 * mm) / iw, (caixa_h - 6 * mm) / ih)
    c.drawImage(img, MARGEM + 3 * mm, y - caixa_h + 3 * mm, iw * esc, ih * esc, mask="auto")
    c.setFillColor(NAVY); c.setFont("Helvetica", 9)
    c.drawString(MARGEM, y - caixa_h - 5 * mm, aceite.nome)
    y -= caixa_h + 16 * mm

    # Verificacao
    c.setFillColor(MUTED); c.setFont("Helvetica", 8)
    c.drawString(MARGEM, y, "Código de verificação (SHA-256 dos números acima):")
    c.setFont("Courier", 8); c.setFillColor(NAVY)
    c.drawString(MARGEM, y - 4.5 * mm, aceite.hash_retrato)
    c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
    c.drawString(MARGEM, y - 10 * mm, "Se os números do RDC forem alterados depois, o código calculado deixa de bater com este.")

    quem = getattr(gerado_por, "username", "") or "Sistema"
    c.setStrokeColor(LINE); c.line(MARGEM, MARGEM + 7 * mm, largura - MARGEM, MARGEM + 7 * mm)
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGEM, MARGEM + 2 * mm, f"RDC Inteligente · D'OR@NGE · emitido por {quem} em {timezone.localtime():%d/%m/%Y %H:%M}")
    c.save()
    return buffer.getvalue()
