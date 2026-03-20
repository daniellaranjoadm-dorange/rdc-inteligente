from pathlib import Path
from datetime import datetime

from django.conf import settings
from openpyxl import Workbook

from core.audit import traduzir_acao_auditoria


def exportar_auditoria_rdc_para_excel(rdc, logs):
    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoria RDC"

    ws.append(["RDC", rdc.pk])
    ws.append(["Projeto", getattr(getattr(rdc, "projeto", None), "codigo", "")])
    ws.append(["Data", rdc.data.strftime("%d/%m/%Y") if getattr(rdc, "data", None) else ""])
    ws.append([])
    ws.append(["Data/Hora", "Usuário", "Ação", "Detalhe"])

    for log in logs:
        ws.append([
            datetime.strftime(log.created_at, "%d/%m/%Y %H:%M") if log.created_at else "",
            log.user.username if log.user else "Sistema",
            traduzir_acao_auditoria(log.action),
            log.detail or "",
        ])

    export_dir = Path(settings.MEDIA_ROOT) / "auditoria_exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    filename = f"auditoria_rdc_{rdc.pk}.xlsx"
    out_path = export_dir / filename
    wb.save(out_path)

    return out_path
