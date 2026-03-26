from pathlib import Path

path = Path("core/services/import_funcionarios.py")
content = path.read_text(encoding="utf-8")

old = """        obj, created = Funcionario.objects.update_or_create(
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

new = """        matricula = row.get("matricula")

        existente = Funcionario.objects.filter(matricula=matricula).first()

        if not existente:
            obj = Funcionario.objects.create(
                matricula=matricula,
                nome=row.get("nome"),
                empresa=empresa,
                funcao=funcao,
                ativo=True,
            )
            status = "created"

        else:
            mudou = (
                existente.nome != row.get("nome")
                or existente.empresa_id != empresa.id
                or existente.funcao_id != funcao.id
            )

            if mudou:
                existente.nome = row.get("nome")
                existente.empresa = empresa
                existente.funcao = funcao
                existente.ativo = True
                existente.save()
                obj = existente
                status = "updated"
            else:
                obj = existente
                status = "unchanged"

        return {
            "matricula": obj.matricula,
            "nome": obj.nome,
            "empresa": empresa.nome,
            "funcao": funcao.nome,
            "status": status,
        }
"""

if old not in content:
    print("[ERRO] Bloco esperado não encontrado")
    raise SystemExit(1)

content = content.replace(old, new)
path.write_text(content, encoding="utf-8")

print("[OK] Importação incremental aplicada.")

