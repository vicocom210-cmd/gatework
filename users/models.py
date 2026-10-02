from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Bizning maxsus foydalanuvchi modelimiz. AbstractUser'dan meros
    oladi — ya'ni username, email, password, first_name, last_name,
    is_staff, is_superuser kabi maydonlar TAYYOR keladi. Biz faqat
    ESKI Flask loyihamizda bo'lgan QO'SHIMCHA maydonlarni yozamiz.
    """

    # Eski jadvaldagi "provider" — email orqalimi, Google orqalimi
    PROVIDER_CHOICES = [
        ("email", "Email"),
        ("google", "Google"),
    ]
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="email")

    avatar = models.CharField(max_length=255, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    # UZ/RU/EN/DE: foydalanuvchi telefon raqami (tasdiqlangan)
    phone = models.CharField(max_length=20, blank=True, default="")

    # Eski jadvalda "assets" JSON matn (masalan '["diploma","visa"]') edi.
    # Django'da buni to'g'ridan-to'g'ri ro'yxat sifatida saqlaydigan
    # maydon bor — JSONField. Endi json.dumps/json.loads yozish shart
    # emas, Django o'zi bajaradi.
    assets = models.JSONField(default=list, blank=True)

    points = models.IntegerField(default=0)
    last_seen = models.DateTimeField(blank=True, null=True)

    PLAN_CHOICES = [
        ("free", "Free"),
        ("pro", "PRO"),
        ("max", "MAX"),
    ]
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default="free")
    plan_until = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.email or self.username


class PendingSignup(models.Model):
    """
    UZ: Vaqtinchalik ro'yxatdan o'tish yozuvi. Foydalanuvchi forma to'ldirganда
         hali User YARATILMAYDI — avval shu yerga yoziladi va email/telefonga
        kod yuboriladi. Ikkala kod ham to'g'ri kiritilса, User yaratiladi va bu
        yozuv o'chiriladi. Parol allaqachon HASH qilinган holda saqlanadi
        (ochiq parol saqlanmaydi).
    RU: Временная запись регистрации. Пока пользователь не подтвердит коды из
        email/телефона, User НЕ создаётся. Пароль хранится уже ХЕШИРОВАННЫМ.
    EN: A temporary signup record. The User is NOT created until the email/phone
        codes are confirmed. The password is stored already HASHED (never plain).
    DE: Ein temporärer Registrierungseintrag. Der User wird erst nach Bestätigung
        der E-Mail-/Telefon-Codes erstellt. Das Passwort wird bereits GEHASHT
        gespeichert (nie im Klartext).
    """
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    birth_date = models.DateField(blank=True, null=True)
    password = models.CharField(max_length=255)  # UZ: HASH qilingan parol / EN: hashed password

    email_code = models.CharField(max_length=6)
    phone_code = models.CharField(max_length=6, blank=True, default="")
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    attempts = models.IntegerField(default=0)   # UZ: noto'g'ri urinishlar / EN: wrong attempts
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PendingSignup({self.email})"