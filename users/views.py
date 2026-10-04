from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from rest_framework.authentication import SessionAuthentication
import logging

from .models import User
from .serializers import RegisterSerializer
from .verification import check_code, resend_wait_seconds, send_code

logger = logging.getLogger(__name__)


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
        # Avval shu email bilan ro'yxatdan o'tib, lekin kodni TASDIQLAMAY
        # qolgan eski urinish bo'lsa — uni o'chiramiz, aks holda odam
        # qayta ro'yxatdan o'ta olmay qolardi.
        email = (request.data.get("email") or "").strip()
        if email:
            _unverified(email).delete()

        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            first = next(iter(serializer.errors.values()))[0]
            return Response({"ok": False, "error": str(first), "errors": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        try:
            send_code(user)
        except Exception:
            logger.exception("Tasdiqlash kodini yuborib bo'lmadi: %s", user.email)
            user.delete()
            return Response({"ok": False, "error": "Tasdiqlash kodini yuborib bo'lmadi. Keyinroq urinib ko'ring."},
                            status=status.HTTP_502_BAD_GATEWAY)
        return Response({"ok": True, "needVerify": True, "email": user.email}, status=status.HTTP_201_CREATED)


def _unverified(email):
    """Ro'yxatdan o'tgan, lekin emailini hali tasdiqlamagan foydalanuvchilar."""
    return User.objects.filter(username=email, is_active=False, email_verification__isnull=False)


def _auth_user(user):
    return {"id": user.id, "name": user.first_name, "email": user.email, "isAdmin": user.is_staff}


class VerifyEmailView(APIView):
    """Foydalanuvchi emailiga kelgan 6 xonali kodni tekshiradi va hisobni faollashtiradi."""
    authentication_classes = []

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        code = (request.data.get("code") or "").strip()
        user = _unverified(email).first()
        if user is None:
            return Response({"ok": False, "error": "Tasdiqlanmagan hisob topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        ok, error = check_code(user, code)
        if not ok:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save(update_fields=["is_active"])
        login(request, user)
        return Response({"ok": True, "user": _auth_user(user)})


class ResendCodeView(APIView):
    """Tasdiqlash kodini qayta yuboradi (60 soniyada bir martadan ko'p emas)."""
    authentication_classes = []

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        user = _unverified(email).first()
        if user is None:
            return Response({"ok": False, "error": "Tasdiqlanmagan hisob topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        wait = resend_wait_seconds(user)
        if wait:
            return Response({"ok": False, "error": f"Yangi kodni {wait} soniyadan keyin so'rashingiz mumkin.",
                             "wait": wait}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        try:
            send_code(user)
        except Exception:
            logger.exception("Tasdiqlash kodini qayta yuborib bo'lmadi: %s", user.email)
            return Response({"ok": False, "error": "Kodni yuborib bo'lmadi. Keyinroq urinib ko'ring."},
                            status=status.HTTP_502_BAD_GATEWAY)
        return Response({"ok": True})


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
            # authenticate() faol bo'lmagan (emailini tasdiqlamagan)
            # foydalanuvchini ham None qaytaradi. Parol to'g'ri bo'lsa,
            # unga "avval emailni tasdiqlang" deymiz va kod oynasini ochamiz.
            pending = _unverified(email).first()
            if pending and pending.check_password(password):
                if not resend_wait_seconds(pending):
                    try:
                        send_code(pending)
                    except Exception:
                        logger.exception("Tasdiqlash kodini yuborib bo'lmadi: %s", pending.email)
                return Response({"ok": False, "needVerify": True, "email": pending.email,
                                 "error": "Email hali tasdiqlanmagan. Pochtangizga yuborilgan kodni kiriting."},
                                status=status.HTTP_403_FORBIDDEN)
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


class MeView(APIView):
    """Eski Flask'dagi @app.route("/api/me") ekvivalenti."""
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)
        u = request.user
        return Response({"ok": True, "user": {
            "id": u.id, "name": u.first_name, "email": u.email,
            "plan": u.plan, "isAdmin": u.is_staff,
        }})