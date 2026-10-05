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
