"""Envio do RDC por e-mail: resumo no corpo, PDF do RDC e relatorio fotografico anexados."""
import logging
import re

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils.html import escape

from core.audit import registrar_auditoria

log = logging.getLogger(__name__)


def separar_emails(texto):
    emails, invalidos = [], []
    for item in re.split(r"[\s,;]+", texto or ""):
        if not item:
            continue
        try:
            validate_email(item)
            if item.lower() not in [e.lower() for e in emails]:
                emails.append(item)
        except ValidationError:
            invalidos.append(item)
    return emails, invalidos


def _resumo(rdc):
    hh = rdc.funcionarios.aggregate(t=Sum("hh_total"))["t"] or 0
    perdido = rdc.paralisacoes.aggregate(t=Sum("hh_perdido"))["t"] or 0
    return [
        ("Projeto", rdc.projeto.nome),
        ("Área", rdc.area_local.descricao),
        ("Disciplina", rdc.disciplina.nome),
        ("Data / turno", f"{rdc.data:%d/%m/%Y} · {rdc.get_turno_display()}"),
        ("Status", rdc.status_workflow_label),
        ("Efetivo", rdc.funcionarios.count()),
        ("HH trabalhado", f"{float(hh):.2f}".replace(".", ",")),
        ("HH perdido", f"{float(perdido):.2f}".replace(".", ",")),
        ("Paralisações", rdc.paralisacoes.count()),
        ("Ocorrências", rdc.ocorrencias.count()),
        ("Fotos", rdc.fotos.count()),
    ]


def enviar_rdc_por_email(rdc, destinatarios, *, usuario=None, base_url="", motivo="manual"):
    """Envia e devolve a quantidade de destinatarios. Levanta ValueError com mensagem para o usuario."""
    if not getattr(settings, "EMAIL_CONFIGURADO", False):
        raise ValueError("O envio de e-mail ainda não está configurado no servidor (falta RESEND_API_KEY no Render).")
    if not destinatarios:
        raise ValueError("Nenhum destinatário. Cadastre os e-mails do projeto ou informe na hora do envio.")

    from rdc.services.relatorio_rdc import gerar_pdf_rdc

    linhas = _resumo(rdc)
    assunto = f"RDC #{rdc.pk} · {rdc.projeto.nome} · {rdc.area_local.descricao} · {rdc.data:%d/%m/%Y}"
    link = f"{base_url.rstrip('/')}/rdc/{rdc.pk}/" if base_url else ""
    texto = "\n".join(f"{k}: {v}" for k, v in linhas) + (f"\n\nAbrir no sistema: {link}" if link else "")
    tabela = "".join(f"<tr><td style='padding:4px 12px 4px 0;color:#5b6b7d'>{escape(k)}</td><td style='padding:4px 0;font-weight:600'>{escape(str(v))}</td></tr>" for k, v in linhas)
    html = (
        "<div style='font-family:Arial,sans-serif;color:#142130;max-width:560px'>"
        "<div style='background:#172432;color:#fff;padding:14px 18px;border-bottom:3px solid #f07a12'>"
        f"<div style='font-size:18px;font-weight:700'>RDC #{rdc.pk} · Relatório Diário de Campo</div>"
        "<div style='font-size:12px;color:#c9d1da'>RDC Inteligente · D'OR@NGE</div></div>"
        f"<table style='margin:14px 0;font-size:14px'>{tabela}</table>"
        + (f"<p><a href='{escape(link)}' style='background:#f07a12;color:#0e1823;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:700'>Abrir no sistema</a></p>" if link else "")
        + "<p style='font-size:12px;color:#5b6b7d'>O PDF completo do RDC segue em anexo.</p></div>"
    )

    msg = EmailMultiAlternatives(assunto, texto, settings.DEFAULT_FROM_EMAIL, destinatarios)
    msg.attach_alternative(html, "text/html")
    msg.attach(f"RDC_{rdc.pk}_{rdc.data:%Y%m%d}.pdf", gerar_pdf_rdc(rdc, gerado_por=usuario), "application/pdf")
    fotos = list(rdc.fotos.all())
    if fotos:
        from rdc.services.relatorio_fotografico import gerar_pdf_fotografico
        msg.attach(f"RDC_{rdc.pk}_fotos.pdf", gerar_pdf_fotografico(rdc, fotos, gerado_por=usuario), "application/pdf")
    msg.send(fail_silently=False)

    registrar_auditoria(usuario, "enviar_email_rdc", target_model="RDC", target_id=rdc.pk,
                        detail=f"{motivo}: {', '.join(destinatarios)}")
    return len(destinatarios)


def agendar_envio_no_fechamento(rdc, usuario=None):
    """Chamado ao fechar o RDC. Envia depois do commit; qualquer falha so vai para o log (nunca impede o fechamento)."""
    destinatarios = rdc.projeto.lista_emails_relatorio
    if not destinatarios or not getattr(settings, "EMAIL_CONFIGURADO", False):
        return

    def _enviar():
        try:
            enviar_rdc_por_email(rdc, destinatarios, usuario=usuario, base_url=getattr(settings, "APP_URL", ""), motivo="fechamento")
        except Exception:  # noqa: BLE001 - e-mail nunca derruba o fechamento
            log.exception("Falha ao enviar RDC %s por e-mail no fechamento", rdc.pk)

    transaction.on_commit(_enviar)


def enviar_alertas_por_email(hoje=None):
    """Um e-mail por projeto (para a lista do projeto) com os alertas do dia. Devolve quantos e-mails saíram."""
    from cadastros.models import Projeto
    from rdc.services.alertas_service import gerar_alertas

    if not getattr(settings, "EMAIL_CONFIGURADO", False):
        raise ValueError("O envio de e-mail não está configurado (falta RESEND_API_KEY).")
    enviados = 0
    base = getattr(settings, "APP_URL", "").rstrip("/")
    cores = {"danger": "#b91c1c", "warning": "#b45309", "info": "#1d4ed8"}
    for projeto in Projeto.objects.filter(ativo=True):
        destinatarios = projeto.lista_emails_relatorio
        alertas = gerar_alertas(hoje=hoje, projeto_id=projeto.pk) if destinatarios else []
        if not alertas:
            continue
        itens_txt = "\n".join(f"- {a['titulo']} ({a['detalhe']}) {base}{a['url']}" for a in alertas)
        itens_html = "".join(
            f"<li style=\"margin:0 0 10px\"><strong style=\"color:{cores.get(a['nivel'], '#142130')}\">{escape(a['titulo'])}</strong>"
            f"<br><span style=\"color:#5b6b7d;font-size:13px\">{escape(a['detalhe'])}</span>"
            f"<br><a href=\"{escape(base + a['url'])}\">{escape(a['acao'])}</a></li>"
            for a in alertas
        )
        msg = EmailMultiAlternatives(
            f"RDC · {len(alertas)} alerta(s) hoje · {projeto.nome}",
            f"Alertas do RDC Inteligente para {projeto.nome}:\n\n{itens_txt}",
            settings.DEFAULT_FROM_EMAIL, destinatarios,
        )
        msg.attach_alternative(
            "<div style=\"font-family:Arial,sans-serif;color:#142130;max-width:600px\">"
            "<div style=\"background:#172432;color:#fff;padding:14px 18px;border-bottom:3px solid #f07a12\">"
            f"<div style=\"font-size:18px;font-weight:700\">Alertas do dia · {escape(projeto.nome)}</div>"
            "<div style=\"font-size:12px;color:#c9d1da\">RDC Inteligente · D&#39;OR@NGE</div></div>"
            f"<ul style=\"padding-left:18px;margin:16px 0\">{itens_html}</ul></div>",
            "text/html",
        )
        msg.send(fail_silently=False)
        enviados += 1
    return enviados
