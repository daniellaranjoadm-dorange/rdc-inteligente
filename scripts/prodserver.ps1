$env:DJANGO_DEBUG="False"
$env:DJANGO_SECURE_SSL_REDIRECT="False"
$env:DJANGO_SESSION_COOKIE_SECURE="False"
$env:DJANGO_CSRF_COOKIE_SECURE="False"
$env:ALLOWED_HOSTS="127.0.0.1,localhost"

python manage.py collectstatic --noinput
gunicorn rdc_inteligente.wsgi:application --bind 127.0.0.1:8001 --workers 3 --timeout 120
