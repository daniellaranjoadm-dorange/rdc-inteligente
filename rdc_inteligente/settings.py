import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
IS_TEST = "test" in os.sys.argv

raw_allowed_hosts = os.getenv("ALLOWED_HOSTS", "")
env_allowed_hosts = [h.strip() for h in raw_allowed_hosts.split(",") if h.strip()]
default_local_hosts = ["127.0.0.1", "localhost", "testserver"]

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = env_allowed_hosts or default_local_hosts

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "mobile_api",
    "core",
    "accounts",
    "cadastros",
    "planejamento",
    "alocacao",
    "acesso",
    "rdc",
    "importacoes",
    "relatorios",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "rdc_inteligente.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "rdc_inteligente.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
}

RDC_TEMPLATE_PATH = BASE_DIR.parent / "RDC - MODELO.xlsx"

# Limites de upload/formulÃ¡rios
DATA_UPLOAD_MAX_NUMBER_FIELDS = 20000
FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400

# CORS para desenvolvimento local do Flutter Web
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ===== SeguranÃ§a para produÃ§Ã£o =====

SECURE_SSL_REDIRECT = (not DEBUG and not IS_TEST) and (
    os.getenv("DJANGO_SECURE_SSL_REDIRECT", "True").lower() == "true"
)

SESSION_COOKIE_SECURE = (not DEBUG and not IS_TEST) and (
    os.getenv("DJANGO_SESSION_COOKIE_SECURE", "True").lower() == "true"
)

CSRF_COOKIE_SECURE = (not DEBUG and not IS_TEST) and (
    os.getenv("DJANGO_CSRF_COOKIE_SECURE", "True").lower() == "true"
)

SECURE_HSTS_SECONDS = 0 if (DEBUG or IS_TEST) else int(
    os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000")
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = (not DEBUG and not IS_TEST) and (
    os.getenv("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "True").lower() == "true"
)

SECURE_HSTS_PRELOAD = (not DEBUG and not IS_TEST) and (
    os.getenv("DJANGO_SECURE_HSTS_PRELOAD", "True").lower() == "true"
)

# SÃ³ faz sentido atrÃ¡s de proxy reverso em produÃ§Ã£o
SECURE_PROXY_SSL_HEADER = None if (DEBUG or IS_TEST) else ("HTTP_X_FORWARDED_PROTO", "https")

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

