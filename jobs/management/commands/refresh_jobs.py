"""
Vakansiyalar keshini oldindan to'ldiradi:  python manage.py refresh_jobs

Serverda har 10 daqiqada ishga tushadi (docker-compose'dagi "scheduler").
Shunda asosiy sahifalar (qidiruv so'zisiz, har bir soha) doim keshda
bo'ladi — foydalanuvchilar tashqi API'ni kutmaydi, API'larga esa
foydalanuvchilar sonidan qat'i nazar bir xil, kam so'rov ketadi.
"""
import time

from django.core.management.base import BaseCommand

from jobs import services


class Command(BaseCommand):
    help = "Asosiy vakansiya sahifalarini tashqi API'lardan olib, keshga yozadi"

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=services.MAX_PAGES)

    def handle(self, *args, **options):
        t0 = time.time()
        total = 0
        for code in services.SOURCES:
            for sector in services.SECTORS:
                for page in range(1, options["pages"] + 1):
                    jobs, more = services.fetch_source_page(code, "", sector, page, force=True)
                    total += len(jobs)
                    if not more:
                        break
        self.stdout.write(f"refresh_jobs: {total} ta vakansiya keshlandi, {time.time() - t0:.1f}s")
