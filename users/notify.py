"""
users/notify.py
============================================================================
UZ: Tasdiqlash kodini yuborish — faqat email (Django/Gmail orqali). Gmail
    sozlanmagan bo'lsa — kod TERMINALda chiqadi (test rejimi).
RU: Отправка кода подтверждения — только email (через Django/Gmail). Без
    настроек Gmail код печатается в ТЕРМИНАЛ (тестовый режим).
EN: Sending the verification code — email only (via Django/Gmail). Without
    Gmail settings the code is printed to the TERMINAL (test mode).
DE: Versand des Bestätigungscodes — nur per E-Mail (über Django/Gmail). Ohne
    Gmail-Einstellungen wird der Code im TERMINAL ausgegeben (Testmodus).
============================================================================
"""
import secrets

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def generate_code():
    """
    UZ: 6 xonali tasodifiy kod (masalan "042517").
    RU: 6-значный случайный код.
    EN: A random 6-digit code.
    DE: Ein zufälliger 6-stelliger Code.
    """
    return f"{secrets.randbelow(1_000_000):06d}"  # secrets — taxmin qilib bo'lmaydi


def send_email_code(email, code):
    """
    UZ: Email'ga tasdiqlash kodini yuboradi. settings'да haqiqiy SMTP (Gmail)
        sozlangan bo'lsa — haqiqiy xat ketadi; bo'lmasa console backend kodni
        terminalда ko'rsatadi.
    RU: Отправляет код на email. Если настроен SMTP (Gmail) — уходит реальное
        письмо; иначе console backend печатает код в терминал.
    EN: Sends the code to the email. If real SMTP (Gmail) is configured a real
        message is sent; otherwise the console backend prints the code.
    DE: Sendet den Code an die E-Mail. Mit echtem SMTP (Gmail) geht eine echte
        Nachricht; sonst gibt das Console-Backend den Code aus.
    """
    # UZ: Spam filtrlari bir tilli, aniq mavzuli va oddiy matn + HTML ikkala
    #     variantli xatlarni yaxshiroq qabul qiladi.
    # EN: Spam filters treat single-language, clear-subject, text+HTML mail better.
    subject = f"{code} — Gate Work tasdiqlash kodingiz"
    text = (
        f"Assalomu alaykum!\n\n"
        f"Gate Work'da ro'yxatdan o'tishni yakunlash uchun tasdiqlash kodingiz: {code}\n\n"
        f"Kod 10 daqiqa amal qiladi. Agar siz ro'yxatdan o'tmagan bo'lsangiz, "
        f"bu xatga e'tibor bermang.\n\n"
        f"Hurmat bilan,\nGate Work jamoasi"
    )
    html = f"""<!doctype html>
<html lang="uz"><body style="margin:0;padding:24px;background:#f4f6f8;font-family:Arial,sans-serif;color:#1a1a1a;">
  <div style="max-width:480px;margin:0 auto;background:#ffffff;border-radius:12px;padding:32px;">
    <h2 style="margin:0 0 16px;font-size:20px;">Gate Work</h2>
    <p style="margin:0 0 16px;font-size:15px;">Assalomu alaykum! Ro'yxatdan o'tishni yakunlash uchun tasdiqlash kodingiz:</p>
    <p style="margin:0 0 16px;font-size:32px;font-weight:bold;letter-spacing:8px;text-align:center;">{code}</p>
    <p style="margin:0 0 8px;font-size:13px;color:#555555;">Kod 10 daqiqa amal qiladi.</p>
    <p style="margin:0;font-size:13px;color:#555555;">Agar siz ro'yxatdan o'tmagan bo'lsangiz, bu xatga e'tibor bermang.</p>
  </div>
</body></html>"""
    try:
        msg = EmailMultiAlternatives(subject, text, getattr(settings, "DEFAULT_FROM_EMAIL", None), [email])
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
        print(f"[Email yuborildi] {email}")
        return True
    except Exception as e:
        print(f"[Email yuborish xatosi] {e}  (kod: {code})")
        return False
