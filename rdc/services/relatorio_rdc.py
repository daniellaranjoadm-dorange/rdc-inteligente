"""PDF completo do RDC do dia: resumo, equipe, atividades, paralisacoes, equipamentos, ocorrencias e aceite."""
from io import BytesIO
from xml.sax.saxutils import escape

from django.db.models import Sum
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from rdc.services.relatorio_fotografico import LINE, MUTED, NAVY, ORANGE, _logo_path

ESTILO = ParagraphStyle("t", fontName="Helvetica", fontSize=8.5, leading=11, textColor=NAVY)
ESTILO_MUTED = ParagraphStyle("m", parent=ESTILO, textColor=MUTED, fontSize=8)
ESTILO_SECAO = ParagraphStyle("s", parent=ESTILO, fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=8, spaceAfter=4)


def _p(texto, estilo=ESTILO):
    return Paragraph(escape(str(texto if texto not in (None, "") else "-")).replace("\n", "<br/>"), estilo)


def _br(valor):
    try:
        return f"{float(valor or 0):.2f}".replace(".", ",")
    except (TypeError, ValueError):
        return str(valor)


def _tabela(cabecalho, linhas, larguras):
    dados = [[_p(c, ParagraphStyle("h", parent=ESTILO, fontName="Helvetica-Bold", textColor=colors.white)) for c in cabecalho]]
    dados += [[c if isinstance(c, Paragraph) else _p(c) for c in linha] for linha in linhas]
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, ORANGE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f5f8")]),
        ("GRID", (0, 1), (-1, -1), 0.25, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _secao(titulo, tabela_ou_texto, vazio):
    itens = [Paragraph(titulo, ESTILO_SECAO)]
    itens.append(tabela_ou_texto if tabela_ou_texto is not None else _p(vazio, ESTILO_MUTED))
    return itens


def gerar_pdf_rdc(rdc, *, gerado_por=None):
    buffer = BytesIO()
    largura_util = A4[0] - 28 * mm
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=34 * mm, bottomMargin=16 * mm, title=f"RDC {rdc.pk}",
                            author="RDC Inteligente · D'OR@NGE")

    hh = rdc.funcionarios.aggregate(t=Sum("hh_total"))["t"] or 0
    hh_perdido = rdc.paralisacoes.aggregate(t=Sum("hh_perdido"))["t"] or 0
    eq = rdc.equipamentos.aggregate(t=Sum("horas_trabalhadas"), p=Sum("horas_paradas"))
    kpis = [
        ("Efetivo", rdc.funcionarios.count()), ("HH trabalhado", _br(hh)), ("HH perdido", _br(hh_perdido)),
        ("Atividades", rdc.atividades.count()), ("Equip. h trab./paradas", f"{_br(eq['t'])} / {_br(eq['p'])}"),
        ("Ocorrências", rdc.ocorrencias.count()),
    ]
    kpi_tab = Table([[_p(k, ESTILO_MUTED) for k, _ in kpis],
                     [Paragraph(f"<b>{escape(str(v))}</b>", ParagraphStyle("k", parent=ESTILO, fontSize=12, leading=15)) for _, v in kpis]],
                    colWidths=[largura_util / len(kpis)] * len(kpis))
    kpi_tab.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f5f8")), ("BOX", (0, 0), (-1, -1), 0.4, LINE)]))

    story = [kpi_tab]
    if rdc.observacoes:
        story += [Spacer(1, 4), _p(f"Observações: {rdc.observacoes}")]

    funcs = list(rdc.funcionarios.select_related("funcao", "equipe").order_by("nome"))
    story += _secao(f"Equipe ({len(funcs)})", _tabela(
        ["Matrícula", "Nome", "Função", "Equipe", "HN", "HE", "HH"],
        [[f.matricula, f.nome, f.funcao or "-", f.equipe or "-", _br(f.hora_normal), _br(f.hora_extra), _br(f.hh_total)] for f in funcs],
        [22 * mm, 52 * mm, 34 * mm, 30 * mm, 14 * mm, 14 * mm, largura_util - 166 * mm],
    ) if funcs else None, "Nenhum funcionário lançado.")

    ativs = list(rdc.atividades.order_by("codigo_atividade"))
    story += _secao("Atividades", _tabela(
        ["Código", "Descrição", "Escopo", "Executado", "Comentário"],
        [[a.codigo_atividade, a.descr_atividade, _br(a.qtd_escopo), _br(a.qtd_executada), a.comentarios] for a in ativs],
        [22 * mm, 70 * mm, 20 * mm, 20 * mm, largura_util - 132 * mm],
    ) if ativs else None, "Nenhuma atividade lançada.")

    pars = list(rdc.paralisacoes.all())
    story += _secao("Paralisações", _tabela(
        ["Motivo", "Responsabilidade", "Período", "Pess.", "HH perdido", "Descrição"],
        [[p.get_motivo_display(), p.get_responsabilidade_display(), f"{p.inicio:%H:%M}–{p.fim:%H:%M}", p.pessoas_afetadas, _br(p.hh_perdido), p.descricao] for p in pars],
        [32 * mm, 30 * mm, 22 * mm, 18 * mm, 20 * mm, largura_util - 122 * mm],
    ) if pars else None, "Nenhuma paralisação.")

    eqs = list(rdc.equipamentos.all())
    story += _secao("Equipamentos", _tabela(
        ["Equipamento", "TAG", "Operador", "Trab.", "Paradas", "Motivo da parada"],
        [[e.get_tipo_display(), e.identificacao, e.operador, _br(e.horas_trabalhadas), _br(e.horas_paradas), e.get_motivo_parada_display()] for e in eqs],
        [34 * mm, 24 * mm, 36 * mm, 16 * mm, 16 * mm, largura_util - 126 * mm],
    ) if eqs else None, "Nenhum equipamento registrado.")

    ocs = list(rdc.ocorrencias.all())
    story += _secao("Ocorrências de segurança e qualidade", _tabela(
        ["Tipo", "Gravidade", "Hora / local", "Descrição e ação", "Situação"],
        [[o.get_tipo_display(), o.get_gravidade_display(), (f"{o.hora:%H:%M} · " if o.hora else "") + (o.local or ""),
          f"{o.descricao}\nação: {o.acao_imediata}" if o.acao_imediata else o.descricao, o.get_status_display()] for o in ocs],
        [32 * mm, 22 * mm, 30 * mm, largura_util - 108 * mm, 24 * mm],
    ) if ocs else None, "Nenhuma ocorrência.")

    aceites = list(rdc.aceites.all())
    story += _secao("Aceite do fiscal", _tabela(
        ["Decisão", "Assinado por", "Data e hora", "Observação"],
        [[a.get_decisao_display(), " · ".join(x for x in (a.nome, a.cargo, a.empresa) if x), f"{timezone.localtime(a.assinado_em):%d/%m/%Y %H:%M}", a.observacao] for a in aceites],
        [30 * mm, 50 * mm, 30 * mm, largura_util - 110 * mm],
    ) if aceites else None, "Sem aceite do fiscal registrado.")

    fotos = rdc.fotos.count()
    if fotos:
        story += [Spacer(1, 6), _p(f"Este RDC tem {fotos} foto(s). Veja o relatório fotográfico no sistema.", ESTILO_MUTED)]

    quem = getattr(gerado_por, "username", "") or "Sistema"
    emitido = timezone.localtime()

    def cabecalho(c, d):
        larg, alt = A4
        topo = alt - 10 * mm
        c.saveState()
        c.setFillColor(NAVY); c.rect(14 * mm, topo - 20 * mm, larg - 28 * mm, 20 * mm, stroke=0, fill=1)
        c.setFillColor(ORANGE); c.rect(14 * mm, topo - 20 * mm, larg - 28 * mm, 1.1 * mm, stroke=0, fill=1)
        x = 20 * mm
        logo = _logo_path()
        if logo:
            c.drawImage(logo, 17 * mm, topo - 17 * mm, 13 * mm, 13 * mm, mask="auto"); x = 34 * mm
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 12.5)
        c.drawString(x, topo - 8.5 * mm, f"RDC #{rdc.pk} · Relatório Diário de Campo")
        c.setFont("Helvetica", 8.5)
        area = rdc.area_local.descricao + (f" ({rdc.area_local.resumo_naval})" if rdc.area_local.resumo_naval else "")
        c.drawString(x, topo - 13.5 * mm, f"{rdc.projeto.nome} · {area} · {rdc.disciplina.nome}"[:115])
        c.drawString(x, topo - 17.5 * mm, f"{rdc.data:%d/%m/%Y} · Turno {rdc.get_turno_display()} · Status: {rdc.status_workflow_label}")
        c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
        c.drawString(14 * mm, 8 * mm, f"RDC Inteligente · D'OR@NGE · emitido por {quem} em {emitido:%d/%m/%Y %H:%M}")
        c.drawRightString(larg - 14 * mm, 8 * mm, f"Página {d.page}")
        c.restoreState()

    doc.build(story, onFirstPage=cabecalho, onLaterPages=cabecalho)
    return buffer.getvalue()
