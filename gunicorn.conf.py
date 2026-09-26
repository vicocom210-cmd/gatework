"""
Gunicorn sozlamalari (production server).

2 vCPU server uchun: 3 jarayon x 8 oqim = bir vaqtda 24 ta so'rov
ishlanadi. Oqimlar (gthread) kerak, chunki vakansiya so'rovi tashqi
API'ni kutib turishi mumkin — shu paytda boshqa so'rovlar to'xtab qolmaydi.
"""
import multiprocessing
import os

bind = "0.0.0.0:8000"
worker_class = "gthread"
workers = int(os.environ.get("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 5)))
threads = int(os.environ.get("GUNICORN_THREADS", 8))
timeout = 60
graceful_timeout = 30
keepalive = 5
# Xotira "oqib ketishi"dan himoya: har jarayon ~2000 so'rovdan keyin yangilanadi
max_requests = 2000
max_requests_jitter = 200
accesslog = "-"
errorlog = "-"
