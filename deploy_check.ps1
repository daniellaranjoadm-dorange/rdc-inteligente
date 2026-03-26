Write-Host "=== VALIDACAO LOCAL DEPLOY ===" -ForegroundColor Cyan
python manage.py check
python manage.py collectstatic --noinput
