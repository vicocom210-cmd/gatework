from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from users.views import (
    RegisterView, VerifyEmailView, ResendCodeView, LoginView, LogoutView, MeView,
    AdminUsersListView, AdminUserDetailView, AdminStatsView,
)
from jobs.views import JobsListView, TrackView, ArchiveView, ArchiveClearView

urlpatterns = [
    # MUHIM: Django'ning O'Z ICHKI admin paneli endi "/django-admin/"da
    # joylashadi — chunki "/admin/"ni sizning saytingizning O'Z (Flask'dagi
    # kabi) admin sahifasi uchun bo'shatib qo'ydik (app.js allaqachon
    # href="/admin" deb yozilgan, shuni o'zgartirmaslik uchun).
    path("django-admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/jobs/", include("jobs.urls")),
    path("api/chat/", include("chat.urls")),
    path("", include("pages.urls")),

    # MUHIM: eski static/js/app.js "/api/jobs" ga OXIRIDA "/" siz
    # so'rov yuboradi. Yuqoridagi "api/jobs/" esa "/" ni talab qiladi
    # — bu ikkisining farqi Django'ni 301 (qayta yo'naltirish) qaytarishga
    # majbur qilgan, va ba'zan brauzer buni to'g'ri kuzatib bormagan.
    # Shuning uchun "/"siz versiyani ham to'g'ridan-to'g'ri ochamiz.
    path("api/jobs", JobsListView.as_view()),
    path("api/track", TrackView.as_view()),
    path("api/archive", ArchiveView.as_view()),
    path("api/archive/clear", ArchiveClearView.as_view()),

    # MUHIM: eski static/js/auth.js fayli aynan shu (eski Flask'dagi)
    # manzillarga so'rov yuboradi. JS kodini o'zgartirmaslik uchun,
    # xuddi o'sha view'larni shu manzillarda ham ochib qo'yamiz —
    # Django'da bitta view'ni bir nechta URL'ga ulash mumkin.
    path("api/register", RegisterView.as_view()),
    path("api/verify-email", VerifyEmailView.as_view()),
    path("api/resend-code", ResendCodeView.as_view()),
    path("api/login", LoginView.as_view()),
    path("api/logout", LogoutView.as_view()),
    path("api/me", MeView.as_view()),

    path("api/admin/users", AdminUsersListView.as_view()),
    path("api/admin/users/<int:uid>", AdminUserDetailView.as_view()),
    path("api/admin/stats", AdminStatsView.as_view()),
]

# MUHIM: yuklangan fayllarni (chat rasmlari/ovozlari) faqat DEBUG
# rejimida (development) shu tarzda ko'rsatamiz. Production'da bu
# boshqacha (Nginx orqali) bo'ladi — buni keyingi bosqichda ko'ramiz.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)