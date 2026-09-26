from django.conf import settings
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.utils import fmt_dt, touch_last_seen, user_public
from users.views import CSRFExemptSessionAuthentication
from .models import Message


def _is_admin(user):
    return user.is_authenticated and user.is_staff


def _first_admin_id():
    row = User.objects.filter(is_staff=True).order_by("id").first()
    return row.id if row else None


def _thread_q(user_id):
    """
    Foydalanuvchi va ADMINLAR (istalgan is_staff) o'rtasidagi barcha xabarlar.

    MUHIM: avval xabarlar faqat "birinchi admin" bilan bog'langan edi —
    saytda ikkita admin bo'lsa, ikkinchisi foydalanuvchi xabarlarini
    ko'rmasdi, uning javobi esa foydalanuvchiga chiqmasdi. Endi barcha
    adminlar bitta umumiy "qabul qutisi"dan foydalanadi.
    """
    return (Q(sender_id=user_id, receiver__is_staff=True)
            | Q(sender__is_staff=True, receiver_id=user_id))


def _unread_for_admins(user_id=None):
    """Oddiy foydalanuvchilardan adminlarga kelgan, hali o'qilmagan xabarlar."""
    qs = Message.objects.filter(receiver__is_staff=True, sender__is_staff=False, is_read=False)
    return qs.filter(sender_id=user_id) if user_id else qs


def _user_public_mini(u):
    if not u:
        return None
    return {"id": u.id, "name": f"{u.first_name} {u.last_name}".strip() or u.username, "isAdmin": u.is_staff}


class ChatMessagesView(APIView):
    """Eski /api/chat/messages ekvivalenti."""

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)
        if user.is_staff:
            try:
                other_id = int(request.query_params.get("with", "0"))
            except ValueError:
                other_id = 0
            if not other_id:
                return Response({"ok": False, "error": "with parametri kerak."}, status=400)
        else:
            other_id = _first_admin_id()
            if other_id is None:
                # Saytda hali birorta admin yo'q — yozishma ham yo'q
                return Response({"ok": True, "me": user.id, "partner": None, "messages": []})
        touch_last_seen(user)

        try:
            after = int(request.query_params.get("after", "0"))
        except ValueError:
            after = 0
        client_id = other_id if user.is_staff else user.id
        thread = Message.objects.filter(_thread_q(client_id))
        if after:
            qs = list(thread.filter(id__gt=after).order_by("id")[:300])
        else:
            # Birinchi ochilishda ENG OXIRGI 300 ta xabar (eng eskilari emas)
            qs = list(thread.order_by("-id")[:300])[::-1]

        # Menga (yoki admin bo'lsam — adminlarga) kelganlarini o'qilgan deb belgilaymiz
        if user.is_staff:
            _unread_for_admins(client_id).update(is_read=True)
        else:
            Message.objects.filter(receiver_id=user.id, sender__is_staff=True, is_read=False).update(is_read=True)
        partner = User.objects.filter(id=other_id).first()
        return Response({
            "ok": True,
            "me": user.id,
            "partner": _user_public_mini(partner),
            "messages": [m.to_public() for m in qs],
        })


class ChatSendView(APIView):
    authentication_classes = [CSRFExemptSessionAuthentication]

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"ok": False, "error": "Avval kiring."}, status=status.HTTP_401_UNAUTHORIZED)
        text = (request.data.get("text") or "").strip()[:2000]
        file = request.FILES.get("file")
        if not text and not file:
            return Response({"ok": False, "error": "Xabar bo'sh."}, status=400)
        if file and file.size > settings.CHAT_MAX_UPLOAD:
            return Response({"ok": False, "error": "Fayl hajmi 25 MB dan oshmasligi kerak."}, status=400)

        if user.is_staff:
            try:
                to_id = int(request.data.get("to") or 0)
            except (TypeError, ValueError):
                to_id = 0
            if not to_id or not User.objects.filter(id=to_id).exists():
                return Response({"ok": False, "error": "Qabul qiluvchi topilmadi."}, status=400)
        else:
            to_id = _first_admin_id()
            if to_id is None:
                return Response({"ok": False, "error": "Hozircha admin yo'q — keyinroq urinib ko'ring."}, status=503)

        msg = Message(sender_id=user.id, receiver_id=to_id, text=text)
        if file:
            msg.attachment = file
            msg.attachment_name = file.name
            ctype = (file.content_type or "").split("/")[0]
            msg.attachment_type = ctype if ctype in ("image", "video", "audio") else "file"
        msg.save()
        touch_last_seen(user, min_interval=0)
        return Response({"ok": True, "message": msg.to_public()})


class ChatUnreadView(APIView):
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"ok": False, "count": 0}, status=status.HTTP_401_UNAUTHORIZED)
        if user.is_staff:
            n = _unread_for_admins().count()
        else:
            n = Message.objects.filter(receiver_id=user.id, is_read=False).count()
        return Response({"ok": True, "count": n})


class ChatThreadsView(APIView):
    """Faqat admin uchun: kim bilan yozishma bor."""

    def get(self, request):
        if not _is_admin(request.user):
            return Response({"ok": False}, status=status.HTTP_403_FORBIDDEN)
        out = []
        for u in User.objects.filter(is_staff=False):
            last = Message.objects.filter(_thread_q(u.id)).order_by("-id").first()
            unread = _unread_for_admins(u.id).count()
            # admin.js suhbat sarlavhasida email, tarif, onlayn holati va
            # tahrirlash oynasi uchun to'liq foydalanuvchi ma'lumotini ishlatadi
            item = user_public(u)
            item["lastText"] = (last.text if last and last.text else (f"📎 {last.attachment_type}" if last else None))
            item["lastAt"] = fmt_dt(last.created_at) if last else None
            item["unread"] = unread
            out.append(item)
        out.sort(key=lambda x: x["lastAt"] or "", reverse=True)
        return Response({"ok": True, "threads": out})
