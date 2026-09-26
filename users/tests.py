import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from jobs.models import JobEvent
from .models import User

TMP_MEDIA = tempfile.mkdtemp()


def make_user(email="ali@x.uz", password="secret123", **kw):
    u = User(username=email, email=email, first_name=kw.pop("first_name", "Ali"), **kw)
    u.set_password(password)
    u.save()
    return u


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class AuthApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def test_register_logs_in_and_rejects_duplicate_email(self):
        data = {"firstName": "Ali", "lastName": "Valiyev", "email": "Ali@X.uz", "password": "secret123", "birthDate": "1999-05-05"}
        r = self.client.post("/api/register", data)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["user"]["email"], "ali@x.uz")
        self.assertEqual(r.json()["user"]["birthDate"], "1999-05-05")
        self.assertEqual(self.client.get("/api/me").status_code, 200)  # darhol tizimda

        self.client.post("/api/logout")
        r = self.client.post("/api/register", data)  # avval 500 (IntegrityError) edi
        self.assertEqual(r.status_code, 400)
        self.assertIn("allaqachon", r.json()["error"])

    def test_register_rejects_bad_birth_date(self):
        r = self.client.post("/api/register", {"firstName": "A", "email": "a@x.uz", "password": "secret123", "birthDate": "xx"})
        self.assertEqual(r.status_code, 400)

    def test_me_returns_fields_the_frontend_needs(self):
        make_user(plan="pro")
        self.client.post("/api/login", {"email": "ali@x.uz", "password": "secret123"}, content_type="application/json")
        user = self.client.get("/api/me").json()["user"]
        for key in ("firstName", "lastName", "avatar", "assets", "points", "planActive", "planUntil", "birthDate"):
            self.assertIn(key, user)
        self.assertTrue(user["planActive"])  # avval yo'q edi -> PRO ham ariza topshira olmasdi

    def test_profile_update_with_avatar(self):
        u = make_user()
        self.client.force_login(u)
        img = SimpleUploadedFile("a.png", b"\x89PNG\r\n\x1a\n" + b"0" * 10, content_type="image/png")
        r = self.client.post("/api/profile", {
            "firstName": "Vali", "lastName": "B", "birthDate": "2000-01-02",
            "assets": '["diploma"]', "password": "newpass1", "avatar": img,
        })
        self.assertEqual(r.status_code, 200, r.content)
        u.refresh_from_db()
        self.assertEqual((u.first_name, str(u.birth_date), u.assets), ("Vali", "2000-01-02", ["diploma"]))
        self.assertTrue(u.avatar.startswith("/media/avatars/"))
        self.assertTrue(u.check_password("newpass1"))
        self.assertEqual(self.client.get("/api/me").status_code, 200)  # parol o'zgarsa ham chiqib ketmaydi

    def test_rating_and_plans(self):
        make_user("a@x.uz", points=5)
        make_user("b@x.uz", points=9)
        make_user("c@x.uz", points=0)
        users = self.client.get("/api/rating").json()["users"]
        self.assertEqual([u["points"] for u in users], [9, 5])
        self.assertEqual(users[0]["rank"], 1)
        self.assertIn("card", self.client.get("/api/plans").json())


class AdminApiTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin@x.uz", is_staff=True)
        self.user = make_user("u@x.uz")
        JobEvent.objects.create(user=self.user, kind="apply", job_id="1", title="T")
        self.client.force_login(self.admin)

    def test_list_has_counts(self):
        users = self.client.get("/api/admin/users").json()["users"]
        row = next(x for x in users if x["id"] == self.user.id)
        self.assertEqual((row["applies"], row["views"]), (1, 0))

    def test_detail_has_archive(self):
        data = self.client.get(f"/api/admin/users/{self.user.id}").json()
        self.assertEqual(len(data["archive"]["applies"]), 1)
        # vaqt JS (timeAgo) tushunadigan formatda: "YYYY-MM-DD HH:MM:SS"
        self.assertRegex(data["archive"]["applies"][0]["createdAt"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$")

    def test_edit_validation(self):
        url = f"/api/admin/users/{self.user.id}"
        self.assertEqual(self.client.post(url, {"email": "admin@x.uz"}).status_code, 400)  # band email
        self.assertEqual(self.client.post(url, {"points": "abc"}).status_code, 400)  # avval 500 edi
        r = self.client.post(url, {"plan": "pro", "planUntil": "2099-01-01"}, content_type="application/json")
        self.assertTrue(r.json()["user"]["planActive"])
        r = self.client.post(url, {"plan": "free", "planUntil": ""}, content_type="application/json")
        self.assertIsNone(r.json()["user"]["planUntil"])

    def test_stats(self):
        s = self.client.get("/api/admin/stats").json()
        self.assertEqual((s["users"], s["applies"]), (2, 1))

    def test_non_admin_forbidden(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)
