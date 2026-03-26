from pathlib import Path

path = Path("core/services/import_funcionarios.py")
content = path.read_text(encoding="utf-8")

old = """    def process_row(self, row, index):
        empresa_nome = row.get("empresa").strip()
        funcao_nome = row.get("funcao").strip()

        empresa, _ = Empresa.objects.get_or_create(
            nome=empresa_nome,
            defaults={
                "ativa": True,
            },
        )

        funcao_codigo = funcao_nome.upper().replace(" ", "_")[:30]

        funcao, _ = Funcao.objects.get_or_create(
            codigo=funcao_codigo,
            defaults={
                "nome": funcao_nome,
                "ativa": True,
            },
        )

        obj, created = Funcionario.objects.update_or_create(
            matricula=row.get("matricula"),
            defaults={
                "nome": row.get("nome"),
                "empresa": empresa,
                "funcao": funcao,
                "ativo": True,
            },
        )

        return {
            "matricula": obj.matricula,
            "nome": obj.nome,
            "empresa": empresa.nome,
            "funcao": funcao.nome,
            "created": created,
        }
"""

new = """    def process_row(self, row, index):
        empresa_nome = row.get("empresa").strip()
        funcao_nome = row.get("funcao").strip()

        try:
            empresa = Empresa.objects.get(nome=empresa_nome)
        except Empresa.DoesNotExist:
            raise ValueError(f'Empresa "{empresa_nome}" não cadastrada.')

        try:
            funcao = Funcao.objects.get(nome=funcao_nome)
        except Funcao.DoesNotExist:
            raise ValueError(f'Função "{funcao_nome}" não cadastrada.')

        obj, created = Funcionario.objects.update_or_create(
            matricula=row.get("matricula"),
            defaults={
                "nome": row.get("nome"),
                "empresa": empresa,
                "funcao": funcao,
                "ativo": True,
            },
        )

        return {
            "matricula": obj.matricula,
            "nome": obj.nome,
            "empresa": empresa.nome,
            "funcao": funcao.nome,
            "created": created,
        }
"""

if old not in content:
    print("[ERRO] Bloco esperado não encontrado em core/services/import_funcionarios.py")
    raise SystemExit(1)

content = content.replace(old, new)
path.write_text(content, encoding="utf-8")
print("[OK] Validação de domínio aplicada com segurança.")

