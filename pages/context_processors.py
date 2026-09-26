from django.conf import settings


def site(request):
    """
    Barcha shablonlarga umumiy ma'lumot: "Admin bilan bog'lanish" menyusidagi
    Telegram va email (base.html'da {{ CONTACT.telegram }}, {{ CONTACT.email }}).
    Qiymatlar .env'dan: CONTACT_TELEGRAM, CONTACT_EMAIL. Bo'sh bo'lsa — menyuda ko'rinmaydi.
    """
    return {"CONTACT": {"telegram": settings.CONTACT_TELEGRAM, "email": settings.CONTACT_EMAIL}}
