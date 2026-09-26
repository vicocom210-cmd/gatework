/* ===== GATE WORK — til, kun/tun rejimi va animatsiyalar ===== */

const LS_LANG = "gatework-lang";
const LS_THEME = "gatework-theme";
const LS_ASSETS = "gatework-assets";
const LS_CURRENCY = "gatework-currency";
const SS_INTRO = "gatework-intro-shown";

let lang = localStorage.getItem(LS_LANG) || "uz";
if (!LANGS.includes(lang)) lang = "uz";

let displayCurrency = localStorage.getItem(LS_CURRENCY) || "native";
let exchangeRates = null; // { EUR:1, USD:.., GBP:.., SEK:.., PLN:.. } — EUR bazaviy

/* ---------- VALYUTA ALMASHTIRISH ---------- */
async function initCurrency() {
  try {
    const res = await fetch("/api/rates");
    if (res.ok) exchangeRates = await res.json();
  } catch (e) {
    console.error("Valyuta kurslarini olishda xatolik:", e);
  }

  document.querySelectorAll("[data-cur-btn]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.curBtn === displayCurrency);
    btn.addEventListener("click", () => {
      displayCurrency = btn.dataset.curBtn;
      localStorage.setItem(LS_CURRENCY, displayCurrency);
      document.querySelectorAll("[data-cur-btn]").forEach((b) => b.classList.toggle("active", b === btn));
      renderJobs(); // narxlarni yangi valyutada qayta chizish
    });
  });
}

/* pay.currency'dan tanlangan valyutaga aylantiradi. Agar kurslar hali
   kelmagan bo'lsa yoki "native" tanlangan bo'lsa — asl qiymatni qaytaradi. */
function convertPay(pay) {
  if (displayCurrency === "native" || !exchangeRates || !exchangeRates[pay.currency] || !exchangeRates[displayCurrency]) {
    return pay;
  }
  const toEur = (v) => v / exchangeRates[pay.currency];
  const fromEur = (v) => v * exchangeRates[displayCurrency];
  return {
    ...pay,
    min: fromEur(toEur(pay.min)),
    max: fromEur(toEur(pay.max)),
    currency: displayCurrency,
  };
}

const t = (key) => (STRINGS[key] ? STRINGS[key][lang] : key);
const tl = (obj) => (obj ? obj[lang] : "");

/* ---------- KUN / TUN ---------- */
function applyTheme(theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  localStorage.setItem(LS_THEME, theme);
  document.querySelectorAll("[data-theme-icon]").forEach((el) => {
    el.textContent = theme === "dark" ? "☀" : "☾";
  });
  document.querySelectorAll("[data-logo]").forEach((img) => {
    img.src = img.dataset[theme === "dark" ? "white" : "black"];
  });
}

function initTheme() {
  const saved = localStorage.getItem(LS_THEME);
  applyTheme(saved === "light" || saved === "dark" ? saved : "dark");
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) =>
    btn.addEventListener("click", () => {
      applyTheme(document.documentElement.classList.contains("dark") ? "light" : "dark");
    }),
  );
}

/* ---------- KIRISHDAGI LOGO ANIMATSIYASI (intro) ---------- */
function initIntro() {
  const intro = document.querySelector("[data-intro]");
  if (!intro) return;
  if (sessionStorage.getItem(SS_INTRO)) {
    intro.remove();
    return;
  }
  sessionStorage.setItem(SS_INTRO, "1");
  document.body.classList.add("intro-lock");

  const slogan = intro.querySelector("[data-intro-slogan]");
  if (slogan) {
    slogan.innerHTML = t("slogan")
      .split(" ")
      .map((w, i) => `<i style="animation-delay:${0.7 + i * 0.14}s">${w}</i>`)
      .join(" ");
  }

  requestAnimationFrame(() => intro.classList.add("play"));
  setTimeout(() => intro.classList.add("done"), 2600);
  setTimeout(() => {
    intro.remove();
    document.body.classList.remove("intro-lock");
  }, 3400);
}

/* ---------- TIL ---------- */
function initLang() {
  document.querySelectorAll("[data-lang-btn]").forEach((btn) =>
    btn.addEventListener("click", () => {
      lang = btn.dataset.langBtn;
      localStorage.setItem(LS_LANG, lang);
      document.documentElement.lang = lang;
      renderAll();
    }),
  );
}

function renderText() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-t]").forEach((el) => {
    el.textContent = t(el.dataset.t);
  });
  document.querySelectorAll("[data-t-ph]").forEach((el) => {
    el.placeholder = t(el.dataset.tPh);
  });
  document.querySelectorAll("[data-lang-btn]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.langBtn === lang);
  });
}

/* ---------- SANOQ (counter) ---------- */
function animateCounter(el) {
  const to = Number(el.dataset.to);
  const suffix = el.dataset.suffix || "";
  const dur = 1200;
  const start = performance.now();
  function step(now) {
    const p = Math.min((now - start) / dur, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(to * eased) + suffix;
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/* ---------- SCROLL REVEAL ---------- */
function initReveal() {
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        e.target.classList.add("in");
        if (e.target.dataset.to) animateCounter(e.target);
        e.target.querySelectorAll("[data-to]").forEach(animateCounter);
        e.target.querySelectorAll(".slogan i").forEach((w, i) => {
          w.style.transitionDelay = 0.35 + i * 0.12 + "s";
        });
        io.unobserve(e.target);
      });
    },
    { threshold: 0.2, rootMargin: "-40px" },
  );
  document.querySelectorAll(".reveal, .story, .logo-reveal, [data-to]").forEach((el) => io.observe(el));
}

/* ---------- MARQUEE ---------- */
function renderMarquee() {
  const track = document.querySelector("[data-marquee]");
  if (!track) return;
  track.innerHTML = [...SOURCES, ...SOURCES].map((s) => `<span>${s}</span>`).join("");
}

/* ---------- BENEFITS ---------- */
const BENEFITS = [
  { icon: "✔", title: "b1t", text: "b1d" },
  { icon: "🌐", title: "b2t", text: "b2d" },
  { icon: "🛂", title: "b3t", text: "b3d" },
  { icon: "✦", title: "b4t", text: "b4d" },
];

function renderBenefits() {
  const box = document.querySelector("[data-benefits]");
  if (!box) return;
  box.innerHTML = BENEFITS.map(
    (b, i) => `
    <div class="bcard glass reveal" style="transition-delay:${i * 0.08}s">
      <span class="ico">${b.icon}</span>
      <h3>${t(b.title)}</h3>
      <p>${t(b.text)}</p>
    </div>`,
  ).join("");
}

/* ---------- FOOTER manbalar ---------- */
function renderFooterSources() {
  const box = document.querySelector("[data-footer-sources]");
  if (box) box.innerHTML = SOURCES.map((s) => `<li>${s}</li>`).join("");
}

/* ---------- VAKANSIYALAR (haqiqiy backend orqali) ---------- */
let myAssets = [];
try {
  myAssets = JSON.parse(localStorage.getItem(LS_ASSETS) || "[]");
} catch (e) {
  myAssets = [];
}

const state = { query: "", country: "all", sector: "all", visaOnly: false, period: "all", payMin: "", payMax: "", visa: "any" };

/* "Menda bor" filtri — foydalanuvchi o'zida bor hujjat/imkoniyatlarni
   tanlaydi, faqat shularga mos keladigan ishlar chiqadi. */
function renderAssetFilter() {
  const box = document.querySelector("[data-asset-filter]");
  if (!box) return;
  box.innerHTML = ASSETS.map(
    (a) => `<button class="chip ${myAssets.includes(a.key) ? "on" : ""}" data-asset="${a.key}">
      <span>${a.icon}</span>${t(a.label)}</button>`,
  ).join("");

  box.querySelectorAll("[data-asset]").forEach((b) =>
    b.addEventListener("click", () => {
      const key = b.dataset.asset;
      myAssets = myAssets.includes(key) ? myAssets.filter((x) => x !== key) : [...myAssets, key];
      localStorage.setItem(LS_ASSETS, JSON.stringify(myAssets));
      renderFilters();
      renderJobs();
    }),
  );

  const clear = document.querySelector("[data-asset-clear]");
  if (clear)
    clear.onclick = () => {
      myAssets = [];
      localStorage.setItem(LS_ASSETS, "[]");
      renderFilters();
      renderJobs();
    };
}

function renderFilters() {
  const cWrap = document.querySelector("[data-country-pills]");
  if (cWrap) {
    cWrap.innerHTML =
      `<button class="pill ${state.country === "all" ? "active" : ""}" data-country="all">${t("allCountries")}</button>` +
      COUNTRIES.map(
        (c) =>
          `<button class="pill ${state.country === c.code ? "active" : ""}" data-country="${c.code}">${c.flag} ${tl(c.name)}</button>`,
      ).join("");
    cWrap.querySelectorAll("[data-country]").forEach((b) =>
      b.addEventListener("click", () => {
        state.country = b.dataset.country;
        renderFilters();
        renderJobs();
      }),
    );
  }

  const sWrap = document.querySelector("[data-sector-pills]");
  if (sWrap) {
    sWrap.innerHTML =
      `<button class="pill ${state.sector === "all" ? "active" : ""}" data-sector="all">${t("allSectors")}</button>` +
      SECTORS.map(
        (s) =>
          `<button class="pill ${state.sector === s.id ? "active" : ""}" data-sector="${s.id}">${s.icon} ${tl(s.name)}</button>`,
      ).join("");
    sWrap.querySelectorAll("[data-sector]").forEach((b) =>
      b.addEventListener("click", () => {
        state.sector = b.dataset.sector;
        renderFilters();
        renderJobs();
      }),
    );
  }

  const pWrap = document.querySelector("[data-period-pills]");
  if (pWrap) {
    pWrap.innerHTML =
      `<button class="pill sm ${state.period === "all" ? "active" : ""}" data-period="all">${t("anyPeriod")}</button>` +
      PAY_PERIODS.map(
        (p) => `<button class="pill sm ${state.period === p.id ? "active" : ""}" data-period="${p.id}">${tl(p.name)}</button>`,
      ).join("");
    pWrap.querySelectorAll("[data-period]").forEach((b) =>
      b.addEventListener("click", () => {
        state.period = b.dataset.period;
        renderFilters();
        renderJobs();
      }),
    );
  }

  const vWrap = document.querySelector("[data-visa-pills]");
  if (vWrap) {
    vWrap.innerHTML = [["any", "visaAny"], ["sponsor", "visaSponsor"], ["none", "visaNotNeeded"]]
      .map(([v, k]) => `<button class="pill sm ${state.visa === v ? "active" : ""}" data-visa="${v}">${t(k)}</button>`)
      .join("");
    vWrap.querySelectorAll("[data-visa]").forEach((b) =>
      b.addEventListener("click", () => {
        state.visa = b.dataset.visa;
        renderFilters();
        renderJobs();
      }),
    );
  }

  const active =
    (state.country !== "all") + (state.sector !== "all") + (state.period !== "all") +
    (state.payMin !== "") + (state.payMax !== "") + (state.visa !== "any") + myAssets.length;
  document.querySelectorAll("[data-filter-count],[data-filter-count2]").forEach((el) => {
    el.textContent = active;
    el.hidden = active === 0;
  });

  renderAssetFilter();
}

/* ---------- VAKANSIYALAR: bo'lib-bo'lib yuklash + brauzer keshi ----------
   Server vakansiyalarni sahifalab (?page=N) beradi. Birinchi sahifa kelishi
   bilan kartalar chiziladi, qolganlari orqadan qo'shilib boradi.
   Natija localStorage'da saqlanadi: sahifa yangilanganda vakansiyalar
   darhol qayta chiqadi va yuklash to'xtagan joyidan davom etadi. */
const LS_JOBS = "gatework-jobs-v2"; // versiya o'zgarsa — brauzerdagi eski kesh tashlanadi
const JOBS_CACHE_MS = 15 * 60 * 1000;
let jobsList = [];
let jobsById = {};
let jobsKey = null;       // hozir ko'rsatilayotgan qidiruv (davlat|soha|so'z)
let jobsLoading = false;
let jobsAbort = null;

function jobsQueryKey() {
  return [state.country === "all" ? "ALL" : state.country, state.sector, (state.query || "").trim().toLowerCase()].join("|");
}

function readJobsCache(key) {
  try {
    const c = JSON.parse(localStorage.getItem(LS_JOBS) || "null");
    if (c && c.key === key && Date.now() - c.at < JOBS_CACHE_MS && Array.isArray(c.jobs)) return c;
  } catch {}
  return null;
}

function writeJobsCache(key, jobs, nextPage, at) {
  try {
    localStorage.setItem(LS_JOBS, JSON.stringify({ key, at: at || Date.now(), jobs, nextPage }));
  } catch {}
}

async function fetchJobsPage(page, signal) {
  const params = new URLSearchParams({
    country: state.country === "all" ? "ALL" : state.country,
    sector: state.sector,
    query: state.query || "",
    visaOnly: state.visaOnly ? "true" : "false",
    visa: state.visa,
    period: state.period,
    payMin: state.payMin,
    payMax: state.payMax,
    assets: myAssets.join(","),
    lang: lang,
    page: String(page),
  });
  const res = await fetch(`/api/jobs?${params.toString()}`, { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function formatSalary(job) {
  const pay = job.pay;
  if (!pay) {
    if (job.salaryMin != null) {
      const sym = job.currency === "GBP" ? "£" : job.currency === "EUR" ? "€" : job.currency || "";
      return `${sym}${job.salaryMin} – ${sym}${job.salaryMax}`;
    }
    return `<i>${t("payUnknown")}</i>`;
  }
  const displayPay = convertPay(pay);
  const sym = { EUR: "€", GBP: "£", SEK: "kr", PLN: "zł", USD: "$" }[displayPay.currency] || displayPay.currency;
  const fmt = (n) => Number(n).toLocaleString("de-DE", { maximumFractionDigits: 2 });
  const range = displayPay.min === displayPay.max ? fmt(displayPay.min) : `${fmt(displayPay.min)} – ${fmt(displayPay.max)}`;
  const per = PAY_PERIODS.find((p) => p.id === pay.period);
  return `<b>${range} ${sym}</b> / ${per ? tl(per.short) : pay.period}`;
}

function assetLabel(key) {
  const found = ASSETS.find((a) => a.key === key);
  return found ? `${found.icon} ${t(found.label)}` : key;
}

function jobCardHtml(job, i) {
  const c = COUNTRIES.find((x) => x.code === job.country);
  const reqs = (job.requirements || [])
    .map((r) => `<span class="req ${myAssets.includes(r) ? "match" : ""}">${myAssets.includes(r) ? "✓ " : ""}${assetLabel(r)}</span>`)
    .join("");
  return `
  <article class="card glass" data-job-id="${job.id}" style="animation-delay:${Math.min(i * 0.06, 1.2)}s">
    <div class="card-top">
      <div>
        <h3>${tl(job.title)}</h3>
        <p class="employer">${job.employer}</p>
      </div>
      <span class="flag">${c ? c.flag : ""}</span>
    </div>
    <div class="meta">
      <span><b>◉</b> ${job.city}, ${c ? tl(c.name) : job.country}</span>
      <span class="pay">${formatSalary(job)}</span>
    </div>
    <p class="desc">${tl(job.desc) || ""}</p>
    <div class="tags">${(job.tags || []).map((tag) => `<span>${tl(VISA_TAGS[tag])}</span>`).join("")}</div>
    ${reqs ? `<div class="reqs"><em>${t("needs")}:</em>${reqs}</div>` : ""}
    <div class="card-foot">
      <span>${t("source")}: ${job.sourceName}</span>
      <a class="btn-apply" title="${t("applyHint")}" href="${canApply() ? job.sourceUrl : "#"}" ${canApply() ? 'target="_blank" rel="noopener noreferrer" data-apply' : isLoggedIn ? 'data-need-plan' : `data-need-login="${encodeURIComponent(job.sourceUrl)}"`}>${canApply() ? "" : "🔒 "}${t("applyNow")} ↗</a>
    </div>
  </article>`;
}

/* Kartalarga hodisalarni ulaydi (faqat root ichidagi yangi kartalarga). */
function bindJobCards(root) {
  root.querySelectorAll("[data-need-login]").forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const redirect = encodeURIComponent(decodeURIComponent(a.dataset.needLogin));
      window.location.href = `/login?mode=signup&redirect=${redirect}`;
    });
  });

  // TARIF: PRO/MAX bo'lmasa — to'lov oynasi
  root.querySelectorAll("[data-need-plan]").forEach((a) => {
    a.addEventListener("click", (e) => { e.preventDefault(); openPlanModal(); });
  });

  // ARXIV: ariza bosilganda 'apply', kartaga qaralganda (1.2s) yoki bosilganda 'view'
  root.querySelectorAll("[data-apply]").forEach((a) => {
    a.addEventListener("click", () => {
      const card = a.closest("[data-job-id]");
      track("apply", jobsById[card && card.dataset.jobId]);
    });
  });
  root.querySelectorAll("[data-job-id]").forEach((card) => {
    let timer;
    const job = jobsById[card.dataset.jobId];
    card.addEventListener("mouseenter", () => { timer = setTimeout(() => track("view", job), 1200); });
    card.addEventListener("mouseleave", () => clearTimeout(timer));
    card.addEventListener("click", (e) => { if (!e.target.closest("a")) track("view", job); });
  });
}

function paintJobsStatus() {
  const grid = document.querySelector("[data-jobs]");
  if (!grid) return;
  const countEl = document.querySelector("[data-count]");
  if (countEl) countEl.innerHTML = `<b>${jobsList.length}</b> ${t("resultsCount")}${jobsLoading && jobsList.length ? " …" : ""}`;
  let more = grid.querySelector("[data-jobs-more]");
  if (jobsLoading) {
    if (!more) {
      more = document.createElement("p");
      more.className = "empty glass-soft";
      more.setAttribute("data-jobs-more", "");
      grid.appendChild(more);
    }
    more.textContent = jobsList.length ? t("jobsLoadingMore") : t("jobsLoading");
  } else if (more) {
    more.remove();
  }
  const empty = grid.querySelector("[data-jobs-empty]");
  if (!jobsLoading && !jobsList.length) {
    if (!empty) grid.innerHTML = `<p class="empty glass-soft" data-jobs-empty>${t("empty")}</p>`;
  } else if (empty) {
    empty.remove();
  }
}

/* Butun ro'yxatni qaytadan chizadi (til / valyuta / tarif o'zgarganda). */
function paintJobs() {
  const grid = document.querySelector("[data-jobs]");
  if (!grid) return;
  grid.innerHTML = jobsList.map(jobCardHtml).join("");
  bindJobCards(grid);
  paintJobsStatus();
}

/* Yangi kelgan kartalarni ro'yxat oxiriga qo'shadi — birma-bir paydo bo'ladi. */
function appendJobs(fresh) {
  const grid = document.querySelector("[data-jobs]");
  if (!grid || !fresh.length) return;
  const tmp = document.createElement("div");
  tmp.innerHTML = fresh.map(jobCardHtml).join("");
  bindJobCards(tmp);
  const more = grid.querySelector("[data-jobs-more]");
  while (tmp.firstElementChild) grid.insertBefore(tmp.firstElementChild, more);
}

function addJobs(list) {
  const fresh = (list || []).filter((j) => j && !jobsById[j.id]);
  fresh.forEach((j) => (jobsById[j.id] = j));
  jobsList = jobsList.concat(fresh);
  return fresh;
}

async function loadJobsFrom(key, startPage, cachedAt) {
  if (jobsAbort) jobsAbort.abort();
  const ctrl = new AbortController();
  jobsAbort = ctrl;
  jobsLoading = true;
  paintJobsStatus();
  let page = startPage;
  try {
    while (page) {
      const data = await fetchJobsPage(page, ctrl.signal);
      if (jobsAbort !== ctrl) return;
      appendJobs(addJobs(Array.isArray(data) ? data : data.jobs));
      page = data.hasMore ? page + 1 : null;
      writeJobsCache(key, jobsList, page, cachedAt);
      paintJobsStatus();
    }
  } catch (e) {
    if (e.name === "AbortError") return;
    console.error("Vakansiyalarni olishda xatolik:", e);
    if (!jobsList.length) jobsKey = null; // keyingi safar qayta urinib ko'riladi
  }
  if (jobsAbort === ctrl) {
    jobsAbort = null;
    jobsLoading = false;
    paintJobsStatus();
  }
}

async function renderJobs() {
  const grid = document.querySelector("[data-jobs]");
  if (!grid) return;

  const key = jobsQueryKey();
  // Qidiruv o'zgarmagan (masalan til, valyuta yoki filtr tugmasi) —
  // serverdan qayta so'ramasdan, bor ro'yxatni qayta chizamiz.
  if (key === jobsKey) {
    paintJobs();
    return;
  }
  jobsKey = key;
  if (jobsAbort) { jobsAbort.abort(); jobsAbort = null; } // eski qidiruv yuklanishini to'xtatamiz
  jobsList = [];
  jobsById = {};

  const cached = readJobsCache(key);
  if (cached) {
    addJobs(cached.jobs);
    jobsLoading = !!cached.nextPage;
    paintJobs();
    if (cached.nextPage) await loadJobsFrom(key, cached.nextPage, cached.at);
    return;
  }

  paintJobs();
  await loadJobsFrom(key, 1);
}

const tracked = new Set();
function track(kind, job) {
  if (!isLoggedIn || !job) return;
  const key = kind + ":" + job.id;
  if (kind === "view" && tracked.has(key)) return;
  tracked.add(key);
  fetch("/api/track", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind,
      job: { id: job.id, title: tl(job.title), employer: job.employer, city: job.city, country: job.country, url: job.sourceUrl },
    }),
  }).catch(() => {});
}

function ping(kind) {
  if (!isLoggedIn) return;
  fetch("/api/activity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind }),
  }).catch(() => {});
}

function initJobsControls() {
  const input = document.querySelector("[data-search]");
  if (input && !input.dataset.bound) {
    input.dataset.bound = "1";
    let timer;
    input.addEventListener("input", (e) => {
      state.query = e.target.value;
      clearTimeout(timer);
      timer = setTimeout(() => {
        renderJobs();
        ping("search");
      }, 300);
    });
  }

  [["[data-pay-min]", "payMin"], ["[data-pay-max]", "payMax"]].forEach(([sel, key]) => {
    const el = document.querySelector(sel);
    if (el && !el.dataset.bound) {
      el.dataset.bound = "1";
      let timer;
      el.addEventListener("input", () => {
        state[key] = el.value;
        clearTimeout(timer);
        timer = setTimeout(() => {
          renderFilters();
          renderJobs();
        }, 400);
      });
    }
  });

  const rs = document.querySelector("[data-filter-reset]");
  if (rs && !rs.dataset.bound) {
    rs.dataset.bound = "1";
    rs.addEventListener("click", () => {
      Object.assign(state, { country: "all", sector: "all", period: "all", payMin: "", payMax: "", visa: "any", visaOnly: false });
      myAssets = [];
      localStorage.setItem(LS_ASSETS, "[]");
      document.querySelectorAll("[data-pay-min],[data-pay-max]").forEach((i) => (i.value = ""));
      renderFilters();
      renderJobs();
    });
  }

  const sw = document.querySelector("[data-visa-switch]");
  if (sw && !sw.dataset.bound) {
    sw.dataset.bound = "1";
    sw.addEventListener("click", () => {
      state.visaOnly = !state.visaOnly;
      sw.classList.toggle("on", state.visaOnly);
      renderJobs();
    });
  }
}

/* ---------- STORY (biz haqimizda) — dumaloq rasmlar ---------- */
function renderStory() {
  const box = document.querySelector("[data-story]");
  if (!box) return;
  box.innerHTML = STORY.map(
    (s, i) => `
    <section class="story ${i % 2 ? "flip" : ""}">
      <div class="shot round glass">
        <img src="${s.img}" alt="${tl(s.title)}" loading="lazy" />
        <div class="aurora"></div>
        <span class="step glass-soft">${s.step}</span>
      </div>
      <div class="txt">
        <h2>${tl(s.title)}</h2>
        <p>${tl(s.text)}</p>
        <div class="line"></div>
      </div>
    </section>`,
  ).join("");
}

function renderSlogan() {
  document.querySelectorAll("[data-slogan]").forEach((el) => {
    el.innerHTML = t("slogan").split(" ").map((w) => `<i>${w}</i>`).join(" ");
  });
}

/* ---------- HAQIQIY LOGIN HOLATI (backend /api/me orqali) ---------- */
let isLoggedIn = false;
let currentUser = null;

async function checkAuthState() {
  try {
    const res = await fetch("/api/me");
    if (res.ok) {
      const data = await res.json();
      isLoggedIn = true;
      currentUser = data.user;
      if (data.user.assets && data.user.assets.length && !myAssets.length) {
        myAssets = data.user.assets;
        localStorage.setItem(LS_ASSETS, JSON.stringify(myAssets));
      }
    } else {
      isLoggedIn = false;
      currentUser = null;
    }
  } catch {
    isLoggedIn = false;
  }
  window.isLoggedIn = isLoggedIn;
  window.currentUser = currentUser;
  renderNavAuth();
}

/* ---------- TARIFLAR (PRO / MAX) ---------- */
const PLAN_INFO = { pro: { price: 20, per: "planPerMonth" }, max: { price: 180, per: "planPerYear" } };
function canApply() {
  return !!(isLoggedIn && currentUser && (currentUser.planActive || currentUser.isAdmin));
}
function planLabel(p) { return p === "pro" ? t("planPro") : p === "max" ? t("planMax") : t("planFree"); }

let planCard = "";
async function openPlanModal() {
  let modal = document.querySelector("[data-plan-modal]");
  if (!modal) {
    modal = document.createElement("div");
    modal.className = "modal plan-modal";
    modal.setAttribute("data-plan-modal", "");
    document.body.appendChild(modal);
    modal.addEventListener("click", (e) => { if (e.target === modal || e.target.closest("[data-plan-close]")) closePlanModal(); });
    try { const r = await fetch("/api/plans"); const d = await r.json(); planCard = d.card || ""; } catch {}
  }
  const cur = currentUser ? currentUser.plan : "free";
  modal.innerHTML = `
    <div class="modal-card glass plan-card-wrap">
      <button class="icon-btn close" type="button" data-plan-close aria-label="Yopish">✕</button>
      <span class="adm-badge">💎 ${t("planYourPlan")}: ${planLabel(cur)}</span>
      <h2>${t("planTitle")}</h2>
      <p class="tagline">${t("planSub")}</p>
      <div class="plans">
        ${["pro", "max"].map((p) => `
          <article class="plan ${p}">
            ${p === "max" ? `<span class="plan-pop">${t("planPopular")}</span>` : ""}
            <h3>${planLabel(p)}</h3>
            <div class="price"><b>$${PLAN_INFO[p].price}</b><small>${t(PLAN_INFO[p].per)}</small></div>
            <p>${t(p === "pro" ? "planProDesc" : "planMaxDesc")}</p>
            <button class="btn-primary big" type="button" data-plan-pay="${p}">${t("planPay")} →</button>
          </article>`).join("")}
      </div>
      ${planCard ? `<p class="plan-cardno">💳 ${t("planCard")}: <b>${planCard}</b></p>` : ""}
      <details class="plan-how"><summary>${t("planHow")}</summary>
        <ol><li>${t("planHow1")}</li><li>${t("planHow2")}</li><li>${t("planHow3")}</li><li>${t("planHow4")}</li></ol>
      </details>
    </div>`;
  modal.hidden = false;
  requestAnimationFrame(() => modal.classList.add("open"));
  modal.querySelectorAll("[data-plan-pay]").forEach((b) =>
    b.addEventListener("click", () => {
      if (!isLoggedIn) { window.location.href = "/login?mode=signup"; return; }
      closePlanModal();
      const msg = t(b.dataset.planPay === "pro" ? "planChatPro" : "planChatMax");
      if (window.GWChat) GWChat.openWith(msg);
    }),
  );
}
function closePlanModal() {
  const modal = document.querySelector("[data-plan-modal]");
  if (!modal) return;
  modal.classList.remove("open");
  setTimeout(() => (modal.hidden = true), 250);
}
window.openPlanModal = openPlanModal;

function renderNavAuth() {
  const box = document.querySelector("[data-nav-auth]");
  if (!box) return;

  if (!isLoggedIn) {
    box.innerHTML = `
      <a class="btn-ghost" href="/login#login">${t("login")}</a>
      <a class="btn-primary" href="/login#signup">${t("signup")}</a>`;
    return;
  }

  const av = currentUser.avatar
    ? `<img src="${currentUser.avatar}" alt="" />`
    : `<i>${(currentUser.firstName || currentUser.name || "?").trim()[0].toUpperCase()}</i>`;

  box.innerHTML = `
    <div class="user-menu" data-user-menu>
      <button class="user-btn" type="button">
        <span class="avatar-round sm">${av}</span>
        <em>${currentUser.firstName || currentUser.name}</em>
        ${currentUser.plan !== "free" ? `<span class="plan-badge ${currentUser.plan}">${planLabel(currentUser.plan)}</span>` : ""}
        <b>▾</b>
      </button>
      <div class="menu glass">
        <a href="/profile">👤 ${t("navProfile")}</a>
        <a href="/archive">🗂 ${t("navArchive")}</a>
        <a href="/rating">🏆 ${t("navRating")}</a>
        <button type="button" data-plan-open>💎 ${currentUser.plan === "free" ? t("planUpgrade") : `${planLabel(currentUser.plan)} · ${(currentUser.planUntil || "").slice(0, 10)}`}</button>
        ${currentUser.isAdmin ? `<a href="/admin" class="admin-link">🛡 ${t("navAdmin")}</a>` : ""}
        <button type="button" data-logout>⎋ ${t("navLogout")}</button>
      </div>
    </div>`;

  const menu = box.querySelector("[data-user-menu]");
  menu.querySelector(".user-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    menu.classList.toggle("open");
  });
  document.addEventListener("click", () => menu.classList.remove("open"));
  menu.querySelector("[data-plan-open]").addEventListener("click", () => { menu.classList.remove("open"); openPlanModal(); });
  menu.querySelector("[data-logout]").addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/";
  });
}

/* ---------- ADMIN BILAN BOG'LANISH (dropdown) ---------- */
function initContactMenu() {
  const menu = document.querySelector("[data-contact-menu]");
  if (!menu || menu.dataset.bound) return;
  menu.dataset.bound = "1";
  const btn = menu.querySelector(".contact-btn");
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = menu.classList.toggle("open");
    btn.setAttribute("aria-expanded", open);
  });
  document.addEventListener("click", () => menu.classList.remove("open"));
  menu.querySelector(".contact-pop").addEventListener("click", (e) => e.stopPropagation());
  menu.querySelectorAll("[data-copy]").forEach((c) =>
    c.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      try {
        await navigator.clipboard.writeText(c.dataset.copy);
        const old = c.textContent;
        c.textContent = "✓";
        c.classList.add("ok");
        setTimeout(() => { c.textContent = old; c.classList.remove("ok"); }, 1400);
      } catch {}
    }),
  );
  menu.querySelector("[data-open-chat]").addEventListener("click", () => menu.classList.remove("open"));
}

/* ---------- HAMMASI ---------- */
async function renderAll() {
  renderText();
  renderMarquee();
  renderBenefits();
  renderFooterSources();
  renderFilters();
  renderStory();
  renderSlogan();
  initJobsControls();
  initReveal();
  renderNavAuth();
  initContactMenu();
  if (window.GWChat) GWChat.refresh();
  renderJobs();
}

/* ---------- MOBIL MENYU ("☰") va aylantirilganda menyu foni ---------- */
function initMobileNav() {
  const outer = document.querySelector(".nav-outer");
  const nav = document.querySelector(".nav");
  const btn = document.querySelector("[data-nav-toggle]");
  if (outer) {
    const onScroll = () => outer.classList.toggle("scrolled", window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }
  if (!nav || !btn) return;
  const setOpen = (v) => {
    nav.classList.toggle("open", v);
    btn.setAttribute("aria-expanded", String(v));
  };
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    setOpen(!nav.classList.contains("open"));
  });
  // sahifaga o'tganda yoki chat ochilganda menyu yopiladi
  nav.addEventListener("click", (e) => {
    if (e.target.closest(".nav-links a, [data-open-chat], .user-menu .menu a")) setOpen(false);
  });
  document.addEventListener("click", (e) => { if (!nav.contains(e.target)) setOpen(false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });
  window.matchMedia("(min-width: 901px)").addEventListener("change", (m) => { if (m.matches) setOpen(false); });
}

document.addEventListener("DOMContentLoaded", async () => {
  initMobileNav();
  initTheme();
  initIntro();
  initLang();
  await initCurrency();
  await checkAuthState();
  await renderAll();
});