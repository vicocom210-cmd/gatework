from datetime import date

from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer — bu DRF'ning "tarjimon"i: foydalanuvchidan kelgan
    ma'lumotni (JSON yoki forma/FormData — ikkalasini ham bir xil
    qabul qiladi) Python obyektiga aylantiradi va tekshiradi.

    MUHIM: haqiqiy sayt formasi "name" emas, balki "firstName",
    "lastName", "birthDate" kabi ALOHIDA maydonlarni yuboradi —
    shuning uchun ularni aynan shunday qabul qilamiz.
    """
    password = serializers.CharField(write_only=True, min_length=6, error_messages={"min_length": "Parol kamida 6 belgidan iborat bo'lsin."})
    firstName = serializers.CharField(write_only=True)
    lastName = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # MUHIM: CharField ishlatamiz (DateField emas) — chunki forma
    # bo'sh qolsa "" (bo'sh matn) yuboradi, DateField esa bo'sh
    # matnni String sifatida qabul qilib, xato berardi.
    birthDate = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["firstName", "lastName", "birthDate", "email", "password"]
        extra_kwargs = {"email": {"required": True, "allow_blank": False}}

    def validate_email(self, value):
        # MUHIM: email = username (unique). Tekshirmasak, bir xil email
        # bilan ikkinchi marta ro'yxatdan o'tishda bazada 500 xato chiqardi.
        value = value.strip().lower()
        if User.objects.filter(username__iexact=value).exists() or User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Bu email bilan allaqachon ro'yxatdan o'tilgan.")
        return value

    def validate_firstName(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Ismni kiriting.")
        return value[:150]

    def validate_birthDate(self, value):
        value = (value or "").strip()
        if not value:
            return ""
        try:
            date.fromisoformat(value[:10])
        except ValueError:
            raise serializers.ValidationError("Tug'ilgan sana noto'g'ri.")
        return value[:10]

    def create(self, validated_data):
        raw_birth = validated_data.get("birthDate") or ""
        birth_date = date.fromisoformat(raw_birth) if raw_birth else None
        user = User(
            username=validated_data["email"],  # email'ni username sifatida ishlatamiz
            email=validated_data["email"],
            first_name=validated_data.get("firstName", ""),
            last_name=validated_data.get("lastName", "").strip()[:150],
            birth_date=birth_date,
        )
        # MUHIM: parolni HECH QACHON to'g'ridan-to'g'ri saqlamang!
        # set_password() uni avtomatik xavfsiz hash qiladi (Flask'da
        # buni generate_password_hash() bilan qo'lda qilgan edingiz —
        # Django buni o'zi, ancha kuchliroq usulda bajaradi).
        user.set_password(validated_data["password"])
        user.save()
        return user