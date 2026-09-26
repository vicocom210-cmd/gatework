from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from users.models import User
from . import services

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def fake_source(code):
    def fetch(query="", sector="all", page=1, page_size=25):
        fetch.calls += 1
        return [{"id": f"{code}-{page}-{i}", "country": code} for i in range(page_size)], page < 2
    fetch.calls = 0
    return fetch


@override_settings(CACHES=LOCMEM)
class JobsApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.de, self.se = fake_source("DE"), fake_source("SE")
        patcher = mock.patch.dict(services.SOURCES, {"DE": self.de, "SE": self.se})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_paged_response_and_cache(self):
        r = self.client.get("/api/jobs", {"country": "ALL", "page": 1}).json()
        self.assertEqual(len(r["jobs"]), 50)
        self.assertTrue(r["hasMore"])
        self.client.get("/api/jobs", {"country": "ALL", "page": 1})
        self.assertEqual((self.de.calls, self.se.calls), (1, 1))  # 2-marta keshdan

        r = self.client.get("/api/jobs", {"country": "DE", "page": 2}).json()
        self.assertFalse(r["hasMore"])
        self.assertEqual(self.se.calls, 1)  # faqat DE so'raldi

    def test_legacy_array_without_page(self):
        r = self.client.get("/api/jobs", {"country": "SE"}).json()
        self.assertIsInstance(r, list)


class ArchiveApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("a@x.uz", "a@x.uz", "secret123", plan="pro")
        self.client.force_login(self.user)

    def test_track_and_archive(self):
        job = {"id": "de-1", "title": "Ish", "country": "DE"}
        self.client.post("/api/track", {"kind": "apply", "job": job}, content_type="application/json")
        self.client.post("/api/track", {"kind": "view", "job": job}, content_type="application/json")
        self.client.post("/api/track", {"kind": "view", "job": job}, content_type="application/json")  # takror
        data = self.client.get("/api/archive").json()
        self.assertEqual((len(data["applies"]), len(data["views"])), (1, 1))
        self.client.post("/api/archive/clear", {"kind": "view"}, content_type="application/json")
        self.assertEqual(len(self.client.get("/api/archive").json()["views"]), 0)

    def test_archive_page_opens_for_logged_in_user(self):
        self.assertEqual(self.client.get("/archive/").status_code, 200)

    def test_apply_needs_plan(self):
        self.user.plan = "free"
        self.user.save()
        r = self.client.post("/api/track", {"kind": "apply", "job": {"id": "x"}}, content_type="application/json")
        self.assertEqual(r.status_code, 402)
