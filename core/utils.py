import re
import unicodedata

def normalizar_texto(valor: str) -> str:
    if not valor:
        return ""
    valor = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    valor = re.sub(r"\s+", " ", valor).strip().lower()
    return valor

