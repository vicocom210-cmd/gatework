"""
pages/api.py
============================================================================
UZ: Saytning "umumiy" (biror modelga bog'lanmagan) API endpointlari shu yerda:
    valyuta kurslari va tarif ("plan") kartasi. Bular frontend (app.js)
    tomonidan chaqiriladi, lekin ilgari backend'da yo'q edi (404 berardi).
RU: Здесь "общие" (не привязанные к модели) API-эндпоинты сайта: курсы валют
    и карточка тарифа ("plan"). Их вызывает фронтенд (app.js), но раньше их
    не было в бэкенде (выдавали 404).
EN: The site's "generic" (not tied to a model) API endpoints live here:
    currency rates and the plan ("plan") card. The frontend (app.js) calls
    them, but they were missing from the backend before (returned 404).
DE: Hier liegen die "allgemeinen" (nicht an ein Modell gebundenen) API-
    Endpunkte: Wechselkurse und die Tarif-("plan")-Karte. Das Frontend
    (app.js) ruft sie auf, sie fehlten aber bisher im Backend (404).
============================================================================
"""
import time

import requests
from rest_framework.views import APIView
from rest_framework.response import Response

# UZ: Agar tarmoq ishlamasa — shu zaxira kurslar ishlatiladi (EUR bazaviy).
# RU: Если сеть недоступна — используются эти резервные курсы (база EUR).
# EN: If the network is down — these fallback rates are used (EUR base).
# DE: Bei Netzwerkausfall — diese Ersatzkurse werden verwendet (Basis EUR).
_FALLBACK_RATES = {"EUR": 1, "USD": 1.08, "GBP": 0.85, "SEK": 11.3, "PLN": 4.3}

# UZ: Kurslarni har safar so'ramaslik uchun 1 soat xotirada saqlaymiz (cache).
# RU: Чтобы не запрашивать курсы каждый раз, кэшируем их на 1 час.
# EN: To avoid fetching rates every time, we cache them for 1 hour.
# DE: Um nicht jedes Mal abzufragen, cachen wir die Kurse 1 Stunde.
_cache = {"rates": None, "at": 0}
_CACHE_TTL = 3600


class RatesView(APIView):
    """
    UZ: /api/rates — valyuta kurslari (EUR bazaviy). Maosh boshqa valyutaga
        aylantirilganda app.js shundan foydalanadi.
    RU: /api/rates — курсы валют (база EUR). app.js использует их при
        конвертации зарплаты в другую валюту.
    EN: /api/rates — currency rates (EUR base). app.js uses them when
        converting a salary into another currency.
    DE: /api/rates — Wechselkurse (Basis EUR). app.js nutzt sie bei der
        Umrechnung eines Gehalts in eine andere Währung.
    """

    def get(self, request):
        now = time.time()
        if _cache["rates"] and (now - _cache["at"]) < _CACHE_TTL:
            return Response(_cache["rates"])

        rates = dict(_FALLBACK_RATES)
        try:
            # UZ: frankfurter.app — bepul, kalit kerak emas.
            # RU: frankfurter.app — бесплатно, ключ не нужен.
            # EN: frankfurter.app — free, no key required.
            # DE: frankfurter.app — kostenlos, kein Schlüssel nötig.
            res = requests.get(
                "https://api.frankfurter.app/latest",
                params={"from": "EUR", "to": "USD,GBP,SEK,PLN"},
                timeout=6,
            )
            res.raise_for_status()
            got = res.json().get("rates", {})
            rates = {"EUR": 1, **{k: got[k] for k in ("USD", "GBP", "SEK", "PLN") if k in got}}
        except Exception as e:
            print(f"[Rates xatosi — zaxira kurslar ishlatildi] {e}")

        _cache["rates"] = rates
        _cache["at"] = now
        return Response(rates)


class PlansView(APIView):
    """
    UZ: /api/plans — tarif kartasi ma'lumoti. Hozircha oddiy matn; keyin
        haqiqiy to'lov tizimiga ulanganda bu yerda karta raqami/holati bo'ladi.
    RU: /api/plans — данные карточки тарифа. Пока простой текст; позже, при
        подключении оплаты, здесь будет номер/статус карты.
    EN: /api/plans — the plan card info. For now it's a simple string; later,
        when a real payment system is connected, it will hold the card
        number/status here.
    DE: /api/plans — die Tarifkarten-Info. Vorerst ein einfacher Text; später,
        bei Anbindung eines echten Zahlungssystems, steht hier die Karten-
        nummer/der Status.
    """

    def get(self, request):
        return Response({"ok": True, "card": ""})
