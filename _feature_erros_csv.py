from pathlib import Path

# =========================
# PATHS
# =========================
views_path = Path("importacoes/views.py")
urls_path = Path("importacoes/urls.py")
template_path = Path("templates/importacoes/form.html")

views = views_path.read_text(encoding="utf-8")

# =========================
# 1. VIEW DOWNLOAD ERROS
# =========================
if "download_erros_importacao" not in views:
    views += """

from django.http import HttpResponse
from importacoes.models import ImportacaoArquivo

def download_erros_importacao(request, pk):
    importacao = ImportacaoArquivo.objects.get(pk=pk)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="erros_importacao_{importacao.pk}.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['linha', 'campo', 'mensagem'])

    for erro in importacao.erros.all():
        writer.writerow([erro.linha, erro.campo, erro.mensagem])

    return response
"""

views_path.write_text(views, encoding="utf-8")

# =========================
# 2. URL
# =========================
urls = urls_path.read_text(encoding="utf-8")

if "download_erros_importacao" not in urls:
    urls = urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('<int:pk>/erros/', download_erros_importacao, name='download_erros_importacao'),"
    )

    if "download_erros_importacao" not in urls:
        urls = urls.replace(
            "from importacoes.views import",
            "from importacoes.views import download_erros_importacao, "
        )

urls_path.write_text(urls, encoding="utf-8")

# =========================
# 3. BOTÃO NO TEMPLATE
# =========================
template = template_path.read_text(encoding="utf-8")

button_html = """
{% if object %}
<div style="margin-bottom: 16px;">
    <a href="{% url 'download_erros_importacao' object.pk %}" class="btn btn-danger">
        ⬇ Baixar erros da importação
    </a>
</div>
{% endif %}
""".strip()

if "download_erros_importacao" not in template:
    template = template + "\n\n" + button_html

template_path.write_text(template, encoding="utf-8")

print("[OK] Download de erros implementado.")

