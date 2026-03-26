from pathlib import Path

path = Path("core/services/import_funcionarios.py")
content = path.read_text(encoding="utf-8")

# =========================
# TROCAR EMPRESA
# =========================
content = content.replace(
    "empresa, _ = Empresa.objects.get_or_create(",
    """try:
            empresa = Empresa.objects.get("""
)

content = content.replace(
    ")\n",
    """)
        except Empresa.DoesNotExist:
            return self.erro(linha_num, "empresa", f'Empresa "{empresa_nome}" não cadastrada')
"""
)

# =========================
# TROCAR FUNÇÃO
# =========================
content = content.replace(
    "funcao, _ = Funcao.objects.get_or_create(",
    """try:
            funcao = Funcao.objects.get("""
)

content = content.replace(
    ")\n",
    """)
        except Funcao.DoesNotExist:
            return self.erro(linha_num, "funcao", f'Função "{funcao_nome}" não cadastrada')
"""
)

path.write_text(content, encoding="utf-8")

print("[OK] Validação de domínio aplicada.")

