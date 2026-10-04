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


class EmailVerification(models.Model):
    """
    Ro'yxatdan o'tgan, lekin emailini hali TASDIQLAMAGAN foydalanuvchi
    uchun yuborilgan 6 xonali kod. Kodning o'zini emas, faqat uning
    HASH'ini saqlaymiz — baza o'g'irlansa ham kodlar ochilib qolmaydi.
    Email tasdiqlangach, bu yozuv o'chiriladi.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="email_verification")
    code_hash = models.CharField(max_length=128)
    sent_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"{self.user.email} (tasdiqlanmagan)"