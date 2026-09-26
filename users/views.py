import json
from datetime import date, datetime, timedelta

import requests
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Message
from jobs.models import JobEvent

from .models import User
from .serializers import RegisterSerializer
from .security import enforce_csrf, rate_limit
from .utils import save_avatar, touch_last_seen, user_public


def _first_error(errors):
    """Serializer xatolaridan birinchisini oddiy matn sifatida oladi (auth.js data.error'ni ko'rsatadi)."""
    for field, msgs in errors.items():
        msg = msgs[0] if isinstance(msgs, list) and msgs else msgs
        return str(msg)
    return "Ma'lumotlar noto'g'ri."


def _parse_date(value):
    """"YYYY-MM-DD" -> date. Bo'sh bo'lsa None. Noto'g'ri bo'lsa ValueError."""
    value = (value or "").strip()
    if not value:
        return None
    return date.fromisoformat(value[:10])


def _parse_assets(raw):
    """FormData'dan JSON matn ('["diploma","visa"]') yoki JSON'dan ro'yxat keladi."""
    if isinstance(raw, list):
        items = raw
    else:
        try:
            items = json.loads(raw or "[]")
        except (TypeError, ValueError):
            return None
    if not isinstance(items, list):
        return None
    return [str(x)[:50] for x in items][:30]


class RegisterView(APIView):
    # MUHIM: bu ochiq (login/register/logout) view'larda foydalanuvchi
    # hali kirmagan bo'lishi mumkin — DRF bunday holda CSRF'ni o'zi
    # tekshirmaydi. Shuning uchun enforce_csrf()ni qo'lda chaqiramiz.
    # Token'ni frontend X-CSRFToken sarlavhasida yuboradi (base.html).
    authentication_classes = []
    """
    Eski Flask'dagi @app.route("/api/register", methods=["POST"]) ning
    Django'dagi ekvivalenti. Muvaffaqiyatli bo'lsa — foydalanuvchi
    darhol tizimga kiritiladi (auth.js shundan keyin sahifani o'zgartiradi).
    """
    def post(self, request):
        enforce_csrf(request)
        rate_limit(request, "register", 10, 3600)
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"ok": False, "error": _first_error(serializer.errors), "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()

        avatar = request.FILES.get("avatar")
        if avatar and not save_avatar(user, avatar):
            user.save(update_fields=["avatar"])

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"ok": True, "user": user_public(user)}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = []
    """
    Eski Flask'dagi @app.route("/api/login", methods=["POST"]) ning
    ekvivalenti.

    MUHIM: bizning User modelimizda "username" — bu email manzilning
    o'zi (RegisterView'da shunday saqlagan edik). Shuning uchun
    authenticate() ga email'ni username sifatida beramiz.
    """
    def post(self, request):
        enforce_csrf(request)
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        # parolni taxmin qilib buzishdan himoya: IP+email bo'yicha 15 daqiqada 10 ta urinish
        rate_limit(request, "login", 10, 900, extra=email)

        user = authenticate(request, username=email, password=password)
        if user is None and email.lower() != email:
            user = authenticate(request, username=email.lower(), password=password)
        if user is None:
            return Response({"ok": False, "error": "Email yoki parol noto'g'ri"}, status=status.HTTP_401_UNAUTHORIZED)

        # login() — Flask'dagi session["user_id"] = user.id bilan bir xil
        # vazifani bajaradi, faqat Django buni o'zi, xavfsizroq qiladi.
        login(request, user)
        touch_last_seen(user, min_interval=0)
        return Response({"ok": True, "user": user_public(user)})


class LogoutView(APIView):
    authentication_classes = []

    def post(self, request):
        enforce_csrf(request)
        logout(request)
        return Response({"ok": True})


class MeView(APIView):
    """Eski Flask'dagi @app.route("/api/me") ekvivalenti."""
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)
        touch_last_seen(request.user)
        return Response({"ok": True, "user": user_public(request.user)})


class ProfileView(APIView):
    """Eski /api/profile — foydalanuvchi o'z profilini tahrirlaydi (profile.js)."""
    def post(self, request):
        u = request.user
        if not u.is_authenticated:
            return Response({"ok": False, "error": "Avval kiring."}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data

        first = (data.get("firstName") or "").strip()
        if "firstName" in data and not first:
            return Response({"ok": False, "error": "Ism bo'sh bo'lmasligi kerak."}, status=400)
        if "firstName" in data:
            u.first_name = first[:150]
        if "lastName" in data:
            u.last_name = (data.get("lastName") or "").strip()[:150]
        if "birthDate" in data:
            try:
                u.birth_date = _parse_date(data.get("birthDate"))
            except ValueError:
                return Response({"ok": False, "error": "Tug'ilgan sana noto'g'ri."}, status=400)
        if "assets" in data:
            assets = _parse_assets(data.get("assets"))
            if assets is None:
                return Response({"ok": False, "error": "Hujjatlar ro'yxati noto'g'ri."}, status=400)
            u.assets = assets

        password = data.get("password") or ""
        if password:
            if len(password) < 6:
                return Response({"ok": False, "error": "Parol kamida 6 belgidan iborat bo'lsin."}, status=400)
            u.set_password(password)

        avatar = request.FILES.get("avatar")
        if avatar:
            err = save_avatar(u, avatar)
            if err:
                return Response({"ok": False, "error": err}, status=400)

        u.save()
        if password:
            # Parol o'zgarganda Django sessiyani bekor qiladi — foydalanuvchini tizimda qoldiramiz.
            login(request, u, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"ok": True, "user": user_public(u)})


class RatingView(APIView):
    """Eski /api/rating — eng ko'p ball to'plagan foydalanuvchilar (rating.js)."""
    def get(self, request):
        qs = (User.objects.filter(is_active=True, is_staff=False, points__gt=0)
              .order_by("-points", "date_joined")[:50])
        users = []
        for i, u in enumerate(qs, start=1):
            users.append({
                "rank": i, "name": f"{u.first_name} {u.last_name}".strip() or "—",
                "firstName": u.first_name, "avatar": u.avatar, "points": u.points,
            })
        return Response({"ok": True, "users": users})


class PlansView(APIView):
    """Eski /api/plans — to'lov oynasida ko'rsatiladigan karta raqami (settings.PAYMENT_CARD)."""
    def get(self, request):
        return Response({"ok": True, "card": getattr(settings, "PAYMENT_CARD", "")})


class ActivityView(APIView):
    """Eski /api/activity — foydalanuvchi faolligi (masalan qidiruv). Hozircha faqat last_seen yangilanadi."""
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)
        touch_last_seen(request.user)
        return Response({"ok": True})


class GoogleVerifyView(APIView):
    """
    Eski /auth/google/verify — Google Sign-In'dan kelgan ID token'ni
    Google'ning o'zida tekshiradi, keyin foydalanuvchini topadi yoki
    yaratadi va tizimga kiritadi.
    """
    authentication_classes = []

    def post(self, request):
        enforce_csrf(request)
        rate_limit(request, "google", 30, 3600)
        credential = request.data.get("credential") or ""
        if not credential:
            return Response({"ok": False, "error": "Token yo'q."}, status=400)
        try:
            res = requests.get("https://oauth2.googleapis.com/tokeninfo",
                               params={"id_token": credential}, timeout=8)
            info = res.json() if res.ok else {}
        except Exception as e:
            print(f"[Google tekshiruv xatosi] {e}")
            return Response({"ok": False, "error": "Google bilan bog'lanib bo'lmadi."}, status=502)

        client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
        email = (info.get("email") or "").strip().lower()
        if (not info or info.get("aud") != client_id or not email
                or str(info.get("email_verified")).lower() != "true"):
            return Response({"ok": False, "error": "Google token noto'g'ri."}, status=401)

        user = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()
        if user is None:
            user = User(username=email, email=email, provider="google",
                        first_name=(info.get("given_name") or "")[:150],
                        last_name=(info.get("family_name") or "")[:150],
                        avatar=info.get("picture") or None)
            user.set_unusable_password()
            user.save()
        elif not user.is_active:
            return Response({"ok": False, "error": "Akkaunt bloklangan."}, status=403)

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        touch_last_seen(user, min_interval=0)
        return Response({"ok": True, "user": user_public(user)})


# ---------------------------- ADMIN ----------------------------

def _is_admin(user):
    return user.is_authenticated and user.is_staff


def _count_subquery(qs):
    return Coalesce(Subquery(qs.order_by().values("user_id" if qs.model is JobEvent else "sender_id")
                             .annotate(n=Count("id")).values("n")[:1]), 0)


def _with_counts(qs):
    """
    Har bir foydalanuvchiga arizalar, ko'rishlar va o'qilmagan xabarlar sonini
    qo'shadi. Alohida ichki so'rovlar (subquery) bilan — JOIN qilinsa, jadvallar
    bir-biriga ko'payib, katta bazada juda sekinlashadi.
    """
    return qs.annotate(
        n_applies=_count_subquery(JobEvent.objects.filter(user_id=OuterRef("pk"), kind="apply")),
        n_views=_count_subquery(JobEvent.objects.filter(user_id=OuterRef("pk"), kind="view")),
        n_unread=_count_subquery(Message.objects.filter(sender_id=OuterRef("pk"), is_read=False,
                                                        receiver_id__in=list(User.objects.filter(is_staff=True)
                                                                             .values_list("id", flat=True)))),
    )


def _admin_user_public(u):
    d = user_public(u)
    d["applies"] = getattr(u, "n_applies", 0)
    d["views"] = getattr(u, "n_views", 0)
    d["unread"] = getattr(u, "n_unread", 0)
    return d


class AdminUsersListView(APIView):
    def get(self, request):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        q = (request.query_params.get("q") or "").strip()
        qs = User.objects.all().order_by("-date_joined")
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
        total = qs.count()
        # ko'pi bilan 300 ta (eng yangilari) — qolganini qidiruv orqali topish mumkin
        out = [_admin_user_public(u) for u in _with_counts(qs)[:300]]
        return Response({"ok": True, "users": out, "total": total})


class AdminUserDetailView(APIView):
    def get_object(self, request, uid):
        return _with_counts(User.objects.filter(id=uid)).first()

    def get(self, request, uid):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        u = self.get_object(request, uid)
        if not u:
            return Response({"ok": False, "error": "Foydalanuvchi topilmadi."}, status=404)
        events = u.job_events.all()
        return Response({
            "ok": True,
            "user": _admin_user_public(u),
            # admin.js'dagi "Arxiv" oynasi aynan shu ma'lumotni kutadi
            "archive": {
                "applies": [e.to_public() for e in events.filter(kind="apply")[:200]],
                "views": [e.to_public() for e in events.filter(kind="view")[:200]],
            },
        })

    def post(self, request, uid):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        u = self.get_object(request, uid)
        if not u:
            return Response({"ok": False, "error": "Foydalanuvchi topilmadi."}, status=404)
        data = request.data

        if "firstName" in data:
            u.first_name = (data.get("firstName") or "").strip()[:150]
        if "lastName" in data:
            u.last_name = (data.get("lastName") or "").strip()[:150]
        if "email" in data:
            email = (data.get("email") or "").strip().lower()
            if not email or "@" not in email:
                return Response({"ok": False, "error": "Email noto'g'ri."}, status=400)
            taken = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exclude(id=u.id).exists()
            if taken:
                return Response({"ok": False, "error": "Bu email boshqa foydalanuvchida bor."}, status=400)
            u.email = email
            u.username = email
        if "birthDate" in data:
            try:
                u.birth_date = _parse_date(data.get("birthDate"))
            except ValueError:
                return Response({"ok": False, "error": "Tug'ilgan sana noto'g'ri."}, status=400)
        if "points" in data:
            try:
                u.points = max(0, int(data.get("points") or 0))
            except (TypeError, ValueError):
                return Response({"ok": False, "error": "Ball butun son bo'lishi kerak."}, status=400)
        if "assets" in data:
            assets = _parse_assets(data.get("assets"))
            if assets is None:
                return Response({"ok": False, "error": "Hujjatlar ro'yxati noto'g'ri."}, status=400)
            u.assets = assets
        if "plan" in data:
            plan = data.get("plan") or "free"
            if plan not in ("free", "pro", "max"):
                return Response({"ok": False, "error": "Tarif noto'g'ri."}, status=400)
            u.plan = plan
            if plan == "free":
                u.plan_until = None
            else:
                try:
                    until = _parse_date(data.get("planUntil"))
                except ValueError:
                    return Response({"ok": False, "error": "Sana noto'g'ri."}, status=400)
                if until:
                    # tanlangan kunning oxirigacha amal qiladi
                    u.plan_until = timezone.make_aware(datetime.combine(until, datetime.max.time()))
                else:
                    # sana berilmasa: PRO — 1 oy, MAX — 1 yil (to'lov oynasidagi narxlar kabi)
                    u.plan_until = timezone.now() + timedelta(days=30 if plan == "pro" else 365)
        if "isAdmin" in data and u.id != request.user.id:
            val = str(data.get("isAdmin")).lower()
            u.is_staff = val in ("1", "true", "on", "yes")

        new_password = (data.get("password") or "").strip()
        if new_password:
            if len(new_password) < 6:
                return Response({"ok": False, "error": "Parol kamida 6 belgidan iborat bo'lsin."}, status=400)
            u.set_password(new_password)

        avatar = request.FILES.get("avatar")
        if avatar:
            err = save_avatar(u, avatar)
            if err:
                return Response({"ok": False, "error": err}, status=400)

        u.save()
        return Response({"ok": True, "user": _admin_user_public(u)})

    def delete(self, request, uid):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        if uid == request.user.id:
            return Response({"ok": False, "error": "O'zingizni o'chira olmaysiz."}, status=400)
        u = User.objects.filter(id=uid).first()
        if not u:
            return Response({"ok": False, "error": "Foydalanuvchi topilmadi."}, status=404)
        u.delete()
        return Response({"ok": True})


class AdminStatsView(APIView):
    def get(self, request):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        staff = list(User.objects.filter(is_staff=True).values_list("id", flat=True))
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return Response({
            "ok": True,
            "users": User.objects.count(),
            "newToday": User.objects.filter(date_joined__gte=today_start).count(),
            "pro": User.objects.filter(plan="pro").count(),
            "max": User.objects.filter(plan="max").count(),
            "applies": JobEvent.objects.filter(kind="apply").count(),
            "views": JobEvent.objects.filter(kind="view").count(),
            "unread": Message.objects.filter(receiver_id__in=staff, is_read=False).exclude(sender_id__in=staff).count(),
            "online": User.objects.filter(last_seen__gte=now - timedelta(minutes=5)).count(),
        })
