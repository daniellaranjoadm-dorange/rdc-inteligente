$env:DJANGO_DEBUG="True"
$env:DJANGO_SECURE_SSL_REDIRECT="False"
$env:DJANGO_SESSION_COOKIE_SECURE="False"
$env:DJANGO_CSRF_COOKIE_SECURE="False"
$env:DJANGO_CSRF_COOKIE_SECURE="False"
$env:ALLOWED_HOSTS="127.0.0.1,localhost,testserver"

python manage.py runserver 127.0.0.1:8010 --noreload
