"""Relatório semanal ao armador/fiscal: avanço (curva S), blocos, HH, solda, punch e ocorrências da semana."""
from datetime import datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.db.models import Count, Sum
from django.utils import timezone
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.choices import MotivoParalisacaoChoices
from rdc.models import RDC, RDCFuncionario, RDCOcorrencia, RDCParalisacao
from rdc.services.avanco_service import montar_avanco
from rdc.services.bloco_service import liberacao_blocos
from rdc.services.relatorio_fotografico import LINE, MUTED, NAVY, ORANGE, _logo_path
from rdc.services.relatorio_rdc import ESTILO, ESTILO_MUTED, ESTILO_SECAO, _p, _tabela

VERDE, VERMELHO = colors.HexColor("#15803d"), colors.HexColor("#b42318")
ESTILO_DESTAQUE = ParagraphStyle("d", parent=ESTILO, fontSize=9.5, leading=13.5, leftIndent=8, bulletIndent=0)


def _num(v, casas=1):
    return f"{float(v or 0):.{casas}f}".replace(".", ",")


def _pp(v):
    return ("+" if v > 0 else "") + _num(v) + " pp"


def periodo_da_semana(fim=None):
    """Semana de 7 dias terminando em `fim` (padrão: hoje)."""
    fim = fim or timezone.localdate()
    return fim - timedelta(days=6), fim


def dados_semana(projeto, fim=None):
    from punchlist.models import STATUS_EM_ABERTO, PunchItem
    from soldagem.models import ExecucaoSolda, InspecaoEND, ResultadoEND

    inicio, fim = periodo_da_semana(fim)
    ini_dt = timezone.make_aware(datetime.combine(inicio, time.min))
    fim_dt = timezone.make_aware(datetime.combine(fim, time.max))
    av = montar_avanco(fim, projeto_id=projeto.pk)
    av_antes = montar_avanco(inicio - timedelta(days=1), projeto_id=projeto.pk)
    blocos = liberacao_blocos(projeto_id=projeto.pk, hoje=fim + timedelta(days=1))

    rdcs = RDC.objects.filter(projeto=projeto, data__range=(inicio, fim))
    hh = RDCFuncionario.objects.filter(rdc__in=rdcs).aggregate(t=Sum("hh_total"))["t"] or Decimal("0")
    paral = RDCParalisacao.objects.filter(rdc__in=rdcs)
    hh_perdido = paral.aggregate(t=Sum("hh_perdido"))["t"] or Decimal("0")
    rotulos = dict(MotivoParalisacaoChoices.CHOICES)
    motivos = [{"motivo": rotulos.get(m["motivo"], m["motivo"]), "hh": m["t"], "n": m["n"]} for m in
               paral.values("motivo").annotate(t=Sum("hh_perdido"), n=Count("id")).order_by("-t")[:5]]

    exec_semana = ExecucaoSolda.objects.filter(junta__projeto=projeto, data__range=(inicio, fim))
    metros_soldados = exec_semana.filter(reparo=False).aggregate(t=Sum("metros"))["t"] or Decimal("0")
    ensaios = InspecaoEND.objects.filter(junta__projeto=projeto, inspecionado_em__range=(inicio, fim))
    insp = ensaios.aggregate(t=Sum("metros_inspecionados"))["t"] or Decimal("0")
    repr_ = ensaios.aggregate(t=Sum("metros_reprovados"))["t"] or Decimal("0")
    end_pendentes = InspecaoEND.objects.filter(junta__projeto=projeto, resultado=ResultadoEND.PENDENTE).count()

    punch = PunchItem.objects.filter(projeto=projeto)
    abertos = punch.filter(status__in=STATUS_EM_ABERTO)
    punch_info = {
        "abertas_semana": punch.filter(created_at__range=(ini_dt, fim_dt)).count(),
        "fechadas_semana": punch.filter(status="fechada", fechada_em__range=(ini_dt, fim_dt)).count(),
        "em_aberto": abertos.count(),
        "A": abertos.filter(categoria="A").count(),
        "vencidas": abertos.filter(prazo__lt=fim).count(),
    }
    ocorrencias = list(RDCOcorrencia.objects.filter(rdc__projeto=projeto, rdc__data__range=(inicio, fim))
                       .select_related("rdc", "rdc__area_local").order_by("rdc__data"))

    total, total_antes = av.get("total") or {}, av_antes.get("total") or {}
    destaques = []
    if total:
        destaques.append(
            f"Avanço da semana: {_pp(total['realizado'] - total_antes.get('realizado', 0))} realizado contra "
            f"{_pp(total['previsto'] - total_antes.get('previsto', 0))} previsto. Acumulado {_num(total['realizado'])}% "
            f"× {_num(total['previsto'])}% previsto (desvio {_pp(total['desvio'])}, IDP {str(total['spi']).replace('.', ',') if total['spi'] is not None else '-'}).")
        pior = min(av["por_area"], key=lambda l: l["desvio"], default=None)
        if pior and pior["desvio"] < -5:
            destaques.append(f"Bloco mais atrasado: {pior['codigo']} ({_pp(pior['desvio'])}).")
    liberados = [b for b in blocos if b["liberado"]]
    destaques.append(f"Blocos liberados para edificação: {len(liberados)} de {len(blocos)}"
                     + (f" ({', '.join(b['area'].codigo for b in liberados)})." if liberados else "."))
    if motivos:
        destaques.append(f"Principal causa de HH perdido: {motivos[0]['motivo'].lower()} ({_num(motivos[0]['hh'], 0)} HH).")
    if insp:
        destaques.append(f"Solda: {_num(metros_soldados, 0)} m soldados, {_num(insp, 0)} m ensaiados, taxa de reparo da semana "
                         f"{_num(repr_ / insp * 100)}%. {end_pendentes} END aguardando resultado.")
    if punch_info["A"]:
        destaques.append(f"Punch list: {punch_info['A']} pendência(s) categoria A em aberto travam a liberação de blocos.")
    graves = [o for o in ocorrencias if o.gravidade in ("alta", "critica")]
    if graves:
        destaques.append(f"Segurança/qualidade: {len(graves)} ocorrência(s) de gravidade alta ou crítica na semana.")

    return {
        "projeto": projeto, "inicio": inicio, "fim": fim, "avanco": av, "avanco_antes": av_antes, "blocos": blocos,
        "rdcs": rdcs.count(), "hh": hh, "hh_perdido": hh_perdido,
        "pct_perdido": float(hh_perdido / (hh + hh_perdido) * 100) if (hh + hh_perdido) else 0, "motivos": motivos,
        "solda": {"metros": metros_soldados, "inspecionado": insp, "reprovado": repr_, "pendentes": end_pendentes,
                  "taxa": float(repr_ / insp * 100) if insp else None},
        "punch": punch_info, "ocorrencias": ocorrencias, "destaques": destaques,
    }


def _grafico_curva(curva, fim, largura):
    pontos = [p for p in curva if p["data"]]
    if len(pontos) < 2:
        return None
    base = pontos[0]["data"]
    prev = [((p["data"] - base).days, p["previsto"]) for p in pontos]
    real = [((p["data"] - base).days, p["realizado"]) for p in pontos if p["realizado"] is not None]
    altura = 62 * mm
    d = Drawing(largura, altura)
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 12 * mm, 8 * mm, largura - 16 * mm, altura - 14 * mm
    lp.data = [prev] + ([real] if len(real) > 1 else [])
    lp.lines[0].strokeColor, lp.lines[0].strokeWidth, lp.lines[0].strokeDashArray = MUTED, 1.4, (4, 3)
    if len(lp.data) > 1:
        lp.lines[1].strokeColor, lp.lines[1].strokeWidth = ORANGE, 2.2
    lp.yValueAxis.valueMin, lp.yValueAxis.valueMax, lp.yValueAxis.valueStep = 0, 100, 25
    lp.yValueAxis.labelTextFormat = "%d%%"
    lp.yValueAxis.labels.fontSize = lp.xValueAxis.labels.fontSize = 7
    total_dias = prev[-1][0] or 1
    passo = max(7, (total_dias // 6 // 7) * 7 or 7)
    lp.xValueAxis.valueMin, lp.xValueAxis.valueMax, lp.xValueAxis.valueStep = 0, total_dias, passo
    lp.xValueAxis.labelTextFormat = lambda v: (base + timedelta(days=int(v))).strftime("%d/%m")
    lp.yValueAxis.gridStrokeColor, lp.yValueAxis.visibleGrid = LINE, 1
    d.add(lp)
    d.add(String(largura - 4 * mm, altura - 4 * mm, "— previsto   — realizado", fontSize=7, fillColor=MUTED, textAnchor="end"))
    return d


def gerar_pdf_semanal(projeto, fim=None, *, gerado_por=None):
    dados = dados_semana(projeto, fim)
    buffer = BytesIO()
    larg = A4[0] - 28 * mm
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=34 * mm,
                            bottomMargin=16 * mm, title=f"Relatório semanal {projeto.nome}",
                            author="RDC Inteligente · D'OR@NGE")
    story = []
    total = dados["avanco"].get("total")

    # Indicadores da semana
    cartoes = [
        ("Avanço realizado", f"{_num(total['realizado'])}%" if total else "-", f"previsto {_num(total['previsto'])}%" if total else "sem cronograma"),
        ("Desvio", _pp(total["desvio"]) if total else "-", total["situacao_label"] if total else ""),
        ("HH da semana", _num(dados["hh"], 0), f"{_num(dados['hh_perdido'], 0)} HH perdidos ({_num(dados['pct_perdido'])}%)"),
        ("Taxa de reparo", f"{_num(dados['solda']['taxa'])}%" if dados["solda"]["taxa"] is not None else "-", f"{dados['solda']['pendentes']} END pendente(s)"),
        ("Punch em aberto", str(dados["punch"]["em_aberto"]), f"{dados['punch']['A']} categoria A · {dados['punch']['vencidas']} vencida(s)"),
    ]
    rot = ParagraphStyle("kr", parent=ESTILO, fontSize=6.8, leading=8.5, textColor=MUTED)
    val = ParagraphStyle("kv", parent=ESTILO, fontName="Helvetica-Bold", fontSize=14, leading=17)
    sub = ParagraphStyle("ks", parent=ESTILO, fontSize=7, leading=9, textColor=MUTED)
    k = Table([[[Paragraph(t.upper(), rot), Paragraph(v, val), Paragraph(s, sub)] for t, v, s in cartoes]],
              colWidths=[larg / 5] * 5)
    k.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.4, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                           ("LINEABOVE", (0, 0), (-1, 0), 2, ORANGE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [k, Spacer(1, 6), Paragraph("Destaques da semana", ESTILO_SECAO)]
    story += [Paragraph(f"• {d}", ESTILO_DESTAQUE) for d in dados["destaques"]] or [_p("Sem lançamentos na semana.", ESTILO_MUTED)]

    grafico = _grafico_curva(dados["avanco"].get("curva") or [], dados["fim"], larg)
    if grafico:
        story += [KeepTogether([Paragraph("Curva S do projeto", ESTILO_SECAO), grafico])]

    if dados["avanco"].get("por_area"):
        liberacao = {b["area"].pk: b for b in dados["blocos"]}
        antes = {l["area"].pk: l for l in dados["avanco_antes"].get("por_area", [])}
        linhas = []
        for l in sorted(dados["avanco"]["por_area"], key=lambda x: x["codigo"]):
            b = liberacao.get(l["area"].pk)
            delta = l["realizado"] - antes.get(l["area"].pk, {}).get("realizado", 0)
            falta = "; ".join(c["titulo"][0].lower() + c["titulo"][1:] for c in (b["pendencias"] if b else [])[:2])
            linhas.append([l["codigo"], l["area"].casco or "-", f"{_num(l['previsto'])}%", f"{_num(l['realizado'])}%",
                           _pp(delta), _pp(l["desvio"]),
                           Paragraph(f"<font color='{'#15803d' if b and b['liberado'] else '#b42318'}'><b>"
                                     f"{'Liberado' if b and b['liberado'] else 'Não liberado'}</b></font>"
                                     + (f"<br/><font size=7 color='#5b6670'>falta: {falta}</font>" if falta else ""), ESTILO)])
        story += _secao_tabela("Blocos: avanço e liberação para edificação",
                               ["Bloco", "Casco", "Prev.", "Real.", "Na semana", "Desvio", "Liberação"], linhas,
                               [16 * mm, 24 * mm, 16 * mm, 16 * mm, 20 * mm, 18 * mm, larg - 110 * mm])

    story += _secao_tabela("HH perdido na semana por motivo", ["Motivo", "Ocorrências", "HH perdido"],
                           [[m["motivo"], m["n"], _num(m["hh"], 0)] for m in dados["motivos"]],
                           [larg - 60 * mm, 30 * mm, 30 * mm], vazio="Nenhuma paralisação registrada na semana.")

    s = dados["solda"]
    p = dados["punch"]
    story += _secao_tabela("Solda e punch list", ["Indicador", "Semana", "Situação atual"], [
        ["Metros soldados", f"{_num(s['metros'], 0)} m", "-"],
        ["Ensaios (END) com resultado", f"{_num(s['inspecionado'], 0)} m ensaiados · {_num(s['reprovado'], 1)} m reprovados",
         f"{s['pendentes']} aguardando resultado"],
        ["Pendências do punch list", f"{p['abertas_semana']} abertas · {p['fechadas_semana']} fechadas",
         f"{p['em_aberto']} em aberto ({p['A']} A, {p['vencidas']} vencidas)"],
    ], [50 * mm, 70 * mm, larg - 120 * mm])

    story += _secao_tabela("Ocorrências de segurança e qualidade", ["Data", "Bloco", "Tipo", "Gravidade", "Descrição", "Situação"],
                           [[f"{o.rdc.data:%d/%m}", o.rdc.area_local.codigo, o.get_tipo_display(), o.get_gravidade_display(),
                             o.descricao, o.get_status_display()] for o in dados["ocorrencias"]],
                           [14 * mm, 16 * mm, 30 * mm, 21 * mm, larg - 107 * mm, 26 * mm],
                           vazio="Nenhuma ocorrência registrada na semana.")
    story += [Spacer(1, 8), _p(f"Base: {dados['rdcs']} RDC(s) lançados na semana. Avanço físico calculado a partir das "
                                "quantidades executadas nos RDCs sobre o cronograma, ponderado pelo HH orçado.", ESTILO_MUTED)]

    quem = getattr(gerado_por, "username", "") or "envio automático"
    emitido = timezone.localtime()

    def cabecalho(c, d):
        largura, alt = A4
        topo = alt - 10 * mm
        c.saveState()
        c.setFillColor(NAVY); c.rect(14 * mm, topo - 20 * mm, largura - 28 * mm, 20 * mm, stroke=0, fill=1)
        c.setFillColor(ORANGE); c.rect(14 * mm, topo - 20 * mm, largura - 28 * mm, 1.1 * mm, stroke=0, fill=1)
        x = 20 * mm
        logo = _logo_path()
        if logo:
            c.drawImage(logo, 17 * mm, topo - 17 * mm, 13 * mm, 13 * mm, mask="auto"); x = 34 * mm
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 12.5)
        c.drawString(x, topo - 8.5 * mm, "Relatório semanal de obra")
        c.setFont("Helvetica", 8.5)
        c.drawString(x, topo - 13.5 * mm, f"{projeto.nome} · cliente {projeto.cliente}"[:110])
        c.drawString(x, topo - 17.5 * mm, f"Semana de {dados['inicio']:%d/%m/%Y} a {dados['fim']:%d/%m/%Y}")
        c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
        c.drawString(14 * mm, 8 * mm, f"RDC Inteligente · D'OR@NGE · emitido ({quem}) em {emitido:%d/%m/%Y %H:%M}")
        c.drawRightString(largura - 14 * mm, 8 * mm, f"Página {d.page}")
        c.restoreState()

    doc.build(story, onFirstPage=cabecalho, onLaterPages=cabecalho)
    return buffer.getvalue(), dados


def _secao_tabela(titulo, cabecalho, linhas, larguras, vazio="Sem dados."):
    if not linhas:
        return [Paragraph(titulo, ESTILO_SECAO), _p(vazio, ESTILO_MUTED)]
    return [Paragraph(titulo, ESTILO_SECAO), _tabela(cabecalho, linhas, larguras)]


def enviar_relatorios_semanais(fim=None, projeto_id=None):
    """Um e-mail por projeto ativo com e-mails cadastrados e RDC na semana. Devolve quantos saíram."""
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives
    from django.utils.html import escape

    from cadastros.models import Projeto

    if not getattr(settings, "EMAIL_CONFIGURADO", False):
        raise ValueError("O envio de e-mail não está configurado (falta RESEND_API_KEY).")
    inicio, fim = periodo_da_semana(fim)
    enviados = 0
    projetos = Projeto.objects.filter(ativo=True)
    if projeto_id:
        projetos = projetos.filter(pk=projeto_id)
    for projeto in projetos:
        destinatarios = projeto.lista_emails_relatorio
        if not destinatarios or not RDC.objects.filter(projeto=projeto, data__range=(inicio, fim)).exists():
            continue
        pdf, dados = gerar_pdf_semanal(projeto, fim)
        itens = "".join(f"<li style='margin:0 0 6px'>{escape(d)}</li>" for d in dados["destaques"])
        msg = EmailMultiAlternatives(
            f"Relatório semanal · {projeto.nome} · {inicio:%d/%m} a {fim:%d/%m}",
            "Destaques da semana:\n\n" + "\n".join(f"- {d}" for d in dados["destaques"]) + "\n\nO relatório completo segue em PDF.",
            settings.DEFAULT_FROM_EMAIL, destinatarios)
        msg.attach_alternative(
            "<div style='font-family:Arial,sans-serif;color:#111827;max-width:600px'>"
            "<div style='background:#12171c;color:#fff;padding:14px 18px;border-bottom:3px solid #e8611f'>"
            f"<div style='font-size:18px;font-weight:700'>Relatório semanal · {escape(projeto.nome)}</div>"
            f"<div style='font-size:12px;color:#a9b3bc'>Semana de {inicio:%d/%m/%Y} a {fim:%d/%m/%Y} · RDC Inteligente D&#39;OR@NGE</div></div>"
            f"<ul style='padding-left:18px;margin:16px 0'>{itens}</ul>"
            "<p style='font-size:12px;color:#5b6670'>O relatório completo, com curva S, blocos, HH, solda, punch list e ocorrências, segue em anexo.</p></div>",
            "text/html")
        msg.attach(f"Relatorio_semanal_{projeto.codigo}_{fim:%Y%m%d}.pdf", pdf, "application/pdf")
        msg.send(fail_silently=False)
        enviados += 1
    return enviados
