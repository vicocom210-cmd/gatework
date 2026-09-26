from django.test import TestCase

from users.models import User
from .models import Message


class ChatApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u@x.uz", "u@x.uz", "secret123")

    def test_no_admin_yet(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/chat/messages").json()["messages"], [])
        r = self.client.post("/api/chat/send", {"text": "salom"}, content_type="application/json")
        self.assertEqual(r.status_code, 503)  # avval 500 (IntegrityError) edi

    def test_user_admin_roundtrip(self):
        admin = User.objects.create_user("a@x.uz", "a@x.uz", "secret123", is_staff=True)
        self.client.force_login(self.user)
        r = self.client.post("/api/chat/send", {"text": "salom"}, content_type="application/json")
        self.assertTrue(r.json()["ok"])

        self.client.force_login(admin)
        threads = self.client.get("/api/chat/threads").json()["threads"]
        self.assertEqual(threads[0]["unread"], 1)
        self.assertIn("email", threads[0])
        msgs = self.client.get(f"/api/chat/messages?with={self.user.id}").json()["messages"]
        self.assertEqual(msgs[0]["text"], "salom")

    def test_first_load_returns_latest_messages(self):
        admin = User.objects.create_user("a@x.uz", "a@x.uz", "secret123", is_staff=True)
        Message.objects.bulk_create([Message(sender=self.user, receiver=admin, text=str(i)) for i in range(305)])
        self.client.force_login(self.user)
        msgs = self.client.get("/api/chat/messages").json()["messages"]
        self.assertEqual((len(msgs), msgs[-1]["text"]), (300, "304"))


class SharedAdminInboxTests(TestCase):
    """Saytda IKKI admin bo'lganda ham chat ishlashi kerak (avval ishlamasdi)."""

    def setUp(self):
        self.a1 = User.objects.create_user("a1", "a1@x.uz", "secret123", is_staff=True)
        self.a2 = User.objects.create_user("a2", "a2@x.uz", "secret123", is_staff=True)
        self.user = User.objects.create_user("u@x.uz", "u@x.uz", "secret123")

    def test_second_admin_sees_user_message_and_user_sees_reply(self):
        self.client.force_login(self.user)
        self.client.post("/api/chat/send", {"text": "savol"}, content_type="application/json")

        self.client.force_login(self.a2)  # birinchi admin EMAS
        self.assertEqual(self.client.get("/api/chat/unread").json()["count"], 1)
        threads = self.client.get("/api/chat/threads").json()["threads"]
        self.assertEqual([t["id"] for t in threads], [self.user.id])  # adminlar ro'yxatda yo'q
        self.assertEqual(threads[0]["unread"], 1)
        msgs = self.client.get(f"/api/chat/messages?with={self.user.id}").json()["messages"]
        self.assertEqual([m["text"] for m in msgs], ["savol"])
        self.assertEqual(self.client.get("/api/chat/unread").json()["count"], 0)
        self.client.post("/api/chat/send", {"text": "javob", "to": self.user.id}, content_type="application/json")

        self.client.force_login(self.user)
        msgs = self.client.get("/api/chat/messages").json()["messages"]
        self.assertEqual([m["text"] for m in msgs], ["savol", "javob"])
