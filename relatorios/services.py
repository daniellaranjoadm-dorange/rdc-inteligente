from rdc.models import RDC

def montar_contexto_pdf_rdc(rdc: RDC) -> dict:
    return {
        "cabecalho": {
            "projeto": str(rdc.projeto),
            "area_local": str(rdc.area_local),
            "disciplina": str(rdc.disciplina),
            "data": rdc.data,
            "turno": rdc.turno,
            "status": rdc.status,
        },
        "atividades": list(rdc.atividades.values()),
        "funcionarios": list(rdc.funcionarios.values()),
        "validacoes": list(rdc.validacoes.values()),
    }


