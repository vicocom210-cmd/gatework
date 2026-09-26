"""
Django settings for config project.

Barcha maxfiy va muhitga bog'liq qiymatlar muhit o'zgaruvchilaridan
(yoki loyiha ildizidagi .env faylidan) o'qiladi — namuna: .env.example.

  * Kompyuteringizda (.env bo'lmasa): DEBUG=True, SQLite, fayl-kesh — avvalgidek.
  * Serverda (.env'da DJANGO_DEBUG=0): PostgreSQL, Redis, HTTPS xavfsizlik sozlamalari.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Oddiy .env o'quvchi (KALIT=qiymat qatorlari). Allaqachon o'rnatilgan o'zgaruvchilarni o'zgartirmaydi."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def env(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    return env(name, "1" if default else "0").strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [x.strip() for x in env(name, default).split(",") if x.strip()]


DEBUG = env_bool("DJANGO_DEBUG", True)

# MUHIM: serverda SECRET_KEY faqat .env'dan olinadi. Pastdagi zaxira kalit
# faqat kompyuteringizda (DEBUG) ishlaydi — u GitHub'da ochiq turibdi.
SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY o'rnatilmagan (.env faylga qo'shing).")
    SECRET_KEY = "django-insecure-dev-only-j^4m&&rd&p&s5!%bsaad=$3o9-_(d6nvgy67#v+is23xd1+q0r"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Sayt Caddy/Nginx ortida ishlaganda — haqiqiy IP va HTTPS'ni proksidan olamiz
TRUST_PROXY = env_bool("DJANGO_TRUST_PROXY", not DEBUG)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "rest_framework",
    "users",
    "jobs",
    "pages",
    "chat",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ---------- Ma'lumotlar bazasi ----------
# DATABASE_URL=postgres://user:parol@host:5432/baza  → PostgreSQL
# berilmasa → SQLite (faqat kompyuterda ishlash uchun)
def _database_from_url(url):
    from urllib.parse import unquote, urlparse
    u = urlparse(url)
    if u.scheme not in ("postgres", "postgresql"):
        raise ImproperlyConfigured("DATABASE_URL faqat postgres:// bo'lishi mumkin.")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": u.path.lstrip("/"),
        "USER": unquote(u.username or ""),
        "PASSWORD": unquote(u.password or ""),
        "HOST": u.hostname or "localhost",
        "PORT": str(u.port or 5432),
        # ulanishlarni qayta ishlatish — har so'rovda yangi ulanish ochilmaydi
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }


if env("DATABASE_URL"):
    DATABASES = {"default": _database_from_url(env("DATABASE_URL"))}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
# "python manage.py collectstatic" hamma statik faylni shu yerga yig'adi — serverda Caddy beradi
STATIC_ROOT = Path(env("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles")))

# Foydalanuvchilar yuklagan fayllar (chat rasmlari/ovozlari, avatarlar)
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))

# ---------- Kesh ----------
# Vakansiyalar, urinishlar hisoblagichi (rate limit) shu yerda saqlanadi.
# Serverda — Redis (barcha Gunicorn jarayonlari uchun umumiy, tez).
# Kompyuterda — fayl-kesh ("runserver" qayta ishga tushganda ham yo'qolmaydi).
if env("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": env("REDIS_URL"),
            "TIMEOUT": 15 * 60,
        }
    }
    # Sessiyalar ham Redis'da (bazaga har so'rovda murojaat qilinmaydi), bazada zaxirasi bilan
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": BASE_DIR / ".cache",
            "TIMEOUT": 15 * 60,
        }
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    # Faqat sessiya (cookie) orqali kirish. CSRF tekshiruvi YOQILGAN.
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # Xatolar {"ok": false, "error": "..."} ko'rinishida — JS shuni kutadi
    "EXCEPTION_HANDLER": "users.exceptions.api_exception_handler",
}

# Google Sign-In (static/js/auth.js'dagi GOOGLE_CLIENT_ID bilan bir xil bo'lishi SHART)
GOOGLE_CLIENT_ID = env(
    "GOOGLE_CLIENT_ID", "509245131008-kib34dra6sb7djvqjqjh85ac9ucma0av.apps.googleusercontent.com"
)

# To'lov oynasida ko'rsatiladigan karta raqami (/api/plans). Bo'sh bo'lsa — ko'rsatilmaydi.
PAYMENT_CARD = env("PAYMENT_CARD")

# Chat fayllari uchun yuklash chegarasi (baytlarda)
CHAT_MAX_UPLOAD = 25 * 1024 * 1024
# Bitta so'rov hajmi chegarasi (fayllar bundan tashqari, ular diskka yoziladi)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024


# ---------- Production xavfsizligi (DEBUG=False) ----------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", True)
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SECONDS", "2592000"))  # 30 kun
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 kun
    # HSTS "preload" ataylab o'chiq: u brauzerlarning global ro'yxatiga yozadi va
    # keyin bekor qilish oylab vaqt oladi. Sayt barqaror ishlagach yoqish mumkin.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO" if not DEBUG else "WARNING"},
    "loggers": {"django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False}},
}
