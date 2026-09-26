# Gate Work — serverga o'rnatish

Sayt Docker orqali bitta buyruq bilan ishga tushadi:

| Xizmat | Vazifasi |
|---|---|
| `web` | Django + Gunicorn (3 jarayon × 8 oqim) |
| `db` | PostgreSQL 17 |
| `redis` | Kesh, sessiyalar, urinishlar cheklovi |
| `scheduler` | Har 10 daqiqada vakansiyalar keshini yangilaydi (`refresh_jobs`) |
| `caddy` | HTTPS (Let's Encrypt sertifikatini o'zi oladi), statik fayllar, rasmlar |

## 1. Server tayyorlash (Ubuntu 24.04)

```bash
# Docker o'rnatish
curl -fsSL https://get.docker.com | sh

# Faqat kerakli portlar ochiq bo'lsin
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
```

Domen DNS sozlamalarida: `gatework.uz` va `www.gatework.uz` uchun **A yozuvi → server IP**.

## 2. Kodni olish va sozlash

```bash
git clone https://github.com/vicocom210-cmd/gatework.git /opt/gatework
cd /opt/gatework
cp .env.example .env
nano .env
```

`.env` ichida albatta o'zgartiring:

- `DJANGO_SECRET_KEY` — yangi kalit:
  `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
  (eski kalit GitHub'da ochiq turibdi — uni ishlatmang)
- `POSTGRES_PASSWORD` — kuchli parol
- `DOMAIN`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` — domeningiz
- `PAYMENT_CARD` — to'lov kartasi raqami (ixtiyoriy)

## 3. Ishga tushirish

```bash
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py check_sources   # vakansiya manbalarini tekshirish
```

Sayt: `https://gatework.uz`. Admin panel: `https://gatework.uz/admin-login/`.

## 4. Kompyuterdagi ma'lumotlarni ko'chirish (SQLite → PostgreSQL)

Kompyuteringizda (PyCharm terminali):

```bash
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e sessions -e admin.logentry --indent 2 -o data.json
scp data.json root@SERVER_IP:/opt/gatework/
scp -r media root@SERVER_IP:/opt/gatework/   # chat fayllari va avatarlar (bo'lsa)
```

Serverda:

```bash
cd /opt/gatework
docker compose cp data.json web:/app/data.json
docker compose exec web python manage.py loaddata /app/data.json
docker compose cp media/. web:/data/media/     # agar media ko'chirilgan bo'lsa
```

## 5. Kundalik ishlar

```bash
# Yangi kodni o'rnatish
git pull && docker compose up -d --build

# Loglarni ko'rish
docker compose logs -f web

# Bazaning zaxira nusxasi (har kuni cron'ga qo'yish tavsiya etiladi)
docker compose exec -T db pg_dump -U gatework gatework | gzip > backup_$(date +%F).sql.gz
```

Google orqali kirish ishlashi uchun Google Cloud Console → Credentials → OAuth Client'da
**Authorized JavaScript origins** ga `https://gatework.uz` qo'shing.

## Yuklama sinovi natijasi

2 vCPU ga cheklangan muhitda (Gunicorn + PostgreSQL + Redis), 5 000 foydalanuvchi,
20 000 arxiv yozuvi, 10 000 chat xabari bor bazada:

| Holat | Natija |
|---|---|
| 500 kishi bir soniyada kiradi (kesh bo'sh) | 2 000 so'rov, **0 xato**, hammasi 6 soniyada |
| 500 kishi 60 soniya faol foydalanadi | ~135 so'rov/s, **0 xato**, eng sekin so'rov < 1.3 s |
| CPU | o'rtacha ~52%, eng yuqori ~127% (2 yadrodan = 200%) |
| RAM | Gunicorn ~240 MB, PostgreSQL ~400 MB |
