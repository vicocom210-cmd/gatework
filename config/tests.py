"""Production uchun muhim himoyalarning testlari."""
import threading
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext

from chat.models import Message
from jobs import services
from users.models import User

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM)
class CsrfTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("u@x.uz", "u@x.uz", "secret123")
        self.client = Client(enforce_csrf_checks=True)

    def _token(self):
        self.client.get("/")  # sahifa csrftoken cookie'sini o'rnatadi
        return self.client.cookies["csrftoken"].value

    def test_login_without_token_is_rejected(self):
        r = self.client.post("/api/login", {"email": "u@x.uz", "password": "secret123"}, content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertIn("CSRF", r.json()["error"])

    def test_login_and_post_with_token_work(self):
        token = self._token()
        r = self.client.post("/api/login", {"email": "u@x.uz", "password": "secret123"},
                             content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)
        # login'dan keyin token yangilanadi — JS uni cookie'dan oladi
        token = self.client.cookies["csrftoken"].value
        r = self.client.post("/api/profile", {"firstName": "Ali"}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)
        r = self.client.post("/api/profile", {"firstName": "Ali"})  # tokensiz — rad etiladi
        self.assertEqual(r.status_code, 403)


@override_settings(CACHES=LOCMEM)
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user("u@x.uz", "u@x.uz", "secret123")

    def test_login_bruteforce_is_throttled(self):
        for _ in range(10):
            r = self.client.post("/api/login", {"email": "u@x.uz", "password": "xato"}, content_type="application/json")
            self.assertEqual(r.status_code, 401)
        r = self.client.post("/api/login", {"email": "u@x.uz", "password": "secret123"}, content_type="application/json")
        self.assertEqual(r.status_code, 429)
        self.assertIn("urinish", r.json()["error"])


class ChatUploadTests(TestCase):
    def test_html_upload_is_rejected(self):
        User.objects.create_user("a", "a@x.uz", "secret123", is_staff=True)
        user = User.objects.create_user("u@x.uz", "u@x.uz", "secret123")
        self.client.force_login(user)
        bad = SimpleUploadedFile("x.html", b"<script>alert(1)</script>", content_type="text/html")
        r = self.client.post("/api/chat/send", {"text": "", "file": bad})
        self.assertEqual(r.status_code, 400)


class QueryCountTests(TestCase):
    """Foydalanuvchilar ko'paysa ham so'rovlar soni o'smasligi kerak."""

    def test_threads_and_admin_list_use_constant_queries(self):
        admin = User.objects.create_user("a", "a@x.uz", "secret123", is_staff=True)
        users = [User.objects.create_user(f"u{i}@x.uz", f"u{i}@x.uz", "p") for i in range(30)]
        Message.objects.bulk_create([Message(sender=u, receiver=admin, text="hi") for u in users])
        self.client.force_login(admin)
        for url in ("/api/chat/threads", "/api/admin/users"):
            with CaptureQueriesContext(connection) as q:
                r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertLess(len(q), 10, f"{url}: {len(q)} ta so'rov")
        self.assertEqual(len(self.client.get("/api/chat/threads").json()["threads"]), 30)


@override_settings(CACHES=LOCMEM)
class StampedeTests(TransactionTestCase):
    def test_concurrent_requests_hit_api_once(self):
        cache.clear()
        calls = []

        def slow_fetch(query="", sector="all", page=1, page_size=25):
            calls.append(1)
            import time
            time.sleep(0.5)
            return [{"id": "de-1", "country": "DE"}], False

        with mock.patch.dict(services.SOURCES, {"DE": slow_fetch}):
            threads = [threading.Thread(target=services.fetch_source_page, args=("DE", "", "all", 1)) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        self.assertEqual(len(calls), 1)
