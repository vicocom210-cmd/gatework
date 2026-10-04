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
    password = serializers.CharField(write_only=True, min_length=6)
    firstName = serializers.CharField(write_only=True)
    lastName = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # MUHIM: CharField ishlatamiz (DateField emas) — chunki forma
    # bo'sh qolsa "" (bo'sh matn) yuboradi, DateField esa bo'sh
    # matnni String sifatida qabul qilib, xato berardi.
    birthDate = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["firstName", "lastName", "birthDate", "email", "password"]
        # AbstractUser'da email ixtiyoriy — ro'yxatdan o'tishda esa majburiy.
        extra_kwargs = {"email": {"required": True, "allow_blank": False}}

    def validate_email(self, value):
        # email = username, username esa yagona bo'lishi shart. Buni oldindan
        # tekshirmasak, baza IntegrityError (500) qaytarardi.
        value = value.strip()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu email bilan hisob allaqachon mavjud.")
        return value

    def create(self, validated_data):
        birth_date = validated_data.get("birthDate") or None
        user = User(
            username=validated_data["email"],  # email'ni username sifatida ishlatamiz
            email=validated_data["email"],
            first_name=validated_data.get("firstName", ""),
            last_name=validated_data.get("lastName", ""),
            birth_date=birth_date,
            # Email kod orqali tasdiqlanmaguncha hisob faol emas —
            # bunday foydalanuvchi tizimga kira olmaydi.
            is_active=False,
        )
        # MUHIM: parolni HECH QACHON to'g'ridan-to'g'ri saqlamang!
        # set_password() uni avtomatik xavfsiz hash qiladi (Flask'da
        # buni generate_password_hash() bilan qo'lda qilgan edingiz —
        # Django buni o'zi, ancha kuchliroq usulda bajaradi).
        user.set_password(validated_data["password"])
        user.save()
        return user