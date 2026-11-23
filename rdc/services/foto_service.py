"""Tratamento das fotos do RDC: corrige orientacao, reduz tamanho e gera miniatura."""
from datetime import datetime
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

TAMANHO_MAXIMO_UPLOAD = 15 * 1024 * 1024  # 15 MB por foto, antes de reduzir
LADO_MAXIMO = 1600
LADO_MINIATURA = 400
QUALIDADE_JPEG = 82
FOTOS_POR_ENVIO = 12

# EXIF: 36867 = DateTimeOriginal, 306 = DateTime
_EXIF_DATAS = (36867, 306)


def _data_exif(img):
    try:
        exif = img.getexif()
        for tag in _EXIF_DATAS:
            bruto = exif.get(tag) or exif.get_ifd(0x8769).get(tag)
            if bruto:
                return timezone.make_aware(datetime.strptime(str(bruto).strip(), "%Y:%m:%d %H:%M:%S"))
    except Exception:
        return None
    return None


def _jpeg(img, lado):
    copia = img.copy()
    copia.thumbnail((lado, lado), Image.LANCZOS)
    buffer = BytesIO()
    copia.save(buffer, format="JPEG", quality=QUALIDADE_JPEG, optimize=True, progressive=True)
    return buffer.getvalue(), copia.size


def processar_foto(arquivo):
    """Valida e prepara a foto enviada.

    Retorna dict com bytes da imagem e da miniatura, tamanho final e a data da foto (EXIF),
    ou levanta ValidationError com uma mensagem para o usuario.
    """
    nome = getattr(arquivo, "name", "foto")
    if getattr(arquivo, "size", 0) > TAMANHO_MAXIMO_UPLOAD:
        raise ValidationError(f"{nome}: arquivo maior que 15 MB.")
    try:
        img = Image.open(arquivo)
        img.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError(f"{nome}: não é uma imagem válida (use JPG, PNG ou HEIC convertido).")

    tirada_em = _data_exif(img)
    img = ImageOps.exif_transpose(img)  # celular grava a foto deitada + tag de rotacao
    if img.mode not in ("RGB", "L"):
        fundo = Image.new("RGB", img.size, (255, 255, 255))
        fundo.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
        img = fundo
    elif img.mode == "L":
        img = img.convert("RGB")

    conteudo, (largura, altura) = _jpeg(img, LADO_MAXIMO)
    miniatura, _ = _jpeg(img, LADO_MINIATURA)
    return {
        "imagem": ContentFile(conteudo),
        "miniatura": ContentFile(miniatura),
        "largura": largura,
        "altura": altura,
        "tamanho_bytes": len(conteudo),
        "tirada_em": tirada_em,
    }
