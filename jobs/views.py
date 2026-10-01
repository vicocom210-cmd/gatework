from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from users.views import CSRFExemptSessionAuthentication
from .services import get_jobs, list_sources
from .models import JobEvent


def _plan_active(user):
    """Tarif hali kuchidami? Muddati o'tmagan pro/max, yoki admin."""
    if user.is_staff:
        return True
    if user.plan in ("pro", "max"):
        if user.plan_until is None or user.plan_until >= timezone.now():
            return True
    return False


class JobsListView(APIView):
    """
    UZ: /api/jobs — ishlar ro'yxati. Endi 'source' (manba) filtrini ham
        qo'llaydi: frontend qaysi tugmani bossa, faqat o'sha manba keladi.
        Barcha mantiq services.get_jobs() dispetcherida.
    RU: /api/jobs — список вакансий. Теперь поддерживает фильтр 'source':
        при нажатии кнопки приходит только выбранный источник. Вся логика
        в диспетчере services.get_jobs().
    EN: /api/jobs — the jobs list. Now also supports the 'source' filter:
        whichever button the frontend clicks, only that source comes back.
        All logic lives in the services.get_jobs() dispatcher.
    DE: /api/jobs — die Jobliste. Unterstützt jetzt den 'source'-Filter:
        je nach angeklicktem Button kommt nur diese Quelle zurück. Die
        gesamte Logik steckt im Dispatcher services.get_jobs().
    """

    def get(self, request):
        query = request.query_params.get("query", "")
        sector = request.query_params.get("sector", "all")
        country = request.query_params.get("country", "ALL")
        source = request.query_params.get("source", "all")

        jobs = get_jobs(query=query, sector=sector, country=country, source=source)

        # UZ: eski app.js javobni TO'G'RIDAN-TO'G'RI massiv sifatida kutadi.
        # RU: старый app.js ждёт ответ НАПРЯМУЮ как массив.
        # EN: the old app.js expects the response DIRECTLY as an array.
        # DE: das alte app.js erwartet die Antwort DIREKT als Array.
        return Response(jobs)


class SourcesView(APIView):
    """
    UZ: /api/sources — manba filtri tugmalari uchun ro'yxat. Har bir manba
        nomi, davlatlari va 'ready' (kalit bor-yo'qligi) belgisi bilan.
    RU: /api/sources — список для кнопок фильтра источников. С именем,
        странами и признаком 'ready' (есть ли ключ).
    EN: /api/sources — the list for the source-filter buttons. With each
        source's name, countries and a 'ready' flag (whether a key exists).
    DE: /api/sources — die Liste für die Quellen-Filter-Buttons. Mit Name,
        Ländern und einem 'ready'-Flag (ob ein Schlüssel vorhanden ist).
    """

    def get(self, request):
        return Response({"ok": True, "sources": list_sources()})


class TrackView(APIView):
    """Eski /api/track ekvivalenti — 'view' yoki 'apply' voqeasini yozadi."""
    authentication_classes = [CSRFExemptSessionAuthentication]

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)

        body = request.data
        kind = body.get("kind")
        job = body.get("job") or {}
        job_id = str(job.get("id") or "").strip()
        if kind not in ("view", "apply") or not job_id:
            return Response({"ok": False, "error": "Noto'g'ri so'rov."}, status=400)

        if kind == "apply" and not _plan_active(user):
            return Response({"ok": False, "error": "plan_required"}, status=402)

        if kind == "view":
            one_day_ago = timezone.now() - timedelta(days=1)
            dup = JobEvent.objects.filter(
                user=user, kind="view", job_id=job_id, created_at__gte=one_day_ago
            ).exists()
            if dup:
                return Response({"ok": True, "dup": True})

        JobEvent.objects.create(
            user=user, kind=kind, job_id=job_id,
            title=str(job.get("title") or "")[:200],
            employer=str(job.get("employer") or "")[:200],
            city=str(job.get("city") or "")[:100],
            country=str(job.get("country") or "")[:5],
            url=str(job.get("url") or "")[:800],
        )
        if kind == "apply":
            user.points = (user.points or 0) + 5
            user.save(update_fields=["points"])
        return Response({"ok": True})


class ArchiveView(APIView):
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)
        views = JobEvent.objects.filter(user=user, kind="view")[:200]
        applies = JobEvent.objects.filter(user=user, kind="apply")[:200]
        return Response({
            "ok": True,
            "views": [e.to_public() for e in views],
            "applies": [e.to_public() for e in applies],
        })


class ArchiveClearView(APIView):
    authentication_classes = [CSRFExemptSessionAuthentication]

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"ok": False}, status=status.HTTP_401_UNAUTHORIZED)
        kind = request.data.get("kind")
        qs = JobEvent.objects.filter(user=user)
        if kind in ("view", "apply"):
            qs = qs.filter(kind=kind)
        qs.delete()
        return Response({"ok": True})