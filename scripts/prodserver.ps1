$env:DJANGO_DEBUG="False"
$env:ALLOWED_HOSTS="127.0.0.1,localhost"

python manage.py collectstatic --noinput
python -m waitress --listen=127.0.0.1:8001 rdc_inteligente.wsgi:application
