"""
Django settings for config project.
"""

import os
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

# Kesh: vakansiyalar natijasi shu yerda 15 daqiqa saqlanadi.
# Fayl-asosli — "runserver" qayta ishga tushganda (kod o'zgarganda)
# ham kesh yo'qolmaydi. Keyingi bosqichda Redis'ga almashtiriladi.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": BASE_DIR / ".cache",
        "TIMEOUT": 15 * 60,
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "users.User"

# Google Sign-In (static/js/auth.js'dagi GOOGLE_CLIENT_ID bilan bir xil bo'lishi SHART)
GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID", "509245131008-kib34dra6sb7djvqjqjh85ac9ucma0av.apps.googleusercontent.com"
)

# To'lov oynasida ko'rsatiladigan karta raqami (/api/plans). Bo'sh bo'lsa — ko'rsatilmaydi.
PAYMENT_CARD = os.environ.get("PAYMENT_CARD", "")

# Chat fayllari va avatarlar uchun yuklash chegarasi (baytlarda)
CHAT_MAX_UPLOAD = 25 * 1024 * 1024