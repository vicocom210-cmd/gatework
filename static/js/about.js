/* =====================================================================
   "BIZ HAQIMIZDA" — suv to'lish yuklagichi
   UZ: Gate Work belgisi ichidagi suv sahifaning HAQIQIY yuklanishiga
       qarab ko'tariladi: hikoya rasmlari, logotiplar va serif shrift
       oldindan yuklab, dekodlab olinadi. Shunda keyingi animatsiyalar
       qotib qolmaydi. Suv kamida MIN_MS davomida to'ladi (animatsiya
       ko'rinishi uchun), internet juda sekin bo'lsa MAX_MS dan keyin
       baribir ochiladi.
   EN: The water inside the Gate Work mark rises with the page's REAL
       loading: story photos, logos and the serif font are preloaded and
       decoded first, so the following animations don't stutter. It takes
       at least MIN_MS (so the fill is visible) and opens after MAX_MS
       even on a very slow connection.
   ===================================================================== */
(function () {
  const loader = document.querySelector("[data-about-loader]");
  if (!loader) return;

  const water = loader.querySelector("[data-water]");
  const pctEl = loader.querySelector("[data-percent]");
  const motion = typeof window.motionEnabled === "function" ? window.motionEnabled() : true;
  const MIN_MS = motion ? 2600 : 250;
  const MAX_MS = 8000;

  document.body.classList.add("aw-lock");
  if (!location.hash) {
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";
    window.scrollTo(0, 0);
  }

  /* ---------- yuklanadigan narsalar ---------- */
  const urls = new Set();
  if (typeof STORY !== "undefined") STORY.forEach((s) => s.img && urls.add(s.img));
  document.querySelectorAll("img[data-white]").forEach((img) => {
    urls.add(img.dataset.white);
    urls.add(img.dataset.black);
  });

  const tasks = [...urls].map((src) => {
    const img = new Image();
    img.decoding = "async";
    img.src = src;
    // decode() rasm yuklanib, chizishga tayyor bo'lganda tugaydi; xato bo'lsa ham davom etamiz
    return img.decode ? img.decode().catch(() => {}) : new Promise((r) => { img.onload = img.onerror = r; });
  });
  if (document.fonts && document.fonts.load) {
    tasks.push(document.fonts.load('400 1em "Instrument Serif"').catch(() => {}));
  }

  let loaded = 0;
  const total = tasks.length || 1;
  tasks.forEach((p) => p.then(() => { loaded += 1; }));

  /* ---------- suv sathi ---------- */
  let shown = 0;
  let finished = false;
  const start = performance.now();

  function render(level) {
    const pct = Math.round(level * 100);
    water.style.setProperty("--level", level.toFixed(4));
    pctEl.textContent = pct;
    loader.setAttribute("aria-valuenow", pct);
  }

  function frame(now) {
    const elapsed = now - start;
    const real = tasks.length ? loaded / total : 1;
    // suv haqiqiy yuklanishdan ham, minimal vaqtdan ham oldinga o'tmaydi
    let target = Math.min(real, elapsed / MIN_MS, 1);
    if (elapsed > MAX_MS) target = 1;

    if (shown < target) shown = Math.min(target, shown + Math.max((target - shown) * 0.09, 0.0025));
    render(shown);

    if (shown >= 1) finish();
    else tick();
  }

  // UZ: yashirin tabda requestAnimationFrame to'xtaydi — shunda taymer bilan davom etamiz.
  // EN: requestAnimationFrame pauses in hidden tabs — fall back to a timer there.
  function tick() {
    if (document.hidden) setTimeout(() => frame(performance.now()), 120);
    else requestAnimationFrame(frame);
  }

  function finish() {
    if (finished) return;
    finished = true;
    render(1);
    // kichik pauza — "100%" ko'rinib qolsin
    setTimeout(() => {
      loader.classList.add("done");
      document.body.classList.add("aw-ready");
      setTimeout(() => {
        loader.remove();
        document.body.classList.remove("aw-lock");
      }, motion ? 1500 : 50);
    }, motion ? 320 : 0);
  }

  tick();
  // qat'iy zaxira: nima bo'lsa ham sahifa ochiladi
  setTimeout(finish, MAX_MS + 1500);
})();

/* =====================================================================
   SAYOHAT — aylantirish = kamera harakati
   UZ: .aw-stage ekranda qotib turadi (sticky). Aylantirish foizi (0..1)
       vaqt chizig'iga aylanadi: har bir sahna o'z "markazi"ga ega; kamera
       unga yaqinlashganda sahna uzoqdan (translateZ manfiy) uchib keladi,
       markazda to'xtaydi, keyin kamera yonidan o'tib ketadi. Harakat
       silliq bo'lishi uchun joriy holat maqsadga asta yaqinlashadi (lerp).
   EN: .aw-stage stays on screen (sticky). Scroll progress (0..1) becomes a
       timeline: each scene has a "centre"; as the camera nears it the scene
       flies in from afar (negative translateZ), rests in the middle, then
       passes the camera. The current value eases toward the target (lerp)
       for smooth motion.
   ===================================================================== */
(function () {
  const journey = document.querySelector("[data-journey]");
  if (!journey) return;
  const stage = journey.querySelector("[data-stage]");
  const cardsBox = stage.querySelector("[data-story]");
  const open = stage.querySelector('[data-scene="open"]');
  const facts = stage.querySelector('[data-scene="facts"]');
  const final = stage.querySelector('[data-scene="final"]');
  const bar = stage.querySelector("[data-progress]");
  const rail = stage.querySelector("[data-rail]");

  const motion = typeof window.motionEnabled === "function" ? window.motionEnabled() : true;
  if (!motion) {
    journey.classList.add("static");
    return;
  }

  /* ---------- vaqt chizig'i (0..1) ---------- */
  const OPEN_END = 0.12;              // ochilish shu yergacha uchib o'tadi
  const CARD0 = 0.25, STEP = 0.145;   // kartochkalar markazlari: .25 .395 .54 .685
  const PERSP = "perspective(1000px)"; // har bir element o'z perspektivasi bilan — z-index bo'yicha saralanadi
  const FACTS = 0.83, FINAL = 0.985;  // yakun raqamlar o'tib ketgach chiqadi
  const SPAN = 0.15;                  // bitta sahnaning "kenglik"i

  /* ---------- zarrachalar ---------- */
  const starsBox = stage.querySelector("[data-stars]");
  const stars = [];
  const count = window.innerWidth < 700 ? 22 : 44;
  for (let i = 0; i < count; i++) {
    const el = document.createElement("i");
    el.style.setProperty("--s", (3 + Math.random() * 7).toFixed(1) + "px");
    starsBox.appendChild(el);
    // markazdan uzoqroq joylashsin — matn ustiga tushmasin
    const a = Math.random() * Math.PI * 2;
    const r = 0.35 + Math.random() * 0.65;
    stars.push({ el, x: Math.cos(a) * r * 60, y: Math.sin(a) * r * 55, z: Math.random() });
  }

  /* ---------- yordamchilar ---------- */
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  // d < 0 — sahna hali uzoqda; d = 0 — markazda; d > 0 — kamera yonidan o'tib ketdi
  function place(el, d, side, stay) {
    if (stay && d > 0) d = 0;
    let vis;
    if (d < -1.35 || d > 0.8) vis = 0;
    else if (d < -0.9) vis = (d + 1.35) / 0.45;
    else if (d > 0.35) vis = 1 - (d - 0.35) / 0.45;
    else vis = 1;

    if (vis <= 0.001) {
      if (el.style.visibility !== "hidden") {
        el.style.visibility = "hidden";
        el.style.opacity = "0";
      }
      return;
    }
    const narrow = window.innerWidth < 700;
    const z = d * (narrow ? 900 : 1150);
    const x = side * -d * (narrow ? 14 : 30);       // vw — uzoqda yon tomonda, markazda o'rtada
    const ry = side * d * (narrow ? 10 : 22);       // biroz burilib uchadi
    el.style.visibility = "visible";
    el.style.opacity = vis.toFixed(3);
    el.style.transform = `translate(-50%, -50%) ${PERSP} translate3d(${x.toFixed(2)}vw, 0, ${z.toFixed(1)}px) rotateY(${ry.toFixed(2)}deg)`;
    el.style.zIndex = String(2000 + Math.round(z));   // yaqinroq sahna ustida chiziladi
    el.style.pointerEvents = Math.abs(d) < 0.3 ? "auto" : "none";
  }

  /* ---------- bosqichlar ro'yxati ---------- */
  let railLang = null;
  function buildRail() {
    if (typeof STORY === "undefined" || typeof tl !== "function") return;
    const cur = typeof lang !== "undefined" ? lang : "uz";
    if (cur === railLang && rail.children.length) return;
    railLang = cur;
    rail.innerHTML = STORY.map(
      (s, i) => `<button type="button" data-go="${CARD0 + i * STEP}"><i></i><b>${s.step}</b><span>${tl(s.title)}</span></button>`,
    ).join("");
    rail.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => goTo(Number(b.dataset.go))));
  }

  function goTo(p) {
    const top = journey.getBoundingClientRect().top + window.scrollY;
    const total = journey.offsetHeight - window.innerHeight;
    window.scrollTo({ top: top + p * total, behavior: "smooth" });
  }
  const next = stage.querySelector("[data-journey-next]");
  if (next) next.addEventListener("click", () => goTo(CARD0));

  /* ---------- raqamlar sanog'i ---------- */
  let counted = false;
  function countUp() {
    if (counted) return;
    counted = true;
    facts.querySelectorAll("[data-goal]").forEach((b) => {
      const to = Number(b.dataset.goal);
      const t0 = performance.now();
      (function step(now) {
        const k = Math.min((now - t0) / 1100, 1);
        b.textContent = Math.round(to * (1 - Math.pow(1 - k, 3)));
        if (k < 1) requestAnimationFrame(step);
      })(t0);
    });
  }

  /* ---------- aylantirish → maqsad ---------- */
  let target = 0;
  let cur = 0;
  let dirty = true;
  function readScroll() {
    const r = journey.getBoundingClientRect();
    const total = journey.offsetHeight - window.innerHeight;
    target = clamp(-r.top / total, 0, 1);
  }
  window.addEventListener("scroll", readScroll, { passive: true });
  window.addEventListener("resize", () => { readScroll(); dirty = true; });
  // til almashsa app.js kartochkalarni qayta chizadi — darhol joylashtiramiz
  new MutationObserver(() => { dirty = true; }).observe(cardsBox, { childList: true });
  readScroll();
  cur = target;

  function render(p) {
    // ochilish: kamera logotip ichidan uchib o'tadi
    place(open, (p / OPEN_END) * 0.8, 0, false);

    const cards = cardsBox.querySelectorAll(".story");
    let active = -1;
    cards.forEach((card, i) => {
      const d = (p - (CARD0 + i * STEP)) / SPAN;
      place(card, d, i % 2 ? 1 : -1, false);
      if (Math.abs(d) < 0.5) active = i;
    });

    const df = (p - FACTS) / 0.11;
    place(facts, df, 0, false);
    if (df > -0.4) countUp();

    place(final, (p - FINAL) / 0.08, 0, true);

    // zarrachalar kameraga qarab uchadi (aylantirishga bog'liq)
    for (const s of stars) {
      const k = (s.z + p * 4) % 1;                   // 0 — uzoqda, 1 — kamera yonida
      const z = -1600 + k * 1550;
      const o = k < 0.15 ? k / 0.15 : k > 0.85 ? (1 - k) / 0.15 : 1;
      s.el.style.opacity = (o * 0.9).toFixed(3);
      s.el.style.transform = `${PERSP} translate3d(${s.x}vw, ${s.y}vh, ${z.toFixed(0)}px)`;
    }

    bar.style.transform = `scaleY(${p.toFixed(4)})`;
    buildRail();
    rail.querySelectorAll("button").forEach((b, i) => b.classList.toggle("active", i === active));
  }

  function frame() {
    const diff = target - cur;
    if (Math.abs(diff) > 0.00005 || dirty) {
      // yashirin tabda silliqlash shart emas — darhol joyiga qo'yamiz
      cur = Math.abs(diff) < 0.0005 || document.hidden ? target : cur + diff * 0.1;
      render(cur);
      dirty = false;
    }
    if (document.hidden) setTimeout(frame, 200);
    else requestAnimationFrame(frame);
  }
  frame();
})();
