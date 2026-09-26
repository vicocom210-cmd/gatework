from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    """
    Django'ning tayyor UserAdmin'idan meros olamiz (bu bizga parol
    hashlash, "Personal info" bo'limlari kabi tayyor narsalarni beradi),
    va faqat ro'yxatda ko'rinadigan ustunlarga o'zimizning yangi
    maydonlarimizni (plan, points) qo'shamiz.
    """
    list_display = ("username", "email", "plan", "points", "is_staff", "date_joined")
    list_filter = ("plan", "provider", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    # Tayyor UserAdmin'dagi bo'limlarga bizning yangi maydonlarimizni qo'shamiz
    fieldsets = UserAdmin.fieldsets + (
        ("Gate Work ma'lumotlari", {
            "fields": ("provider", "avatar", "birth_date", "assets", "points", "plan", "plan_until", "last_seen"),
        }),
    )


admin.site.register(User, CustomUserAdmin)