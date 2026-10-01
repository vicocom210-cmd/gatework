from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from rest_framework.authentication import SessionAuthentication
from .models import User
from .serializers import RegisterSerializer


class CSRFExemptSessionAuthentication(SessionAuthentication):
    """
    Oddiy SessionAuthentication — FAQAT bitta farq bilan: CSRF
    tekshiruvini o'chiradi. Bu bizga ikkalasini ham beradi:
    (1) request.user haqiqiy tizimga kirgan foydalanuvchini ko'rsatadi
        (authentication_classes=[] bo'lsa, bu doim "Anonim" bo'lib
        qolar edi — bu esa admin tekshiruvini buzardi);
    (2) eski auth.js/admin.js CSRF token yubormasa ham, so'rov
        403 bilan rad etilmaydi.
    """
    def enforce_csrf(self, request):
        return  # hech narsa qilmaymiz — tekshiruvni o'tkazib yuboramiz


def admin_auth():
    return [CSRFExemptSessionAuthentication]


class RegisterView(APIView):
    # MUHIM (VAQTINCHA): DRF'ning SessionAuthentication'i har doim
    # o'zining ICHKI CSRF tekshiruvini bajaradi — bu @csrf_exempt
    # dekoratoriga BO'YSUNMAYDI (buni tajriba bilan aniqladik!).
    # Shuning uchun aynan shu ochiq (login/register/logout) view'lar
    # uchun autentifikatsiya sinflarini bo'shatib qo'yamiz — bu
    # Flask'dagi ASL xavfsizlik darajasi bilan bir xil. Xavfsizlik
    # bosqichida (keyinroq) buni to'g'ri yechimga almashtiramiz.
    authentication_classes = []
    """
    Eski Flask'dagi @app.route("/api/register", methods=["POST"]) ning
    Django'dagi ekvivalenti.
    """
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"ok": True, "user": {"id": user.id, "name": user.first_name, "email": user.email, "isAdmin": user.is_staff}},
                status=status.HTTP_201_CREATED,
            )
        return Response({"ok": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


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
        email = request.data.get("email", "")
        password = request.data.get("password", "")

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"ok": False, "error": "Email yoki parol noto'g'ri"}, status=status.HTTP_401_UNAUTHORIZED)

        # login() — Flask'dagi session["user_id"] = user.id bilan bir xil
        # vazifani bajaradi, faqat Django buni o'zi, xavfsizroq qiladi.
        login(request, user)
        return Response({"ok": True, "user": {"id": user.id, "name": user.first_name, "email": user.email, "isAdmin": user.is_staff}})


class LogoutView(APIView):
    authentication_classes = []
    def post(self, request):
        logout(request)
        return Response({"ok": True})


def _is_admin(user):
    return user.is_authenticated and user.is_staff


def _user_public(u):
    return {
        "id": u.id, "name": f"{u.first_name} {u.last_name}".strip() or u.username,
        "email": u.email, "isAdmin": u.is_staff, "plan": u.plan,
        "planUntil": u.plan_until.isoformat() if u.plan_until else None,
        "points": u.points, "avatar": u.avatar,
        "createdAt": u.date_joined.isoformat() if u.date_joined else None,
        "lastSeen": u.last_seen.isoformat() if u.last_seen else None,
        # MUHIM: bular hali 0 — chunki job_events/messages jadvallarini
        # keyingi darsda (kuzatuv va chat mavzusida) yaratamiz.
        "applies": 0, "views": 0, "unread": 0,
    }


class AdminUsersListView(APIView):
    authentication_classes = [CSRFExemptSessionAuthentication]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        q = (request.query_params.get("q") or "").strip().lower()
        qs = User.objects.all().order_by("-date_joined")
        out = []
        for u in qs:
            hay = f"{u.first_name} {u.last_name} {u.email}".lower()
            if q and q not in hay:
                continue
            out.append(_user_public(u))
        return Response({"ok": True, "users": out, "total": len(out)})


class AdminUserDetailView(APIView):
    authentication_classes = [CSRFExemptSessionAuthentication]

    def get_object(self, uid):
        try:
            return User.objects.get(id=uid)
        except User.DoesNotExist:
            return None

    def get(self, request, uid):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        u = self.get_object(uid)
        if not u:
            return Response({"ok": False, "error": "Foydalanuvchi topilmadi."}, status=404)
        return Response({"ok": True, "user": _user_public(u)})

    def post(self, request, uid):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        u = self.get_object(uid)
        if not u:
            return Response({"ok": False, "error": "Foydalanuvchi topilmadi."}, status=404)
        data = request.data
        if "firstName" in data:
            u.first_name = data.get("firstName") or ""
        if "lastName" in data:
            u.last_name = data.get("lastName") or ""
        if "email" in data:
            u.email = data.get("email")
            u.username = data.get("email")
        if "points" in data:
            u.points = max(0, int(data.get("points") or 0))
        if "plan" in data:
            u.plan = data.get("plan") or "free"
        if "isAdmin" in data and u.id != request.user.id:
            val = str(data.get("isAdmin")).lower()
            u.is_staff = val in ("1", "true", "on", "yes")
        new_password = (data.get("password") or "").strip()
        if new_password:
            u.set_password(new_password)
        u.save()
        return Response({"ok": True, "user": _user_public(u)})

    def delete(self, request, uid):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        if uid == request.user.id:
            return Response({"ok": False, "error": "O'zingizni o'chira olmaysiz."}, status=400)
        u = self.get_object(uid)
        if not u:
            return Response({"ok": False, "error": "Foydalanuvchi topilmadi."}, status=404)
        u.delete()
        return Response({"ok": True})


class AdminStatsView(APIView):
    authentication_classes = [CSRFExemptSessionAuthentication]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        from django.utils import timezone
        today = timezone.now().date()
        return Response({
            "ok": True,
            "users": User.objects.count(),
            "newToday": User.objects.filter(date_joined__date=today).count(),
            "pro": User.objects.filter(plan="pro").count(),
            "max": User.objects.filter(plan="max").count(),
            # MUHIM: keyingi darsda haqiqiy qiymatlarga almashtiramiz
            "applies": 0, "views": 0, "unread": 0, "online": 0,
        })


def _me_public(u):
    """
    UZ: Tizimga kirgan foydalanuvchining O'ZI haqidagi ma'lumot (profil
        sahifasi uchun). profile.js firstName/lastName/birthDate/points/
        assets/avatar maydonlarini kutadi — shuning uchun hammasini beramiz.
    RU: Данные о САМОМ вошедшем пользователе (для страницы профиля). profile.js
        ждёт firstName/lastName/birthDate/points/assets/avatar — отдаём всё.
    EN: Data about the logged-in user themselves (for the profile page).
        profile.js expects firstName/lastName/birthDate/points/assets/avatar,
        so we return all of them.
    DE: Daten über den angemeldeten Benutzer selbst (für die Profilseite).
        profile.js erwartet firstName/lastName/birthDate/points/assets/avatar.
    """
    return {
        "id": u.id,
        "name": f"{u.first_name} {u.last_name}".strip() or u.username,
        "firstName": u.first_name,
        "lastName": u.last_name,
        "birthDate": u.birth_date.isoformat() if u.birth_date else "",
        "email": u.email,
        "plan": u.plan,
        "isAdmin": u.is_staff,
        "avatar": u.avatar,
        "points": u.points or 0,
        "assets": u.assets or [],
    }


class MeView(APIView):
    """Eski Flask'dagi @app.route("/api/me") ekvivalenti."""
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"ok": True, "user": _me_public(request.user)})


class ProfileView(APIView):
    """
    UZ: /api/profile — foydalanuvchi o'z profilini tahrirlaydi (ism, familiya,
        tug'ilgan sana, parol, ko'nikmalar/assets va avatar rasmi). Avatar
        fayli media/avatars/ ichiga saqlanadi.
    RU: /api/profile — пользователь редактирует свой профиль (имя, фамилия,
        дата рождения, пароль, навыки/assets и аватар). Файл аватара
        сохраняется в media/avatars/.
    EN: /api/profile — the user edits their own profile (first/last name,
        birth date, password, skills/assets and avatar image). The avatar
        file is saved into media/avatars/.
    DE: /api/profile — der Benutzer bearbeitet sein Profil (Vor-/Nachname,
        Geburtsdatum, Passwort, Fähigkeiten/assets und Avatarbild). Die
        Avatar-Datei wird in media/avatars/ gespeichert.
    """
    authentication_classes = [CSRFExemptSessionAuthentication]

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"ok": False, "error": "Avval tizimga kiring."}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data
        if "firstName" in data:
            user.first_name = (data.get("firstName") or "").strip()
        if "lastName" in data:
            user.last_name = (data.get("lastName") or "").strip()
        # UZ: bo'sh sana -> None (xato bermasligi uchun).
        # RU: пустая дата -> None (чтобы не было ошибки).
        # EN: empty date -> None (to avoid an error).
        # DE: leeres Datum -> None (um Fehler zu vermeiden).
        if "birthDate" in data:
            user.birth_date = (data.get("birthDate") or "").strip() or None

        # UZ: assets — JSON matn ko'rinishida keladi (masalan '["visa"]').
        # RU: assets приходит в виде JSON-строки (например '["visa"]').
        # EN: assets arrives as a JSON string (e.g. '["visa"]').
        # DE: assets kommt als JSON-String (z. B. '["visa"]').
        if "assets" in data:
            import json
            raw = data.get("assets")
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, list):
                    user.assets = parsed
            except Exception:
                pass

        new_password = (data.get("password") or "").strip()
        if new_password:
            user.set_password(new_password)

        # UZ: avatar rasmi (ixtiyoriy) — media/avatars/ ichiga yozamiz.
        # RU: аватар (необязательно) — пишем в media/avatars/.
        # EN: avatar image (optional) — write it into media/avatars/.
        # DE: Avatarbild (optional) — in media/avatars/ schreiben.
        avatar_file = request.FILES.get("avatar")
        if avatar_file:
            import os
            from django.conf import settings
            folder = os.path.join(settings.MEDIA_ROOT, "avatars")
            os.makedirs(folder, exist_ok=True)
            ext = os.path.splitext(avatar_file.name)[1].lower() or ".png"
            fname = f"user_{user.id}{ext}"
            with open(os.path.join(folder, fname), "wb") as f:
                for chunk in avatar_file.chunks():
                    f.write(chunk)
            user.avatar = f"{settings.MEDIA_URL}avatars/{fname}"

        user.save()
        # UZ: parol o'zgargan bo'lsa, sessiya buzilmasligi uchun qayta login.
        # RU: если пароль изменён — перелогиниваем, чтобы не слетела сессия.
        # EN: if the password changed, re-login so the session is not dropped.
        # DE: bei Passwortänderung erneut anmelden, damit die Session bleibt.
        if new_password:
            login(request, user)
        return Response({"ok": True, "user": _me_public(user)})


class RatingView(APIView):
    """
    UZ: /api/rating — eng faol foydalanuvchilar reytingi (ballar bo'yicha).
    RU: /api/rating — рейтинг самых активных пользователей (по баллам).
    EN: /api/rating — the leaderboard of the most active users (by points).
    DE: /api/rating — die Rangliste der aktivsten Benutzer (nach Punkten).
    """
    def get(self, request):
        top = User.objects.order_by("-points", "-date_joined")[:50]
        users = []
        for i, u in enumerate(top, start=1):
            users.append({
                "rank": i,
                "name": f"{u.first_name} {u.last_name}".strip() or u.username,
                "firstName": u.first_name,
                "lastName": u.last_name,
                "avatar": u.avatar,
                "points": u.points or 0,
            })
        return Response({"ok": True, "users": users})


class ActivityView(APIView):
    """
    UZ: /api/activity — foydalanuvchi faolligini belgilaydi (last_seen'ni
        yangilaydi). app.js qidiruv/bosish paytida 'ping' yuboradi.
    RU: /api/activity — отмечает активность пользователя (обновляет last_seen).
        app.js шлёт 'ping' при поиске/кликах.
    EN: /api/activity — marks the user as active (updates last_seen). app.js
        sends a 'ping' on search/clicks.
    DE: /api/activity — markiert den Benutzer als aktiv (aktualisiert
        last_seen). app.js sendet bei Suche/Klicks einen 'ping'.
    """
    authentication_classes = [CSRFExemptSessionAuthentication]

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)
        from django.utils import timezone
        user.last_seen = timezone.now()
        user.save(update_fields=["last_seen"])
        return Response({"ok": True})