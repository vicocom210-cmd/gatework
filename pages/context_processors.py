"""
pages/context_processors.py
============================================================================
UZ: "Context processor" — har bir HTML sahifaga avtomatik qo'shiladigan
    ma'lumot. Shu yerda biz CONTACT (aloqa) ma'lumotlarini beramiz: Telegram
    admin, Telegram kanal, Instagram va Gmail. base.html shu qiymatlardan
    foydalanadi. Bitta joyni o'zgartirsangiz — butun saytda o'zgaradi.
RU: "Context processor" — данные, автоматически добавляемые на каждую HTML-
    страницу. Здесь мы передаём контакты CONTACT: Telegram-админ, Telegram-
    канал, Instagram и Gmail. base.html использует эти значения. Меняете в
    одном месте — меняется на всём сайте.
EN: A "context processor" — data added automatically to every HTML page.
    Here we provide the CONTACT info: Telegram admin, Telegram channel,
    Instagram and Gmail. base.html uses these values. Change it in one place
    and it changes across the whole site.
DE: Ein "Context Processor" — Daten, die jeder HTML-Seite automatisch
    hinzugefügt werden. Hier liefern wir die CONTACT-Infos: Telegram-Admin,
    Telegram-Kanal, Instagram und Gmail. base.html nutzt diese Werte. Einmal
    ändern — überall auf der Seite geändert.
============================================================================
"""
from urllib.parse import quote


def contact(request):
    """
    UZ: Aloqa havolalarini tayyor ko'rinishda qaytaradi. Gmail uchun to'g'ridan-
        to'g'ri "xat yozish" (compose) oynasini ochadigan havola yasaymiz —
        shunda oddiy google.com emas, balki xat yozish oynasi ochiladi.
    RU: Возвращает готовые ссылки для контактов. Для Gmail формируем ссылку,
        открывающую окно "написать письмо" (compose) — чтобы открывался не
        просто google.com, а окно написания письма.
    EN: Returns ready-to-use contact links. For Gmail we build a link that
        opens the "compose" window directly — so it opens an email draft
        instead of just google.com.
    DE: Gibt fertige Kontaktlinks zurück. Für Gmail bauen wir einen Link, der
        direkt das "Verfassen"-Fenster öffnet — nicht einfach google.com.
    """
    email = "gatework.uz@gmail.com"
    subject = quote("Gate Work")
    return {
        "CONTACT": {
            # UZ: Telegram foydalanuvchi nomlari (@ belgisisiz).
            # RU: имена пользователей Telegram (без @).
            # EN: Telegram usernames (without the @).
            # DE: Telegram-Benutzernamen (ohne @).
            "telegram_admin": "gatework_admin",
            "telegram_channel": "gatework_uz",
            "instagram": "gatework.uz",
            "email": email,
            # UZ: Gmail "xat yozish" havolasi (compose) — oynani to'g'ridan ochadi.
            # RU: ссылка Gmail "написать письмо" (compose) — сразу открывает окно.
            # EN: Gmail "compose" link — opens the draft window directly.
            # DE: Gmail-"Verfassen"-Link (compose) — öffnet das Fenster direkt.
            "gmail_compose": f"https://mail.google.com/mail/?view=cm&fs=1&to={email}&su={subject}",
        }
    }
