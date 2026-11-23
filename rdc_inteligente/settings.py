import os
from pathlib import Path
from datetime import timedelta
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Render define RENDER=true em todo servico; usado para exigir configuracao segura.
ON_RENDER = os.getenv("RENDER", "").lower() == "true"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY") or "change-me-in-production"
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
IS_TEST = "test" in os.sys.argv

if ON_RENDER and SECRET_KEY == "change-me-in-production":
    raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY no Render.")

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

def _database_from_url(url):
    """Converte DATABASE_URL (postgres://user:pass@host:port/db?sslmode=...) para o Django."""
    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ImproperlyConfigured(f"DATABASE_URL com esquema nao suportado: {parsed.scheme}")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
        "CONN_MAX_AGE": int(os.getenv("DJANGO_DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": dict(parse_qsl(parsed.query)),
    }


_database_url = os.getenv("DATABASE_URL", "").strip()
if _database_url:
    DATABASES = {"default": _database_from_url(_database_url)}
elif ON_RENDER:
    # No Render o disco do servico e apagado a cada deploy: SQLite perderia os dados.
    raise ImproperlyConfigured("Defina DATABASE_URL (Postgres) no Render.")
else:
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
# No Render aponta para o disco persistente (ex.: /var/data/media).
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))

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

# Modelo do RDC: variavel de ambiente > copia versionada em assets/ > arquivo ao lado do projeto.
_rdc_template_candidates = [
    Path(p) for p in [os.getenv("RDC_TEMPLATE_PATH", "")] if p
] + [BASE_DIR / "assets" / "RDC - MODELO.xlsx", BASE_DIR.parent / "RDC - MODELO.xlsx"]
RDC_TEMPLATE_PATH = next((p for p in _rdc_template_candidates if p.exists()), _rdc_template_candidates[0])

# Limites de upload/formulários
DATA_UPLOAD_MAX_NUMBER_FIELDS = 20000
FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400

# CORS: liberado por padrao para o Flutter Web local; em producao use a lista explicita.
CORS_ALLOW_ALL_ORIGINS = os.getenv("DJANGO_CORS_ALLOW_ALL", "1") == "1"
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("DJANGO_CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

# ===== Segurança para produção =====

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

# Só faz sentido atrás de proxy reverso em produção
SECURE_PROXY_SSL_HEADER = None if (DEBUG or IS_TEST) else ("HTTP_X_FORWARDED_PROTO", "https")

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"




# DEPLOY_PWA_BLOCK
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

_csrf_origins = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins.strip():
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

USE_X_FORWARDED_HOST = True

SESSION_COOKIE_SECURE = os.getenv("DJANGO_SESSION_COOKIE_SECURE", "0") == "1"
CSRF_COOKIE_SECURE = os.getenv("DJANGO_CSRF_COOKIE_SECURE", "0") == "1"

SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "0") == "1"

PWA_APP_NAME = os.getenv("PWA_APP_NAME", "RDC Mobile")
PWA_APP_SCOPE = os.getenv("PWA_APP_SCOPE", "/")
PWA_START_URL = os.getenv("PWA_START_URL", "/m/")
PWA_THEME_COLOR = os.getenv("PWA_THEME_COLOR", "#0b2239")


# ===== E-mail (envio do RDC) =====
# Resend: defina RESEND_API_KEY no Render (o mesmo provedor do Business AI).
# Alternativa: EMAIL_HOST / EMAIL_PORT / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD de outro SMTP.
DEFAULT_FROM_EMAIL = os.getenv("EMAIL_FROM", "RDC Inteligente D'OR@NGE <rdc@dorange.com.br>")
_resend_key = os.getenv("RESEND_API_KEY", "").strip()
if _resend_key:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS = "smtp.resend.com", 587, True
    EMAIL_HOST_USER, EMAIL_HOST_PASSWORD = "resend", _resend_key
elif os.getenv("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
else:
    # Sem provedor: nada sai; a tela avisa que o e-mail nao esta configurado.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_TIMEOUT = 20
EMAIL_CONFIGURADO = bool(_resend_key or os.getenv("EMAIL_HOST"))

APP_URL = os.getenv("APP_URL", "https://rdc.dorange.com.br")
