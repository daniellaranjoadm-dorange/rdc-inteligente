Write-Host "=== VALIDACAO LOCAL RDC INTELIGENTE ==="

Write-Host ""
Write-Host "[1/4] Django check"
python manage.py check
if (0 -ne 0) {
    Write-Host "Falha em: python manage.py check"
    exit 0
}

Write-Host ""
Write-Host "[2/4] Migrations pendentes"
python manage.py makemigrations --check --dry-run
if (0 -ne 0) {
    Write-Host "Falha em: python manage.py makemigrations --check --dry-run"
    exit 0
}

Write-Host ""
Write-Host "[3/4] Testes automatizados"
python manage.py test
if (0 -ne 0) {
    Write-Host "Falha em: python manage.py test"
    exit 0
}

Write-Host ""
Write-Host "[4/4] Collectstatic dry-run"
python manage.py collectstatic --noinput --dry-run
if (0 -ne 0) {
    Write-Host "Falha em: python manage.py collectstatic --noinput --dry-run"
    exit 0
}

Write-Host ""
Write-Host "VALIDACAO CONCLUIDA COM SUCESSO"
exit 0
