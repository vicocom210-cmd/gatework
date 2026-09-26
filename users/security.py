"""
users/security.py — CSRF tekshiruvi va urinishlar sonini cheklash (rate limit).
"""
from django.conf import settings
from django.core.cache import cache
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied, Throttled


def enforce_csrf(request):
    """
    Tizimga kirmagan foydalanuvchi uchun ham CSRF'ni tekshiradi
    (login/register/logout). DRF buni faqat kirgan foydalanuvchi uchun
    qiladi. Frontend tokenni X-CSRFToken sarlavhasida yuboradi
    (templates/base.html'dagi fetch o'rovchisi).
    """
    check = CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied(f"CSRF tekshiruvi o'tmadi: {reason}")


def client_ip(request):
    """
    Foydalanuvchi IP manzili. Sayt Caddy/Nginx ortida ishlaganda haqiqiy
    IP X-Forwarded-For'da keladi — unga faqat TRUST_PROXY=1 bo'lsa ishonamiz
    (aks holda har kim o'zini boshqa IP deb ko'rsata olardi).
    """
    if getattr(settings, "TRUST_PROXY", False):
        fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def rate_limit(request, scope, limit, window, extra=""):
    """
    `window` soniya ichida `limit` martadan ko'p urinish bo'lsa — 429.
    Masalan: rate_limit(request, "login", 10, 900) — 15 daqiqada 10 ta.
    """
    key = f"rl:{scope}:{client_ip(request)}:{extra.lower()}"
    cache.add(key, 0, window)
    try:
        n = cache.incr(key)
    except ValueError:  # kalit shu orada muddati tugab o'chdi
        cache.set(key, 1, window)
        n = 1
    if n > limit:
        raise Throttled(detail="Juda ko'p urinish. Birozdan keyin qayta urinib ko'ring.")
