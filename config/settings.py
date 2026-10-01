"""
Django settings for config project.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-j^4m&&rd&p&s5!%bsaad=$3o9-_(d6nvgy67#v+is23xd1+q0r'

DEBUG = True

ALLOWED_HOSTS = []


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
                # UZ/RU/EN/DE: aloqa havolalari (Telegram/Instagram/Gmail) — har sahifaga
                'pages.context_processors.contact',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


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

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

# Foydalanuvchilar yuklagan fayllar (chat rasmlari/ovozlari, avatarlar)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "users.User"

# ============================================================================
# UZ: MAXFIY sozlamalar (API kalitlari) — agar config/local_settings.py mavjud
#     bo'lsa, shu yerda o'qiladi. Bu fayl GitHub'ga chiqmaydi (.gitignore).
#     Yangi kompyuterда: local_settings.example.py dan nusxa olib, kalit yozing.
# RU: СЕКРЕТНЫЕ настройки (ключи API) — читаются из config/local_settings.py,
#     если он есть. Файл не попадает на GitHub (.gitignore). На новом ПК:
#     скопируйте local_settings.example.py и впишите ключи.
# EN: SECRET settings (API keys) — read from config/local_settings.py if it
#     exists. That file is not pushed to GitHub (.gitignore). On a new machine:
#     copy local_settings.example.py and fill in the keys.
# DE: GEHEIME Einstellungen (API-Schlüssel) — werden aus config/local_settings.py
#     gelesen, falls vorhanden. Nicht auf GitHub (.gitignore). Auf neuem PC:
#     local_settings.example.py kopieren und Schlüssel eintragen.
# ============================================================================
try:
    from .local_settings import *  # noqa: F401,F403
except ImportError:
    pass