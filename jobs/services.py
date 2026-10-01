"""
services.py
============================================================================
UZ: Bu yerda "biznes-mantiq" turadi — tashqi ish qidiruv API'lari bilan
    ishlash. Har bir manba (Bundesagentur, Arbetsförmedlingen, Arbeitnow,
    Adzuna va h.k.) uchun alohida funksiya bor. Pastda SOURCES registri
    (ro'yxati) va get_jobs() dispetcheri barcha manbalarni birlashtiradi.
RU: Здесь находится "бизнес-логика" — работа с внешними API поиска вакансий.
    Для каждого источника (Bundesagentur, Arbetsförmedlingen, Arbeitnow,
    Adzuna и т.д.) отдельная функция. Ниже реестр SOURCES и диспетчер
    get_jobs() объединяют все источники.
EN: This file holds the "business logic" — talking to external job-search
    APIs. There is one function per source (Bundesagentur, Arbetsförmedlingen,
    Arbeitnow, Adzuna, ...). The SOURCES registry and the get_jobs()
    dispatcher at the bottom combine every source.
DE: Hier liegt die "Geschäftslogik" — die Arbeit mit externen Jobsuche-APIs.
    Für jede Quelle (Bundesagentur, Arbetsförmedlingen, Arbeitnow, Adzuna
    usw.) gibt es eine eigene Funktion. Die SOURCES-Registry und der
    get_jobs()-Dispatcher unten führen alle Quellen zusammen.
============================================================================

UZ: ESLATMA — har bir funksiya "normallashtirilgan" (bir xil tuzilishdagi)
    ish obyektini qaytaradi. Frontend (app.js) aynan shu tuzilishni kutadi:
      { id, sector, country, city, employer,
        title:{uz,ru,en,de}, desc:{uz,ru,en,de}, tags:[], requirements:[],
        pay:None, postedAt, sourceName, sourceUrl }
    sourceUrl — "Ariza topshirish" tugmasi o'tadigan rasmiy manzil.
RU: ПРИМЕЧАНИЕ — каждая функция возвращает "нормализованный" объект вакансии
    одинаковой структуры, которую ожидает фронтенд (app.js). sourceUrl — это
    официальный адрес, куда ведёт кнопка "Подать заявку".
EN: NOTE — every function returns a "normalized" job object with the same
    structure that the frontend (app.js) expects. sourceUrl is the official
    address the "Apply" button links to.
DE: HINWEIS — jede Funktion gibt ein "normalisiertes" Job-Objekt mit
    derselben Struktur zurück, die das Frontend (app.js) erwartet. sourceUrl
    ist die offizielle Adresse, auf die der "Bewerben"-Button verweist.
"""
import os

import requests

# UZ: API kalitlarini kodga YOZMAYMIZ — ularni muhit o'zgaruvchisidan
#     (environment variable) yoki settings.py dan o'qiymiz. Kalit yo'q bo'lsa
#     o'sha manba shunchaki o'chirilgan turadi va XATO BERMAYDI.
# RU: Ключи API НЕ пишем в коде — читаем их из переменных окружения или из
#     settings.py. Если ключа нет, источник просто отключён и НЕ выдаёт ошибку.
# EN: We do NOT hard-code API keys — we read them from environment variables
#     (or settings.py). If a key is missing, that source is simply disabled
#     and does NOT raise an error.
# DE: API-Schlüssel werden NICHT im Code gespeichert — wir lesen sie aus
#     Umgebungsvariablen (oder settings.py). Fehlt ein Schlüssel, ist die
#     Quelle einfach deaktiviert und wirft KEINEN Fehler.
try:
    from django.conf import settings as _dj_settings
except Exception:  # pragma: no cover
    _dj_settings = None


def _get_key(name):
    """
    UZ: Kalitni avval muhit o'zgaruvchisidan, keyin settings.py dan qidiradi.
    RU: Ищет ключ сначала в переменных окружения, затем в settings.py.
    EN: Looks up a key first in environment variables, then in settings.py.
    DE: Sucht einen Schlüssel zuerst in Umgebungsvariablen, dann in settings.py.
    """
    val = os.environ.get(name)
    if not val and _dj_settings is not None:
        val = getattr(_dj_settings, name, None)
    return (val or "").strip()


# UZ: Umumiy "sektor -> kalit so'z" lug'atlari. Har bir mamlakat o'z tilida.
# RU: Общие словари "сектор -> ключевое слово". Каждая страна на своём языке.
# EN: Shared "sector -> keyword" dictionaries. Each country in its own language.
# DE: Gemeinsame "Sektor -> Stichwort"-Wörterbücher. Jedes Land in seiner Sprache.
SECTOR_TO_DE_KEYWORD = {"medical": "Pflege", "agriculture": "Landwirtschaft", "service": "Service"}
SECTOR_TO_SE_KEYWORD = {"medical": "vård", "agriculture": "jordbruk", "service": "service"}
SECTOR_TO_EN_KEYWORD = {"medical": "care", "agriculture": "farm", "service": "service"}
ALL_SECTORS_DE_KEYWORDS = " ".join(SECTOR_TO_DE_KEYWORD.values())


def _job(id_, country, city, employer, title, apply_url, sector, source_name, posted=""):
    """
    UZ: Takrorlanmaslik uchun — bitta ish obyektini standart shaklda yasaydi.
    RU: Чтобы не повторяться — собирает один объект вакансии в стандартной форме.
    EN: To avoid repetition — builds one job object in the standard shape.
    DE: Um Wiederholung zu vermeiden — baut ein Job-Objekt in der Standardform.
    """
    title = title or "—"
    return {
        "id": id_,
        "sector": sector if sector and sector != "all" else "service",
        "country": country,
        "city": city or "",
        "employer": employer or "Noma'lum",
        # UZ: title/desc {uz,ru,en,de} obyekti bo'lishi SHART (app.js tl() kutadi).
        #     Hozircha tarjima yo'q — barcha tillarga asl matnni beramiz.
        # RU: title/desc ОБЯЗАТЕЛЬНО объект {uz,ru,en,de} (app.js ждёт tl()).
        #     Перевода пока нет — во все языки кладём исходный текст.
        # EN: title/desc MUST be an {uz,ru,en,de} object (app.js tl() expects it).
        #     No translation yet — we put the original text into every language.
        # DE: title/desc MUSS ein {uz,ru,en,de}-Objekt sein (app.js tl() erwartet es).
        #     Noch keine Übersetzung — Originaltext in jede Sprache.
        "title": {"uz": title, "ru": title, "en": title, "de": title},
        "desc": {"uz": "", "ru": "", "en": "", "de": ""},
        "tags": [],
        "requirements": [],
        "pay": None,
        "postedAt": (posted or "")[:10],
        "sourceName": source_name,
        "sourceUrl": apply_url,
    }


# ===========================================================================
# 1) BUNDESAGENTUR FÜR ARBEIT (DE) — ochiq, bepul, RASMIY
# ===========================================================================
def fetch_bundesagentur_jobs(query="", sector="all", country="DE"):
    """
    UZ: Germaniya — Bundesagentur für Arbeit Jobsuche API (bepul, ochiq).
    RU: Германия — API Bundesagentur für Arbeit (бесплатный, открытый).
    EN: Germany — Bundesagentur für Arbeit Jobsuche API (free, open).
    DE: Deutschland — Bundesagentur für Arbeit Jobsuche-API (kostenlos, offen).
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
        ref_id = item.get("hashId") or item.get("referenznummer") or ""
        apply_url = item.get("externeUrl") or f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref_id}"
        jobs.append(_job(
            id_=f"de-live-{ref_id}",
            country="DE",
            city=(item.get("arbeitsort") or {}).get("ort", ""),
            employer=item.get("arbeitgeber"),
            title=item.get("titel"),
            apply_url=apply_url,
            sector=sector,
            source_name="Bundesagentur für Arbeit",
            posted=item.get("aktuelleVeroeffentlichungsdatum") or "",
        ))
    return jobs


# ===========================================================================
# 2) ARBETSFÖRMEDLINGEN — JobSearch (SE) — ochiq, bepul, RASMIY
# ===========================================================================
def fetch_arbetsformedlingen_jobs(query="", sector="all", country="SE"):
    """
    UZ: Shvetsiya — Arbetsförmedlingen JobSearch (JobTech) API, bepul va ochiq.
    RU: Швеция — Arbetsförmedlingen JobSearch (JobTech) API, бесплатный и открытый.
    EN: Sweden — Arbetsförmedlingen JobSearch (JobTech) API, free and open.
    DE: Schweden — Arbetsförmedlingen JobSearch (JobTech) API, kostenlos und offen.
    """
    MAX_PAGES = 3
    PAGE_SIZE = 100

    sector_keyword = SECTOR_TO_SE_KEYWORD.get(sector, "")
    search_text = f"{query} {sector_keyword}".strip() or sector_keyword

    all_hits = []
    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        data = None
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

    return _parse_jobtech_hits(all_hits, sector, "Arbetsförmedlingen")


# ===========================================================================
# 3) ARBETSFÖRMEDLINGEN — JobStream (SE) — ochiq, bepul, RASMIY
# ===========================================================================
def fetch_arbetsformedlingen_jobstream(query="", sector="all", country="SE"):
    """
    UZ: Shvetsiya — Arbetsförmedlingen JobStream API. Bu "oqim" manbasi:
        oxirgi paytda qo'shilgan/yangilangan e'lonlarni beradi. Juda katta
        bo'lishi mumkin, shuning uchun biz FAQAT bir nechta sahifa olamiz va
        qidiruv so'ziga mos kelganlarini saralaymiz.
    RU: Швеция — Arbetsförmedlingen JobStream API. Это источник-"поток":
        отдаёт недавно добавленные/обновлённые объявления. Может быть очень
        большим, поэтому берём ТОЛЬКО часть и фильтруем по запросу.
    EN: Sweden — Arbetsförmedlingen JobStream API. A "stream" source: it
        returns recently added/updated ads. It can be very large, so we take
        ONLY a slice and filter by the query text.
    DE: Schweden — Arbetsförmedlingen JobStream API. Eine "Stream"-Quelle:
        liefert kürzlich hinzugefügte/aktualisierte Anzeigen. Kann sehr groß
        sein, daher nehmen wir NUR einen Teil und filtern nach dem Suchtext.
    """
    MAX_ITEMS = 120
    q = (query or "").strip().lower()

    try:
        # UZ: stream=True — faylni to'liq yuklamay, bo'lak-bo'lak o'qiymiz.
        # RU: stream=True — читаем по частям, не загружая весь ответ.
        # EN: stream=True — read in chunks instead of loading the whole body.
        # DE: stream=True — in Teilen lesen statt den ganzen Body zu laden.
        res = requests.get(
            "https://jobstream.api.jobtechdev.se/snapshot",
            headers={"accept": "application/json"},
            timeout=10,
            stream=True,
        )
        res.raise_for_status()
        import ijson  # UZ: katta JSON'ni oqim sifatida o'qish uchun (ixtiyoriy kutubxona)

        hits = []
        for obj in ijson.items(res.raw, "item"):
            headline = (obj.get("headline") or "").lower()
            if q and q not in headline:
                continue
            hits.append(obj)
            if len(hits) >= MAX_ITEMS:
                break
        return _parse_jobtech_hits(hits, sector, "Arbetsförmedlingen (JobStream)")
    except ImportError:
        # UZ: ijson o'rnatilmagan bo'lsa — bu manbani jimgina o'tkazib yuboramiz.
        # RU: Если ijson не установлен — тихо пропускаем этот источник.
        # EN: If ijson isn't installed — silently skip this source.
        # DE: Wenn ijson nicht installiert ist — diese Quelle still überspringen.
        print("[JobStream] ijson o'rnatilmagan — o'tkazib yuborildi (pip install ijson)")
        return []
    except Exception as e:
        print(f"[JobStream xatosi] {e}")
        return []


def _parse_jobtech_hits(hits, sector, source_name):
    """
    UZ: JobTech (JobSearch/JobStream) natijalarini standart shaklga aylantiradi.
    RU: Преобразует результаты JobTech (JobSearch/JobStream) в стандартную форму.
    EN: Converts JobTech (JobSearch/JobStream) results into the standard shape.
    DE: Wandelt JobTech-Ergebnisse (JobSearch/JobStream) in die Standardform um.
    """
    jobs = []
    for item in hits:
        employer = (item.get("employer") or {}).get("name")
        workplace = item.get("workplace_address") or {}
        job_id = item.get("id") or ""
        app_details = item.get("application_details") or {}
        apply_url = (
            app_details.get("url")
            or item.get("webpage_url")
            or f"https://arbetsformedlingen.se/platsbanken/annonser/{job_id}"
        )
        jobs.append(_job(
            id_=f"se-live-{job_id}",
            country="SE",
            city=workplace.get("municipality") or workplace.get("city") or "",
            employer=employer,
            title=item.get("headline"),
            apply_url=apply_url,
            sector=sector,
            source_name=source_name,
            posted=item.get("publication_date") or "",
        ))
    return jobs


# ===========================================================================
# 4) ARBEITNOW (DE/EU) — ochiq, bepul, kalit KERAK EMAS
# ===========================================================================
def fetch_arbeitnow_jobs(query="", sector="all", country="DE"):
    """
    UZ: Arbeitnow — Germaniya va Yevropadagi ishlar. To'liq ochiq API,
        kalit kerak emas. https://www.arbeitnow.com/api/job-board-api
    RU: Arbeitnow — вакансии по Германии и Европе. Полностью открытый API,
        ключ не нужен.
    EN: Arbeitnow — jobs across Germany and Europe. Fully open API, no key
        required.
    DE: Arbeitnow — Jobs in Deutschland und Europa. Vollständig offene API,
        kein Schlüssel erforderlich.
    """
    q = (query or "").strip().lower()
    sector_kw = SECTOR_TO_EN_KEYWORD.get(sector, "")
    jobs = []
    try:
        for page in range(1, 4):  # UZ: 3 sahifa yetarli / EN: 3 pages are enough
            res = requests.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"page": page},
                headers={"accept": "application/json"},
                timeout=8,
            )
            res.raise_for_status()
            items = res.json().get("data", [])
            if not items:
                break
            for item in items:
                title = item.get("title") or ""
                tags = " ".join(item.get("tags") or []).lower()
                hay = f"{title} {tags}".lower()
                # UZ: qidiruv so'zi/sektor bo'lsa — mos kelmaganlarini tashlab ketamiz.
                # RU: если есть запрос/сектор — отбрасываем несовпадающие.
                # EN: if there is a query/sector — drop the ones that don't match.
                # DE: bei Suchbegriff/Sektor — nicht passende werden verworfen.
                if q and q not in hay:
                    continue
                if sector_kw and sector_kw not in hay:
                    continue
                slug = item.get("slug") or ""
                jobs.append(_job(
                    id_=f"an-live-{slug}",
                    country="DE",
                    city=item.get("location") or "",
                    employer=item.get("company_name"),
                    title=title,
                    apply_url=item.get("url") or f"https://www.arbeitnow.com/view/{slug}",
                    sector=sector,
                    source_name="Arbeitnow",
                ))
    except Exception as e:
        print(f"[Arbeitnow xatosi] {e}")
    return jobs


# ===========================================================================
# 5) ADZUNA (ko'p davlat) — bepul, lekin KALIT kerak (ADZUNA_APP_ID/KEY)
# ===========================================================================
# UZ: Mamlakat kodimizni (COUNTRIES) Adzuna kodiga aylantiramiz.
# RU: Преобразуем наш код страны (COUNTRIES) в код Adzuna.
# EN: Map our country code (COUNTRIES) to Adzuna's country code.
# DE: Ordnet unseren Ländercode (COUNTRIES) dem Adzuna-Ländercode zu.
ADZUNA_COUNTRY = {"DE": "de", "GB": "gb", "PL": "pl", "NL": "nl", "SE": "se"}


def fetch_adzuna_jobs(query="", sector="all", country="DE"):
    """
    UZ: Adzuna — ko'plab davlatlardagi ishlar. Bepul, lekin ADZUNA_APP_ID va
        ADZUNA_APP_KEY kalitlari kerak (adzuna.com/developer dan olinadi).
        Kalit yo'q bo'lsa — bo'sh ro'yxat qaytaradi (xato bermaydi).
    RU: Adzuna — вакансии во многих странах. Бесплатно, но нужны ключи
        ADZUNA_APP_ID и ADZUNA_APP_KEY. Без ключей возвращает пустой список.
    EN: Adzuna — jobs in many countries. Free, but needs ADZUNA_APP_ID and
        ADZUNA_APP_KEY. Without keys it returns an empty list (no error).
    DE: Adzuna — Jobs in vielen Ländern. Kostenlos, benötigt aber
        ADZUNA_APP_ID und ADZUNA_APP_KEY. Ohne Schlüssel leere Liste.
    """
    app_id = _get_key("ADZUNA_APP_ID")
    app_key = _get_key("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        # UZ: Kalitsiz ishlamaydi — jimgina to'xtaymiz.
        # EN: Does nothing without keys — stop quietly.
        return []

    adz_country = ADZUNA_COUNTRY.get((country or "").upper(), "gb")
    what = f"{query} {SECTOR_TO_EN_KEYWORD.get(sector, '')}".strip()

    jobs = []
    try:
        res = requests.get(
            f"https://api.adzuna.com/v1/api/jobs/{adz_country}/search/1",
            params={
                "app_id": app_id,
                "app_key": app_key,
                "what": what,
                "results_per_page": 50,
                "content-type": "application/json",
            },
            timeout=8,
        )
        res.raise_for_status()
        for item in res.json().get("results", []):
            loc = (item.get("location") or {}).get("display_name") or ""
            jobs.append(_job(
                id_=f"adz-{adz_country}-{item.get('id', '')}",
                country=(country or "DE").upper(),
                city=loc,
                employer=(item.get("company") or {}).get("display_name"),
                title=item.get("title"),
                apply_url=item.get("redirect_url") or "",
                sector=sector,
                source_name="Adzuna",
                posted=item.get("created") or "",
            ))
    except Exception as e:
        print(f"[Adzuna xatosi] {e}")
    return jobs


# ===========================================================================
# 6) EURES (butun YeI) — RASMIY, lekin ro'yxatdan o'tish/kalit kerak
# ===========================================================================
def fetch_eures_jobs(query="", sector="all", country="ALL"):
    """
    UZ: EURES — Yevropa Ittifoqining rasmiy ish portali. Uning API'si bor,
        lekin ro'yxatdan o'tish va kalit (EURES_API_KEY) talab qiladi.
        HOZIRCHA bu zagotovka (stub): kalit qo'shilgach to'ldiriladi.
    RU: EURES — официальный портал вакансий ЕС. API существует, но требует
        регистрации и ключа (EURES_API_KEY). Пока это заготовка (stub):
        будет заполнена после добавления ключа.
    EN: EURES — the EU's official job portal. It has an API but requires
        registration and a key (EURES_API_KEY). For now this is a stub:
        to be completed once a key is added.
    DE: EURES — das offizielle Jobportal der EU. Es gibt eine API, die aber
        Registrierung und einen Schlüssel (EURES_API_KEY) erfordert. Vorerst
        ein Stub: wird nach dem Hinzufügen eines Schlüssels vervollständigt.
    """
    api_key = _get_key("EURES_API_KEY")
    if not api_key:
        return []
    # UZ: Kalit bo'lsa — bu yerga haqiqiy so'rov kodi yoziladi.
    # RU: При наличии ключа — здесь будет реальный запрос.
    # EN: With a key — the real request goes here.
    # DE: Mit Schlüssel — hier kommt die echte Anfrage.
    return []


# ===========================================================================
# 7) FIND A JOB — gov.uk (GB) — RASMIY, kalit kerak
# ===========================================================================
def fetch_findajob_jobs(query="", sector="all", country="GB"):
    """
    UZ: Buyuk Britaniya — "Find a Job" (gov.uk). Rasmiy, lekin API kaliti
        (FINDAJOB_API_KEY) kerak. Zagotovka: kalit qo'shilsa to'ldiriladi.
    RU: Великобритания — "Find a Job" (gov.uk). Официально, но нужен ключ
        (FINDAJOB_API_KEY). Заготовка: заполнится при наличии ключа.
    EN: United Kingdom — "Find a Job" (gov.uk). Official, but needs an API
        key (FINDAJOB_API_KEY). Stub: filled in once a key is added.
    DE: Vereinigtes Königreich — "Find a Job" (gov.uk). Offiziell, benötigt
        aber einen API-Schlüssel (FINDAJOB_API_KEY). Stub.
    """
    api_key = _get_key("FINDAJOB_API_KEY")
    if not api_key:
        return []
    return []


# ===========================================================================
# 8) PRACA.GOV.PL (PL) — RASMIY (CBOP), API murakkab
# ===========================================================================
def fetch_praca_jobs(query="", sector="all", country="PL"):
    """
    UZ: Polsha — Praca.gov.pl (CBOP). Rasmiy, lekin API murakkab/ro'yxatdan
        o'tish kerak. Zagotovka sifatida qoldiramiz.
    RU: Польша — Praca.gov.pl (CBOP). Официально, но API сложный/требует
        регистрации. Оставляем как заготовку.
    EN: Poland — Praca.gov.pl (CBOP). Official, but the API is complex / needs
        registration. Left as a stub.
    DE: Polen — Praca.gov.pl (CBOP). Offiziell, aber die API ist komplex /
        erfordert Registrierung. Als Stub belassen.
    """
    return []


# ===========================================================================
# 9) WERKEN BIJ DE OVERHEID (NL) — davlat ishlari
# ===========================================================================
def fetch_werkenbijdeoverheid_jobs(query="", sector="all", country="NL"):
    """
    UZ: Niderlandiya — davlat idoralari ishlari. Ochiq API noaniq —
        zagotovka sifatida qoldiramiz.
    RU: Нидерланды — вакансии госучреждений. Открытый API неясен — заготовка.
    EN: Netherlands — government jobs. Open API is unclear — left as a stub.
    DE: Niederlande — Behördenjobs. Offene API unklar — als Stub belassen.
    """
    return []


# ===========================================================================
# 10) ÄRZTESTELLEN (DE) — tibbiyot ishlari
# ===========================================================================
def fetch_arztestellen_jobs(query="", sector="all", country="DE"):
    """
    UZ: Germaniya — Ärztestellen (shifokorlar uchun ishlar). Ochiq API
        noaniq — zagotovka sifatida qoldiramiz.
    RU: Германия — Ärztestellen (вакансии для врачей). Открытый API неясен —
        заготовка.
    EN: Germany — Ärztestellen (jobs for doctors). Open API is unclear — stub.
    DE: Deutschland — Ärztestellen (Stellen für Ärzte). Offene API unklar — Stub.
    """
    return []


# ===========================================================================
# SOURCES — barcha manbalar registri (ro'yxati)
# ===========================================================================
# UZ: Har bir manba: kaliti (key), ko'rinadigan nomi (name), qaysi
#     davlatlarga tegishli (countries), chaqiriladigan funksiya (fn), va
#     yoqilgan/o'chirilgan holati (enabled). Frontend "manba filtri"
#     tugmalari shu ro'yxatdan /api/sources orqali keladi.
# RU: Каждый источник: key, отображаемое имя (name), страны (countries),
#     функция (fn) и статус enabled. Кнопки "фильтр источника" на фронтенде
#     берутся отсюда через /api/sources.
# EN: Each source: its key, display name, the countries it covers, the
#     function (fn), and an enabled flag. The frontend "source filter"
#     buttons come from this list via /api/sources.
# DE: Jede Quelle: key, Anzeigename (name), Länder (countries), Funktion (fn)
#     und ein enabled-Flag. Die "Quellen-Filter"-Buttons im Frontend kommen
#     über /api/sources aus dieser Liste.
SOURCES = [
    {"key": "bundesagentur", "name": "Bundesagentur für Arbeit", "countries": ["DE"], "fn": fetch_bundesagentur_jobs, "enabled": True},
    {"key": "arbetsformedlingen", "name": "Arbetsförmedlingen", "countries": ["SE"], "fn": fetch_arbetsformedlingen_jobs, "enabled": True},
    {"key": "jobstream", "name": "Arbetsförmedlingen (JobStream)", "countries": ["SE"], "fn": fetch_arbetsformedlingen_jobstream, "enabled": True},
    {"key": "arbeitnow", "name": "Arbeitnow", "countries": ["DE"], "fn": fetch_arbeitnow_jobs, "enabled": True},
    {"key": "adzuna", "name": "Adzuna", "countries": ["DE", "GB", "PL", "NL", "SE"], "fn": fetch_adzuna_jobs, "enabled": True, "needs_key": "ADZUNA_APP_ID"},
    {"key": "eures", "name": "EURES", "countries": ["DE", "GB", "PL", "NL", "SE"], "fn": fetch_eures_jobs, "enabled": True, "needs_key": "EURES_API_KEY"},
    {"key": "findajob", "name": "Find a Job (gov.uk)", "countries": ["GB"], "fn": fetch_findajob_jobs, "enabled": True, "needs_key": "FINDAJOB_API_KEY"},
    {"key": "praca", "name": "Praca.gov.pl", "countries": ["PL"], "fn": fetch_praca_jobs, "enabled": True},
    {"key": "werkenbijdeoverheid", "name": "WerkenbijdeOverheid", "countries": ["NL"], "fn": fetch_werkenbijdeoverheid_jobs, "enabled": True},
    {"key": "arztestellen", "name": "Ärztestellen", "countries": ["DE"], "fn": fetch_arztestellen_jobs, "enabled": True},
]

SOURCES_BY_KEY = {s["key"]: s for s in SOURCES}


def list_sources():
    """
    UZ: Frontend uchun manbalar ro'yxatini qaytaradi (funksiyasiz — toza ma'lumot).
        'ready' — kalit kerakmi va u mavjudmi degan belgini ham qo'shamiz.
    RU: Возвращает список источников для фронтенда (без функций). 'ready'
        показывает, нужен ли ключ и есть ли он.
    EN: Returns the source list for the frontend (without functions). 'ready'
        marks whether a key is required and present.
    DE: Gibt die Quellenliste für das Frontend zurück (ohne Funktionen).
        'ready' zeigt, ob ein Schlüssel nötig und vorhanden ist.
    """
    out = []
    for s in SOURCES:
        needs = s.get("needs_key")
        ready = True if not needs else bool(_get_key(needs))
        out.append({
            "key": s["key"],
            "name": s["name"],
            "countries": s["countries"],
            "ready": ready,
        })
    return out


def get_jobs(query="", sector="all", country="ALL", source="all"):
    """
    UZ: DISPETCHER — bitta joy. Frontend qaysi manba/mamlakatni so'rasa,
        shu manbalarni chaqirib, natijalarni birlashtiradi.
        - source != "all" bo'lsa: FAQAT o'sha manbani chaqiradi.
        - source == "all" bo'lsa: mamlakatga mos BARCHA yoqilgan manbalarni.
        Har bir manba alohida try/except ichida — biri yiqilsa, qolganlari ishlaydi.
    RU: ДИСПЕТЧЕР — одна точка входа. По запросу источника/страны вызывает
        нужные источники и объединяет результаты. Каждый источник в своём
        try/except — если один упадёт, остальные продолжат работать.
    EN: DISPATCHER — one entry point. Given a source/country request it calls
        the right sources and merges results. Each source runs in its own
        try/except, so one failing source does not break the others.
    DE: DISPATCHER — ein Einstiegspunkt. Ruft je nach Quellen-/Länderanfrage
        die passenden Quellen auf und führt die Ergebnisse zusammen. Jede
        Quelle läuft in eigenem try/except.
    """
    country = (country or "ALL").upper()
    source = source or "all"
    jobs = []

    # UZ: 1-holat — aniq bitta manba so'ralgan.
    # RU: Случай 1 — запрошен конкретный источник.
    # EN: Case 1 — a specific source was requested.
    # DE: Fall 1 — eine bestimmte Quelle wurde angefragt.
    if source != "all":
        s = SOURCES_BY_KEY.get(source)
        if not s or not s.get("enabled"):
            return []
        try:
            use_country = country if country != "ALL" else (s["countries"][0] if s["countries"] else "ALL")
            jobs += s["fn"](query=query, sector=sector, country=use_country) or []
        except Exception as e:
            print(f"[{source} dispatch xatosi] {e}")
        return jobs

    # UZ: 2-holat — "barcha manbalar": mamlakatga mos yoqilganlarini chaqiramiz.
    # RU: Случай 2 — "все источники": вызываем подходящие по стране.
    # EN: Case 2 — "all sources": call the enabled ones that match the country.
    # DE: Fall 2 — "alle Quellen": passende aktivierte je nach Land aufrufen.
    for s in SOURCES:
        if not s.get("enabled"):
            continue
        if country != "ALL" and country not in s["countries"]:
            continue
        try:
            use_country = country if country != "ALL" else (s["countries"][0] if s["countries"] else "ALL")
            jobs += s["fn"](query=query, sector=sector, country=use_country) or []
        except Exception as e:
            print(f"[{s['key']} dispatch xatosi] {e}")
    return jobs
