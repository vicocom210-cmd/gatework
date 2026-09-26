"""
{% asset 'css/style.css' %}  →  /static/css/style.css?v=1789012345

Fayl o'zgarganda (masalan git pull'dan keyin) versiya raqami ham o'zgaradi,
shuning uchun brauzer eski CSS/JS'ni keshdan olmaydi — Ctrl+F5 shart emas.
"""
import os
from functools import lru_cache

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


def _version(path):
    full = finders.find(path)
    if not full:
        full = os.path.join(str(settings.STATIC_ROOT), path)
    try:
        return int(os.path.getmtime(full))
    except OSError:
        return 0


# Serverda (DEBUG=False) fayllar o'zgarmaydi — versiyani bir marta hisoblaymiz
_cached_version = lru_cache(maxsize=256)(_version)


@register.simple_tag
def asset(path):
    v = _version(path) if settings.DEBUG else _cached_version(path)
    return f"{static(path)}?v={v}"
