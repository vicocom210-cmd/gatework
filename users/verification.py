"""
Email orqali tasdiqlash: 6 xonali kod yaratish, yuborish va tekshirish.

Kod Gmail (SMTP) orqali yuboriladi. Sozlamalar .env faylida turadi
(qarang: .env.example). Agar .env'da parol bo'lmasa, Django kodni
xat o'rniga SERVER KONSOLIGA chiqaradi — sinash uchun qulay.
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import EmailVerification

CODE_TTL = timedelta(minutes=10)         # kod shuncha vaqt amal qiladi
RESEND_COOLDOWN = timedelta(seconds=60)  # qayta yuborish oralig'i
MAX_ATTEMPTS = 5                         # noto'g'ri kiritishlar chegarasi


def _hash(code):
    return salted_hmac("users.email-code", code).hexdigest()


def send_code(user):
    """Yangi kod yaratadi, uni saqlaydi va foydalanuvchi emailiga yuboradi."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    EmailVerification.objects.update_or_create(
        user=user,
        defaults={"code_hash": _hash(code), "sent_at": timezone.now(), "attempts": 0},
    )
    minutes = int(CODE_TTL.total_seconds() // 60)
    send_mail(
        subject=f"Gate Work tasdiqlash kodi: {code}",
        message=(
            f"Salom, {user.first_name or user.email}!\n\n"
            f"Gate Work'da ro'yxatdan o'tishni yakunlash uchun tasdiqlash kodingiz: {code}\n\n"
            f"Kod {minutes} daqiqa amal qiladi. Agar siz ro'yxatdan o'tmagan bo'lsangiz, "
            f"bu xatga e'tibor bermang."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def resend_wait_seconds(user):
    """Qayta yuborishga hali necha soniya qolganini qaytaradi (0 — hozir mumkin)."""
    v = getattr(user, "email_verification", None)
    if v is None:
        return 0
    left = (v.sent_at + RESEND_COOLDOWN - timezone.now()).total_seconds()
    return max(0, int(left) + 1) if left > 0 else 0


def check_code(user, code):
    """
    Kodni tekshiradi. (True, None) yoki (False, "xato matni") qaytaradi.
    Muvaffaqiyatli bo'lsa, tasdiqlash yozuvini o'chiradi.
    """
    v = getattr(user, "email_verification", None)
    if v is None:
        return False, "Tasdiqlash kodi topilmadi. Yangi kod so'rang."
    if timezone.now() > v.sent_at + CODE_TTL:
        return False, "Kodning muddati tugagan. Yangi kod so'rang."
    if v.attempts >= MAX_ATTEMPTS:
        return False, "Juda ko'p noto'g'ri urinish. Yangi kod so'rang."

    if not constant_time_compare(v.code_hash, _hash(str(code).strip())):
        v.attempts += 1
        v.save(update_fields=["attempts"])
        left = MAX_ATTEMPTS - v.attempts
        if left <= 0:
            return False, "Juda ko'p noto'g'ri urinish. Yangi kod so'rang."
        return False, f"Kod noto'g'ri. Yana {left} ta urinish qoldi."

    v.delete()
    return True, None
