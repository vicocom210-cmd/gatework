"""
users/notify.py
============================================================================
UZ: Tasdiqlash kodlarini yuborish — email (Django orqali) va SMS (Eskiz.uz
    orqali, kalit bo'lsa). Kalit/sozlama bo'lmasa — kod TERMINALda chiqadi
    (test rejimi), shunda ishlab chiqish paytida ham sinab ko'rsa bo'ladi.
RU: Отправка кодов подтверждения — email (через Django) и SMS (через Eskiz.uz,
    если есть ключ). Без ключа код печатается в ТЕРМИНАЛ (тестовый режим).
EN: Sending verification codes — email (via Django) and SMS (via Eskiz.uz when
    a key is set). Without a key the code is printed to the TERMINAL (test mode).
DE: Versand von Bestätigungscodes — E-Mail (über Django) und SMS (über Eskiz.uz,
    wenn ein Schlüssel vorhanden ist). Ohne Schlüssel wird der Code im TERMINAL
    ausgegeben (Testmodus).
============================================================================
"""
import os
import random

import requests
from django.conf import settings
from django.core.mail import send_mail


def generate_code():
    """
    UZ: 6 xonali tasodifiy kod (masalan "042517").
    RU: 6-значный случайный код.
    EN: A random 6-digit code.
    DE: Ein zufälliger 6-stelliger Code.
    """
    return f"{random.randint(0, 999999):06d}"


def _get(name):
    val = os.environ.get(name) or getattr(settings, name, "")
    return (val or "").strip()


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
    subject = "Gate Work — tasdiqlash kodi / verification code"
    body = (
        f"Assalomu alaykum!\n\n"
        f"Gate Work ro'yxatdan o'tish uchun tasdiqlash kodingiz: {code}\n"
        f"Kod 10 daqiqa amal qiladi.\n\n"
        f"Your Gate Work verification code: {code} (valid for 10 minutes).\n"
    )
    try:
        send_mail(
            subject,
            body,
            getattr(settings, "DEFAULT_FROM_EMAIL", None),
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"[Email yuborish xatosi] {e}  (kod: {code})")
        return False


def send_sms(phone, code):
    """
    UZ: Telefon raqamга SMS kod yuboradi. Eskiz.uz kaliti (ESKIZ_EMAIL +
        ESKIZ_PASSWORD) sozlangan bo'lsa — haqiqiy SMS; bo'lmasa kod TERMINALda
        chiqadi (test rejimi). Shunday qilib kalitsiz ham sinab ko'rsa bo'ladi.
    RU: Отправляет SMS-код. Если настроен Eskiz.uz (ESKIZ_EMAIL + ESKIZ_PASSWORD)
        — реальная SMS; иначе код печатается в ТЕРМИНАЛ (тестовый режим).
    EN: Sends an SMS code. If Eskiz.uz is configured (ESKIZ_EMAIL +
        ESKIZ_PASSWORD) a real SMS goes out; otherwise the code is printed to the
        TERMINAL (test mode).
    DE: Sendet einen SMS-Code. Mit Eskiz.uz (ESKIZ_EMAIL + ESKIZ_PASSWORD) echte
        SMS; sonst wird der Code im TERMINAL ausgegeben (Testmodus).
    """
    email = _get("ESKIZ_EMAIL")
    password = _get("ESKIZ_PASSWORD")
    text = f"Gate Work tasdiqlash kodi: {code}"

    # UZ: Kalit yo'q bo'lsa — test rejimi: kodni terminalga chiqaramiz.
    # RU: Нет ключа — тестовый режим: печатаем код в терминал.
    # EN: No key — test mode: print the code to the terminal.
    # DE: Kein Schlüssel — Testmodus: Code im Terminal ausgeben.
    if not email or not password:
        print(f"[SMS TEST REJIMI] {phone} -> {text}")
        return True

    # UZ: Eskiz.uz — O'zbekiston SMS shlyuzi. Avval token olamiz, keyin yuboramiz.
    # RU: Eskiz.uz — SMS-шлюз Узбекистана. Сначала токен, затем отправка.
    # EN: Eskiz.uz — Uzbekistan SMS gateway. Get a token first, then send.
    # DE: Eskiz.uz — SMS-Gateway Usbekistans. Erst Token, dann senden.
    try:
        tok_res = requests.post(
            "https://notify.eskiz.uz/api/auth/login",
            data={"email": email, "password": password},
            timeout=10,
        )
        tok_res.raise_for_status()
        token = (tok_res.json().get("data") or {}).get("token")
        if not token:
            print("[Eskiz] token olinmadi")
            return False

        # UZ: raqamни faqat raqamlar ko'rinishiga keltiramiz (998901234567).
        # RU: приводим номер к цифрам (998901234567).
        # EN: normalize the phone to digits (998901234567).
        # DE: Nummer auf Ziffern normalisieren (998901234567).
        digits = "".join(ch for ch in phone if ch.isdigit())
        res = requests.post(
            "https://notify.eskiz.uz/api/message/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            data={"mobile_phone": digits, "message": text, "from": "4546"},
            timeout=10,
        )
        res.raise_for_status()
        return True
    except Exception as e:
        print(f"[SMS yuborish xatosi] {e}  (kod: {code})")
        return False
