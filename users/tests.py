import re
from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from .models import EmailVerification, User


class EmailVerificationTests(TestCase):
    signup = {"firstName": "Ali", "lastName": "Valiyev", "birthDate": "", "email": "ali@example.com", "password": "Parol123!"}

    def register(self, **extra):
        return self.client.post("/api/register", {**self.signup, **extra})

    def last_code(self):
        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def test_register_sends_code_and_user_is_inactive(self):
        res = self.register()
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["needVerify"])
        user = User.objects.get(email="ali@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ali@example.com"])

    def test_cannot_login_before_verifying(self):
        self.register()
        res = self.client.post("/api/login", {"email": "ali@example.com", "password": "Parol123!"},
                               content_type="application/json")
        self.assertEqual(res.status_code, 403)
        self.assertTrue(res.json()["needVerify"])

    def test_correct_code_activates_and_logs_in(self):
        self.register()
        res = self.client.post("/api/verify-email", {"email": "ali@example.com", "code": self.last_code()},
                               content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(User.objects.get(email="ali@example.com").is_active)
        self.assertFalse(EmailVerification.objects.exists())
        self.assertEqual(self.client.get("/api/me").status_code, 200)

    def test_wrong_code_is_limited(self):
        self.register()
        code = self.last_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.client.post("/api/verify-email", {"email": "ali@example.com", "code": wrong},
                             content_type="application/json")
        res = self.client.post("/api/verify-email", {"email": "ali@example.com", "code": code},
                               content_type="application/json")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.get(email="ali@example.com").is_active)

    def test_expired_code_rejected(self):
        self.register()
        EmailVerification.objects.update(sent_at=timezone.now() - timedelta(minutes=11))
        res = self.client.post("/api/verify-email", {"email": "ali@example.com", "code": self.last_code()},
                               content_type="application/json")
        self.assertEqual(res.status_code, 400)

    def test_resend_has_cooldown(self):
        self.register()
        res = self.client.post("/api/resend-code", {"email": "ali@example.com"}, content_type="application/json")
        self.assertEqual(res.status_code, 429)
        EmailVerification.objects.update(sent_at=timezone.now() - timedelta(seconds=61))
        res = self.client.post("/api/resend-code", {"email": "ali@example.com"}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

    def test_unverified_signup_can_register_again(self):
        self.register()
        res = self.register(password="Boshqa456!")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(User.objects.filter(email="ali@example.com").count(), 1)

    def test_duplicate_verified_email_rejected(self):
        User.objects.create_user(username="ali@example.com", email="ali@example.com", password="x")
        res = self.register()
        self.assertEqual(res.status_code, 400)
        self.assertIn("allaqachon", res.json()["error"])
