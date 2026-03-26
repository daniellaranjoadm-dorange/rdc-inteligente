from pathlib import Path

path = Path("core/services/import_funcionarios.py")
content = path.read_text(encoding="utf-8")

# =========================
# RESTAURAR get_or_create (caso tenha sido corrompido)
# =========================
content = content.replace("empresa = Empresa.objects.get(", "empresa, _ = Empresa.objects.get_or_create(")
content = content.replace("funcao = Funcao.objects.get(", "funcao, _ = Funcao.objects.get_or_create(")

# Remove blocos quebrados de try/except mal inseridos
content = content.replace("try:\n", "")
content = content.replace("except Empresa.DoesNotExist:\n            return self.erro(linha_num, \"empresa\", f'Empresa \"{empresa_nome}\" não cadastrada')\n", "")
content = content.replace("except Funcao.DoesNotExist:\n            return self.erro(linha_num, \"funcao\", f'Função \"{funcao_nome}\" não cadastrada')\n", "")

path.write_text(content, encoding="utf-8")

print("[OK] Arquivo restaurado para estado estável.")

