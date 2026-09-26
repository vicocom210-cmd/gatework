"""
users/utils.py — bir nechta ilova (users, jobs, chat) birgalikda
ishlatadigan kichik yordamchi funksiyalar.
"""
import os
import time
from datetime import timedelta, timezone as dt_timezone

from django.core.files.storage import default_storage
from django.utils import timezone


def fmt_dt(dt):
    """
    MUHIM: eski JS (timeAgo, isOnline) vaqtni Flask'dagi kabi
    "YYYY-MM-DD HH:MM:SS" (UTC, zonasiz) ko'rinishida kutadi va
    oxiriga o'zi "Z" qo'shadi. Django'ning isoformat() natijasi
    ("...+00:00") bunga "Z" qo'shilsa — "Invalid Date" bo'lib qoladi.
    """
    if not dt:
        return None
    if timezone.is_aware(dt):
        dt = dt.astimezone(dt_timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def plan_active(user):
    """Tarif hali kuchidami? Muddati o'tmagan pro/max, yoki admin."""
    if user.is_staff:
        return True
    if user.plan in ("pro", "max"):
        if user.plan_until is None or user.plan_until >= timezone.now():
            return True
    return False


def user_public(u):
    """Foydalanuvchining JS (app.js, profile.js, admin.js) kutadigan ko'rinishi."""
    return {
        "id": u.id,
        "name": f"{u.first_name} {u.last_name}".strip() or u.username,
        "firstName": u.first_name,
        "lastName": u.last_name,
        "email": u.email,
        "birthDate": u.birth_date.isoformat() if u.birth_date else "",
        "avatar": u.avatar,
        "assets": u.assets or [],
        "points": u.points,
        "isAdmin": u.is_staff,
        "plan": u.plan,
        "planUntil": fmt_dt(u.plan_until),
        "planActive": plan_active(u),
        "provider": u.provider,
        "createdAt": fmt_dt(u.date_joined),
        "lastSeen": fmt_dt(u.last_seen),
    }


def touch_last_seen(user, min_interval=60):
    """last_seen'ni yangilaydi (har so'rovda bazaga yozmaslik uchun — ko'pi bilan daqiqada bir marta)."""
    now = timezone.now()
    if user.last_seen is None or now - user.last_seen > timedelta(seconds=min_interval):
        user.last_seen = now
        user.save(update_fields=["last_seen"])


AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def save_avatar(user, file):
    """
    Profil rasmini MEDIA_ROOT/avatars/ ga saqlab, user.avatar'ga URL'ni
    yozadi (user.save()'ni chaqiruvchi o'zi bajaradi).
    Xato bo'lsa — foydalanuvchiga ko'rsatiladigan matn qaytaradi.
    """
    ext = os.path.splitext(file.name or "")[1].lower()
    if not (file.content_type or "").startswith("image/") or ext not in AVATAR_EXTS:
        return "Faqat rasm (jpg, png, webp, gif) yuklash mumkin."
    if file.size > AVATAR_MAX_BYTES:
        return "Rasm hajmi 5 MB dan oshmasligi kerak."
    name = default_storage.save(f"avatars/user_{user.id}_{int(time.time())}{ext}", file)
    user.avatar = default_storage.url(name)
    return None
