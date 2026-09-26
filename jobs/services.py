"""
services.py — bu Django'ning standart fayli emas, biz o'zimiz
yaratamiz. Bu yerda "biznes-mantiq" (tashqi API bilan ishlash) turadi.

NEGA ALOHIDA FAYL? Django'ning odatiy qoidasi: views.py faqat
"so'rovni qabul qilib, javob qaytarish" bilan shug'ullansin, murakkab
mantiq esa alohida faylda (services.py) tursin. Shunda kod tartibli
bo'ladi va keyinchalik buni Celery task'ga o'tkazish ham osonlashadi
(migratsiya rejamizdagi 2-bosqich, eslaysizmi?).
"""
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from django.core.cache import cache

SECTOR_TO_DE_KEYWORD = {"medical": "Pflege", "agriculture": "Landwirtschaft", "service": "Service"}


# MUHIM: 2026-yil holatiga ko'ra v4 manzillari 403 "No match found"
# qaytaradi (o'chirilgan) — ishlaydigani v6. v4 faqat zaxira sifatida qoldi.
DE_API_URLS = (
    "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs",
    "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs",
    "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/app/jobs",
)
DE_ITEM_HINTS = ("titel", "refnr", "beruf", "hashId", "referenznummer", "stellenangebotsTitel")


def _first(d, *keys):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return None


def de_extract_items(data):
    """
    Javobdan vakansiyalar ro'yxatini topadi. v4'da bu "stellenangebote"
    edi; v6'da nomi boshqacha bo'lishi mumkin — shuning uchun ichida
    vakansiyaga o'xshash (titel/refnr/... maydonli) obyektlar bor
    birinchi ro'yxatni qidiramiz (2 darajagacha chuqurlikda).
    """
    def looks_like_jobs(v):
        return isinstance(v, list) and v and isinstance(v[0], dict) and any(h in v[0] for h in DE_ITEM_HINTS)

    if not isinstance(data, dict):
        return data if looks_like_jobs(data) else []
    if isinstance(data.get("stellenangebote"), list):
        return data["stellenangebote"]
    for v in data.values():
        if looks_like_jobs(v):
            return v
    for v in data.values():
        if isinstance(v, dict):
            for vv in v.values():
                if looks_like_jobs(vv):
                    return vv
    return []
DE_HEADERS = {
    "X-API-Key": "jobboerse-jobsuche",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; GateWork/1.0; +https://gatework.uz)",
}
# Qaysi versiya ishlagani eslab qolinadi — aks holda har sahifada avval
# ishlamaydigan manzil sinab ko'rilib, har safar vaqt yo'qotilar edi.
_de_working_url = None
DE_DOWN_KEY = "jobs:de-down"


def _de_request(params):
    """
    Bundesagentur API'ga bitta so'rov. Muvaffaqiyatli bo'lsa — JSON,
    aks holda None. API butunlay ishlamasa, 2 daqiqa davomida qayta
    urinmaymiz (aks holda har sahifa 8-16 soniya kutib qolardi).
    """
    global _de_working_url
    if cache.get(DE_DOWN_KEY):
        return None
    urls = [_de_working_url] if _de_working_url else []
    urls += [u for u in DE_API_URLS if u != _de_working_url]
    for url in urls:
        try:
            res = requests.get(url, headers=DE_HEADERS, params=params, timeout=8)
            res.raise_for_status()
            data = res.json()
            _de_working_url = url
            return data
        except Exception as e:
            print(f"[Bundesagentur xatosi — {url}] {e}")
    cache.set(DE_DOWN_KEY, True, 120)
    return None


def _de_to_job(item, sector):
    title = _first(item, "titel", "stellenangebotsTitel", "beruf", "title") or "—"
    ref_id = _first(item, "refnr", "referenznummer", "hashId", "id") or ""
    apply_url = _first(item, "externeUrl", "externeURL", "url") or f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref_id}"
    employer = _first(item, "arbeitgeber", "arbeitgeberName", "firma") or "Noma'lum"
    if isinstance(employer, dict):
        employer = _first(employer, "name", "firma") or "Noma'lum"
    place = item.get("arbeitsort") or item.get("arbeitsorte") or {}
    if isinstance(place, list):
        place = place[0] if place and isinstance(place[0], dict) else {}
    city = (_first(place, "ort", "stadt", "region") or "") if isinstance(place, dict) else ""
    posted = _first(item, "aktuelleVeroeffentlichungsdatum", "veroeffentlichungsdatum", "eintrittsdatum") or ""
    return {
        "id": f"de-live-{ref_id}",
        "sector": sector,
        "country": "DE",
        "city": city,
        "employer": employer,
        # MUHIM: app.js "title" ni {uz,ru,en,de} obyekti sifatida
        # kutadi (tl() funksiyasi orqali). Hozircha barcha tillar
        # uchun bir xil (asl) matnni beramiz — haqiqiy tarjimani
        # keyingi bosqichda qo'shamiz.
        "title": {"uz": title, "ru": title, "en": title, "de": title},
        "desc": {"uz": "", "ru": "", "en": "", "de": ""},
        "tags": [],
        "requirements": [],
        "pay": None,
        "postedAt": str(posted)[:10],
        "sourceName": "Bundesagentur für Arbeit",
        "sourceUrl": apply_url,
    }


def fetch_bundesagentur_jobs(query="", sector="all", page=1, page_size=25):
    """
    Germaniya — Bundesagentur für Arbeit Jobsuche API (bepul, ochiq).
    Faqat BITTA sahifani oladi. Qaytaradi: (jobs, has_more).

    MUHIM: API "was" maydonidagi so'zlarning HAMMASI bir vakansiyada
    bo'lishini talab qiladi. Avval "Hammasi" tanlanganda "Pflege
    Landwirtschaft Service" deb bitta so'rov ketardi — natija deyarli
    doim bo'sh edi. Endi har bir soha alohida (parallel) so'raladi.
    """
    query = query.strip()
    if sector in SECTOR_TO_DE_KEYWORD:
        searches = [(f"{query} {SECTOR_TO_DE_KEYWORD[sector]}".strip(), sector, page_size)]
    elif query:
        searches = [(query, "service", page_size)]
    else:
        per = max(1, -(-page_size // len(SECTOR_TO_DE_KEYWORD)))  # yuqoriga yaxlitlash
        searches = [(kw, sec, per) for sec, kw in SECTOR_TO_DE_KEYWORD.items()]

    def one(search):
        was, sec, size = search
        # "wo" berilmaydi — butun Germaniya bo'yicha qidiriladi
        data = _de_request({"angebotsart": "1", "was": was, "pav": "false", "size": size, "page": page})
        if data is None:
            return [], False
        items = de_extract_items(data)
        return [_de_to_job(it, sec) for it in items], len(items) >= size

    with ThreadPoolExecutor(max_workers=len(searches)) as pool:
        results = list(pool.map(one, searches))

    # Sohalarni aralashtirib (navbat bilan) qo'yamiz, takrorlarni olib tashlaymiz
    jobs, seen = [], set()
    for i in range(max((len(js) for js, _ in results), default=0)):
        for js, _ in results:
            if i < len(js) and js[i]["id"] not in seen:
                seen.add(js[i]["id"])
                jobs.append(js[i])
    return jobs, any(more for _, more in results)


def fetch_arbetsformedlingen_jobs(query="", sector="all", page=1, page_size=25):
    """
    Shvetsiya — Arbetsförmedlingen (JobSearch/JobTech) API, bepul,
    ochiq va RASMIY. Faqat BITTA sahifani oladi. Qaytaradi: (jobs, has_more).
    """
    sector_keyword = {"medical": "vård", "agriculture": "jordbruk", "service": "service"}.get(sector, "")
    search_text = f"{query} {sector_keyword}".strip() or sector_keyword
    offset = (page - 1) * page_size

    data = None
    # Tarmoq vaqti-vaqti bilan uzilib qolishi mumkin — shuning
    # uchun taslim bo'lishdan oldin yana bir marta qayta so'raymiz.
    for attempt in range(2):
        try:
            res = requests.get(
                "https://jobsearch.api.jobtechdev.se/search",
                params={"q": search_text, "limit": page_size, "offset": offset},
                headers={"accept": "application/json"},
                timeout=8,
            )
            res.raise_for_status()
            data = res.json()
            break
        except Exception as e:
            print(f"[Arbetsförmedlingen xatosi — {offset}-offset, {attempt + 1}-urinish] {e}")
    if data is None:
        return [], False

    hits = data.get("hits", []) or []

    jobs = []
    for item in hits:
        title = item.get("headline") or "—"
        employer = (item.get("employer") or {}).get("name") or "Noma'lum"
        workplace = item.get("workplace_address") or {}
        job_id = item.get("id") or ""
        app_details = item.get("application_details") or {}
        apply_url = app_details.get("url") or item.get("webpage_url") or f"https://arbetsformedlingen.se/platsbanken/annonser/{job_id}"
        jobs.append({
            "id": f"se-live-{job_id}",
            "sector": sector if sector != "all" else "service",
            "country": "SE",
            "city": workplace.get("municipality") or workplace.get("city") or "",
            "employer": employer,
            "title": {"uz": title, "ru": title, "en": title, "de": title},
            "desc": {"uz": "", "ru": "", "en": "", "de": ""},
            "tags": [],
            "requirements": [],
            "pay": None,
            "postedAt": (item.get("publication_date") or "")[:10],
            "sourceName": "Arbetsförmedlingen",
            "sourceUrl": apply_url,
        })
    return jobs, len(hits) >= page_size


SOURCES = {
    "DE": fetch_bundesagentur_jobs,
    "SE": fetch_arbetsformedlingen_jobs,
}
PAGE_SIZE = 25        # har bir manbadan bitta so'rovda nechta vakansiya
MAX_PAGES = 6         # 6 x 25 = har manbadan ko'pi bilan 150 ta (avvalgidek ~300 jami)
# 30 daqiqa: serverda "refresh_jobs" har 10 daqiqada asosiy sahifalarni
# yangilab turadi, shuning uchun foydalanuvchi deyarli doim keshdan oladi.
CACHE_SECONDS = 30 * 60
SECTORS = ("all", "medical", "agriculture", "service")


def _cache_key(code, query, sector, page):
    return "jobs:" + hashlib.md5(f"{code}|{query}|{sector}|{page}".encode()).hexdigest()


def fetch_source_page(code, query="", sector="all", page=1, force=False):
    """
    Bitta manbaning bitta sahifasi, kesh orqali: (jobs, has_more).

    MUHIM ("stampede" himoyasi): kesh bo'sh paytda bir vaqtda 500 kishi
    kirsa, tashqi API'ga 500 ta emas, faqat BITTA so'rov ketadi — qolganlar
    birinchisi natijani keshga yozguncha kutib turadi.
    """
    key = _cache_key(code, query, sector, page)
    if not force:
        cached = cache.get(key)
        if cached is not None:
            return cached
        if not cache.add(key + ":lock", 1, 20):
            # boshqa so'rov aynan shu sahifani yuklayapti — 10 soniyagacha kutamiz
            for _ in range(40):
                time.sleep(0.25)
                cached = cache.get(key)
                if cached is not None:
                    return cached
    try:
        jobs, more = SOURCES[code](query=query, sector=sector, page=page, page_size=PAGE_SIZE)
        # Bo'sh natija (ehtimol tarmoq xatosi) keshlanmaydi — keyingi safar qayta uriniladi.
        if jobs:
            cache.set(key, (jobs, more), CACHE_SECONDS)
        return jobs, more
    finally:
        cache.delete(key + ":lock")


def get_jobs_page(country="ALL", query="", sector="all", page=1):
    """
    Tanlangan davlat(lar) uchun BITTA sahifani qaytaradi: (jobs, has_more).
    Bir nechta manba PARALLEL so'raladi (ketma-ket emas); har biri keshlanadi.
    """
    codes = [c for c in SOURCES if country in (c, "ALL")]
    if not codes or page > MAX_PAGES:
        return [], False
    query = " ".join(query.split()).lower()[:100]
    if sector not in SECTORS:
        sector = "all"

    with ThreadPoolExecutor(max_workers=len(codes)) as pool:
        results = list(pool.map(lambda c: fetch_source_page(c, query, sector, page), codes))

    jobs = [j for js, _ in results for j in js]
    has_more = page < MAX_PAGES and any(more for _, more in results)
    return jobs, has_more
