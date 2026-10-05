"""
config/local_settings.example.py
============================================================================
UZ: NAMUNA fayl. Haqiqiy kalitlarni bu yerga YOZMANG. Buning nusxasini olib,
    "local_settings.py" deb nomlang va o'sha nusxaga kalitlarni yozing:
        1) shu faylni nusxalang
        2) nomini local_settings.py qiling
        3) kalitlarни to'ldiring
    local_settings.py GitHub'ga chiqmaydi (.gitignore'da).
RU: ОБРАЗЕЦ. НЕ пишите сюда реальные ключи. Скопируйте этот файл, назовите
    "local_settings.py" и впишите ключи в копию.
EN: EXAMPLE file. Do NOT put real keys here. Copy it to "local_settings.py"
    and put the keys in that copy. local_settings.py is gitignored.
DE: BEISPIEL-Datei. KEINE echten Schlüssel hier. Kopieren Sie sie nach
    "local_settings.py" und tragen Sie die Schlüssel in der Kopie ein.
============================================================================
"""

# UZ: Adzuna — https://developer.adzuna.com/ (ro'yxatdan o'tib olinadi)
# RU: Adzuna — зарегистрируйтесь на developer.adzuna.com
# EN: Adzuna — register at developer.adzuna.com
# DE: Adzuna — auf developer.adzuna.com registrieren
ADZUNA_APP_ID = ""
ADZUNA_APP_KEY = ""

# UZ: Ixtiyoriy / RU: необязательно / EN: optional / DE: optional
EURES_API_KEY = ""
FINDAJOB_API_KEY = ""

# ============================================================================
# EMAIL (Gmail) — ro'yxatdan o'tish kodini yuborish uchun
# UZ: Gmail "app password" oling (2 bosqichli himoya yoqilган bo'lishi kerak):
#     https://myaccount.google.com/apppasswords  — 16 belgili parol beradi.
#     EMAIL_HOST_USER = to'liq gmail manzilingiz, EMAIL_HOST_PASSWORD = app password.
#     Bo'sh qoldirsangiz — kod haqiqiy email o'rniga terminalda chiqadi (test).
# RU: Создайте Gmail "app password" (нужна 2FA): myaccount.google.com/apppasswords
# EN: Create a Gmail "app password" (2FA required): myaccount.google.com/apppasswords
# DE: Gmail "App-Passwort" erstellen (2FA nötig): myaccount.google.com/apppasswords
# ============================================================================
EMAIL_HOST_USER = ""        # masalan / e.g. "gatework.uz@gmail.com"
EMAIL_HOST_PASSWORD = ""    # Gmail app password (16 belgi, probelsiz)
