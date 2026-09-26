from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from users.utils import plan_active
from users.views import CSRFExemptSessionAuthentication
from .services import get_jobs_page
from .models import JobEvent


class JobsListView(APIView):
    """
    Eski Flask'dagi @app.route("/api/jobs") ekvivalenti.

    ?page=N berilsa — faqat N-sahifani {"jobs": [...], "page": N,
    "hasMore": bool} ko'rinishida qaytaradi (app.js vakansiyalarni
    shu tarzda bo'lib-bo'lib yuklaydi, shuning uchun birinchilari
    darhol chiqadi). page berilmasa — eski format: 1-sahifa massiv sifatida.
    """

    def get(self, request):
        query = request.query_params.get("query", "")
        sector = request.query_params.get("sector", "all")
        country = request.query_params.get("country", "ALL")
        raw_page = request.query_params.get("page")
        try:
            page = max(1, int(raw_page or 1))
        except ValueError:
            page = 1

        jobs, has_more = get_jobs_page(country=country, query=query, sector=sector, page=page)

        if raw_page is None:
            # MUHIM: eski app.js javobni TO'G'RIDAN-TO'G'RI massiv sifatida kutgan.
            return Response(jobs)
        return Response({"jobs": jobs, "page": page, "hasMore": has_more})


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

        if kind == "apply" and not plan_active(user):
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