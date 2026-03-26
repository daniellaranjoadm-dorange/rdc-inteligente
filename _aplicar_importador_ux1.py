from pathlib import Path
import re
import sys

ROOT = Path.cwd()

files = {
    "views": ROOT / "apps" / "importador" / "views.py",
    "urls": ROOT / "apps" / "importador" / "urls.py",
    "template": ROOT / "templates" / "importador" / "importar_funcionarios.html",
}

for nome, caminho in files.items():
    if not caminho.exists():
        print(f"[ERRO] Arquivo não encontrado: {caminho}")
        sys.exit(1)

# -----------------------------
# views.py
# -----------------------------
views_path = files["views"]
views = views_path.read_text(encoding="utf-8")

if "import csv" not in views:
    if "from django.http import HttpResponse" in views:
        views = views.replace(
            "from django.http import HttpResponse",
            "from django.http import HttpResponse\nimport csv"
        )
    else:
        views = "import csv\n" + views

func_code = '''

def download_modelo_funcionarios(request):
    """
    Gera um CSV modelo para importação de funcionários.
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename=\"modelo_funcionarios.csv\"'

    writer = csv.writer(response, delimiter=';')

    writer.writerow(['matricula', 'nome', 'empresa', 'funcao'])
    writer.writerow(['123', 'João Silva', 'Empresa Exemplo', 'Operador'])

    return response
'''.rstrip() + "\n"

if "def download_modelo_funcionarios(request):" not in views:
    views = views.rstrip() + "\n\n" + func_code

views_path.write_text(views, encoding="utf-8")

# -----------------------------
# urls.py
# -----------------------------
urls_path = files["urls"]
urls = urls_path.read_text(encoding="utf-8")

route_line = "    path('modelo/funcionarios/', views.download_modelo_funcionarios, name='download_modelo_funcionarios'),"

if "download_modelo_funcionarios" not in urls:
    match = re.search(r"urlpatterns\s*=\s*\[\n", urls)
    if not match:
        print("[ERRO] Não foi possível localizar urlpatterns em apps/importador/urls.py")
        sys.exit(1)
    insert_at = match.end()
    urls = urls[:insert_at] + route_line + "\n" + urls[insert_at:]

urls_path.write_text(urls, encoding="utf-8")

# -----------------------------
# template
# -----------------------------
template_path = files["template"]
template = template_path.read_text(encoding="utf-8")

button_html = """
<div style="margin-bottom: 16px;">
    <a href="{% url 'download_modelo_funcionarios' %}" class="btn btn-secondary">
        ⬇ Baixar modelo CSV
    </a>
</div>
""".strip()

if "download_modelo_funcionarios" not in template:
    alvo = "<h2>Importar Funcionários</h2>"
    if alvo in template:
        template = template.replace(alvo, alvo + "\n\n" + button_html, 1)
    else:
        template = button_html + "\n\n" + template

template_path.write_text(template, encoding="utf-8")

print("[OK] Alterações aplicadas com sucesso.")

