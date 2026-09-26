"""
services.py — bu Django'ning standart fayli emas, biz o'zimiz
yaratamiz. Bu yerda "biznes-mantiq" (tashqi API bilan ishlash) turadi.

NEGA ALOHIDA FAYL? Django'ning odatiy qoidasi: views.py faqat
"so'rovni qabul qilib, javob qaytarish" bilan shug'ullansin, murakkab
mantiq esa alohida faylda (services.py) tursin. Shunda kod tartibli
bo'ladi va keyinchalik buni Celery task'ga o'tkazish ham osonlashadi
(migratsiya rejamizdagi 2-bosqich, eslaysizmi?).
"""
import requests

SECTOR_TO_DE_KEYWORD = {"medical": "Pflege", "agriculture": "Landwirtschaft", "service": "Service"}
ALL_SECTORS_DE_KEYWORDS = " ".join(SECTOR_TO_DE_KEYWORD.values())


def fetch_bundesagentur_jobs(query="", sector="all"):
    """
    Germaniya — Bundesagentur für Arbeit Jobsuche API (bepul, ochiq).
    Bu — eski Flask kodimizning deyarli AYNAN o'zi, faqat endi
    Django loyihasi ichida turibdi.
    """
    MAX_PAGES = 3
    PAGE_SIZE = 100

    if sector in SECTOR_TO_DE_KEYWORD:
        search_text = f"{query} {SECTOR_TO_DE_KEYWORD[sector]}".strip()
    else:
        search_text = query.strip() or ALL_SECTORS_DE_KEYWORDS

    headers = {"X-API-Key": "jobboerse-jobsuche"}
    all_items = []

    for page in range(1, MAX_PAGES + 1):
        params = {
            "angebotsart": "1",
            "was": search_text,
            "wo": "Deutschland",
            "pav": "false",
            "size": PAGE_SIZE,
            "page": page,
        }
        data = None
        for version_url in (
            "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs",
            "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs",
        ):
            try:
                res = requests.get(version_url, headers=headers, params=params, timeout=8)
                res.raise_for_status()
                data = res.json()
                break
            except Exception as e:
                print(f"[Bundesagentur xatosi — {page}-sahifa] {e}")
        if data is None:
            break

        page_items = data.get("stellenangebote", [])
        if not page_items:
            break
        all_items += page_items
        if len(page_items) < PAGE_SIZE:
            break

    jobs = []
    for item in all_items:
        title = item.get("titel") or "—"
        ref_id = item.get("hashId") or item.get("referenznummer") or ""
        apply_url = item.get("externeUrl") or f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref_id}"
        jobs.append({
            "id": f"de-live-{ref_id}",
            "sector": sector if sector != "all" else "service",
            "country": "DE",
            "city": (item.get("arbeitsort") or {}).get("ort", ""),
            "employer": item.get("arbeitgeber") or "Noma'lum",
            # MUHIM: app.js "title" ni {uz,ru,en,de} obyekti sifatida
            # kutadi (tl() funksiyasi orqali). Hozircha barcha tillar
            # uchun bir xil (asl) matnni beramiz — haqiqiy tarjimani
            # keyingi darsda qo'shamiz.
            "title": {"uz": title, "ru": title, "en": title, "de": title},
            "desc": {"uz": "", "ru": "", "en": "", "de": ""},
            "tags": [],
            "requirements": [],
            "pay": None,
            "postedAt": (item.get("aktuelleVeroeffentlichungsdatum") or "")[:10],
            "sourceName": "Bundesagentur für Arbeit",
            "sourceUrl": apply_url,
        })
    return jobs


def fetch_arbetsformedlingen_jobs(query="", sector="all"):
    """
    Shvetsiya — Arbetsförmedlingen (JobSearch/JobTech) API, bepul,
    ochiq va RASMIY. Sizning tarmog'ingizda bu manba ISHLAYDI.
    """
    MAX_PAGES = 3
    PAGE_SIZE = 100

    sector_keyword = {"medical": "vård", "agriculture": "jordbruk", "service": "service"}.get(sector, "")
    search_text = f"{query} {sector_keyword}".strip() or sector_keyword

    all_hits = []
    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        data = None
        # Tarmoq vaqti-vaqti bilan uzilib qolishi mumkin — shuning
        # uchun har bir sahifani taslim bo'lishdan oldin yana bir
        # marta qayta so'raymiz.
        for attempt in range(2):
            try:
                res = requests.get(
                    "https://jobsearch.api.jobtechdev.se/search",
                    params={"q": search_text, "limit": PAGE_SIZE, "offset": offset},
                    headers={"accept": "application/json"},
                    timeout=8,
                )
                res.raise_for_status()
                data = res.json()
                break
            except Exception as e:
                print(f"[Arbetsförmedlingen xatosi — {offset}-offset, {attempt + 1}-urinish] {e}")
        if data is None:
            break

        hits = data.get("hits", [])
        if not hits:
            break
        all_hits += hits
        if len(hits) < PAGE_SIZE:
            break

    jobs = []
    for item in all_hits:
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
    return jobs