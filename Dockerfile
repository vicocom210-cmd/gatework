# Gate Work — Django ilovasi uchun obraz
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Root bo'lmagan foydalanuvchi — xavfsizroq
RUN useradd --create-home app && mkdir -p /data/static /data/media && chown -R app:app /app /data
USER app

ENV DJANGO_STATIC_ROOT=/data/static \
    DJANGO_MEDIA_ROOT=/data/media

EXPOSE 8000

# Har ishga tushganda: bazani yangilash, statik fayllarni yig'ish, keyin Gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput -v 0 && exec gunicorn config.wsgi:application -c gunicorn.conf.py"]
