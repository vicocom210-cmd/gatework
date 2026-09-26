from django.conf import settings
from django.db import models

from users.utils import fmt_dt


class JobEvent(models.Model):
    """Eski Flask'dagi 'job_events' jadvalining Django ekvivalenti.
    Foydalanuvchi ishni ko'rganda ('view') yoki ariza tugmasini
    bosganda ('apply') shu yerga bitta qator yoziladi."""

    KIND_CHOICES = [("view", "Ko'rilgan"), ("apply", "Ariza")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_events")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    job_id = models.CharField(max_length=100)
    title = models.CharField(max_length=200, blank=True, default="")
    employer = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=5, blank=True, default="")
    url = models.CharField(max_length=800, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            # arxiv va admin statistikasi uchun
            models.Index(fields=["user", "kind", "created_at"], name="jobs_event_user_kind_idx"),
        ]

    def to_public(self):
        return {
            "id": self.id, "kind": self.kind, "jobId": self.job_id,
            "title": self.title, "employer": self.employer, "city": self.city,
            "country": self.country, "url": self.url,
            "createdAt": fmt_dt(self.created_at),
        }