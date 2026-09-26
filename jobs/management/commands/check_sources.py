"""
Vakansiya manbalarini tekshirish:  python manage.py check_sources

Har bir API manziliga to'g'ridan-to'g'ri so'rov yuboradi va natijani
(HTTP kodi, vaqt, nechta vakansiya) ko'rsatadi. Germaniya vakansiyalari
chiqmasa — birinchi navbatda shu buyruqni ishga tushiring.
"""
import json
import time

import requests
from django.core.cache import cache
from django.core.management.base import BaseCommand

from jobs import services


class Command(BaseCommand):
    help = "Bundesagentur va Arbetsförmedlingen API'larini tekshiradi"

    def handle(self, *args, **options):
        cache.delete(services.DE_DOWN_KEY)
        self.stdout.write("== Bundesagentur für Arbeit (Germaniya) ==")
        for url in services.DE_API_URLS:
            self._probe(url, services.DE_HEADERS,
                        {"angebotsart": "1", "was": "Pflege", "size": 5, "page": 1}, services.de_extract_items)

        self.stdout.write("\n== Arbetsförmedlingen (Shvetsiya) ==")
        self._probe("https://jobsearch.api.jobtechdev.se/search", {"accept": "application/json"},
                    {"q": "vård", "limit": 5}, lambda d: d.get("hits", []))

        self.stdout.write("\n== Saytning o'zi qanday ko'radi (1-sahifa) ==")
        for code, fetch in services.SOURCES.items():
            t0 = time.time()
            jobs, more = fetch(page=1, page_size=25)
            self.stdout.write(f"{code}: {len(jobs)} ta vakansiya, yana bor: {more}, {time.time() - t0:.1f}s")
        cache.delete(services.DE_DOWN_KEY)

    def _probe(self, url, headers, params, extract):
        t0 = time.time()
        try:
            res = requests.get(url, headers=headers, params=params, timeout=15)
            took = time.time() - t0
            data = None
            try:
                data = res.json()
                n = len(extract(data) or [])
            except ValueError:
                n = "JSON emas"
            style = self.style.SUCCESS if res.ok and n else self.style.ERROR
            self.stdout.write(style(f"{res.status_code}  {took:.1f}s  {n} ta  {url}"))
            if not res.ok:
                self.stdout.write("     javob: " + res.text[:200].replace("\n", " "))
            elif not n:
                # Vakansiya topilmadi — javob tuzilishini ko'rsatamiz (tuzatish uchun kerak)
                if isinstance(data, dict):
                    self.stdout.write(f"     kalitlar: {list(data.keys())}")
                self.stdout.write("     javob: " + json.dumps(data, ensure_ascii=False)[:1500])
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"XATO  {time.time() - t0:.1f}s  {url}\n     {e}"))
