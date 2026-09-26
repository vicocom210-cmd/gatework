/* ===== GATE WORK — "Biz haqimizda": yuksalish sahnasi =====
   Sahifa pastga aylantirilganda kamera tog' etagidan ko'tariladi:
     tun → tong → tuman ichidagi qorli tog' → bulutlar ichi → bo'ronli
     bulutlar → bulutlardan tepaga → Yer shari (Toshkentdan Yevropaga yo'llar).
   Hamma narsa kod bilan chiziladi (tashqi rasm yo'q):
     - tog'lar: SVG (tasodifiy, lekin har safar bir xil — "seed" bilan)
     - bulutlar: <canvas> (bir marta chiziladi, keyin faqat CSS transform)
     - Yer shari: <canvas> + globe-dots.js (quruqlik nuqtalari)
   Tezlik uchun: har kadrda faqat transform/opacity o'zgaradi, Yer shari
   faqat ko'rinib turganda chiziladi. */
(function () {
  const root = document.querySelector("[data-ascent]");
  if (!root) return;

  /* ---------- Matnlar (mavjud STORY tarjimalaridan) ---------- */
  // MUHIM: data.js'da "const" bilan e'lon qilingan — window.STORY orqali ko'rinmaydi
  if (typeof STORY !== "undefined" && typeof STRINGS !== "undefined") {
    STORY.forEach((s, i) => {
      STRINGS[`ascent${i + 1}t`] = s.title;
      STRINGS[`ascent${i + 1}d`] = s.text;
    });
  }

  const stage = root.querySelector(".ascent-stage");
  const svg = root.querySelector("[data-mountains]");
  const globeCanvas = root.querySelector("[data-globe]");
  const starsCanvas = root.querySelector("[data-stars]");
  const bar = root.querySelector("[data-ascent-bar]");
  const layer = (name) => root.querySelector(`[data-layer="${name}"]`);
  const L = { dawn: layer("dawn"), mist: layer("mist"), storm: layer("storm"), space: layer("space"), sun: layer("sun"), fog: layer("fog") };
  const scenes = [...root.querySelectorAll("[data-scene]")];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- Yordamchi funksiyalar ---------- */
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const ramp = (p, a, b) => clamp((p - a) / (b - a));
  const smooth = (t) => t * t * (3 - 2 * t);
  const band = (p, a, b, c, d) => smooth(ramp(p, a, b)) * (1 - smooth(ramp(p, c, d)));
  const lerp = (a, b, t) => a + (b - a) * t;

  function rng(seed) {
    // mulberry32 — har safar bir xil "tasodifiy" tog'lar
    return function () {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* ================= TOG'LAR (SVG) ================= */
  const NS = "http://www.w3.org/2000/svg";

  // Tizma chizig'i: o'rtadagi nuqtani siljitish (midpoint displacement) usuli
  function ridge(rand, x0, x1, yLeft, yRight, rough, depth) {
    let pts = [[x0, yLeft], [x1, yRight]];
    let amp = rough;
    for (let d = 0; d < depth; d++) {
      const next = [pts[0]];
      for (let i = 0; i < pts.length - 1; i++) {
        const [ax, ay] = pts[i], [bx, by] = pts[i + 1];
        next.push([(ax + bx) / 2, (ay + by) / 2 + (rand() - 0.5) * amp], pts[i + 1]);
      }
      pts = next;
      amp *= 0.55;
    }
    return pts;
  }
  const toPath = (pts, bottom = 900) =>
    `M${pts[0][0]},${bottom} ` + pts.map(([x, y]) => `L${x.toFixed(1)},${y.toFixed(1)}`).join(" ") + ` L${pts[pts.length - 1][0]},${bottom} Z`;

  // Asosiy cho'qqi: tik yonbag'irlar + notekis qirralar
  function peak(rand, cx, top, halfW, base) {
    const left = ridge(rand, cx - halfW, cx, base, top, 70, 6).map(([x, y]) => {
      const t = (x - (cx - halfW)) / halfW; // 0..1 — cho'qqiga yaqinlashish
      return [x, lerp(base, top, Math.pow(t, 1.6)) + (y - lerp(base, top, t)) * 0.6];
    });
    const right = ridge(rand, cx, cx + halfW, top, base + 20, 70, 6).map(([x, y]) => {
      const t = 1 - (x - cx) / halfW;
      return [x, lerp(base + 20, top, Math.pow(t, 1.8)) + (y - lerp(base + 20, top, t)) * 0.6];
    });
    return left.concat(right.slice(1));
  }

  // Qor qoplami: cho'qqi siluetidan qor chizig'igacha bo'lgan qism, pastki cheti tishli
  function snowCap(pts, snowLine, rand) {
    const top = pts.filter(([, y]) => y < snowLine);
    if (top.length < 3) return "";
    const first = top[0], last = top[top.length - 1];
    let d = `M${first[0].toFixed(1)},${first[1].toFixed(1)} ` + top.map(([x, y]) => `L${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
    const steps = 14;
    for (let i = 1; i < steps; i++) {
      const x = lerp(last[0], first[0], i / steps);
      const y = snowLine - 10 + (rand() - 0.25) * 60 - Math.sin((i / steps) * Math.PI) * 20;
      d += ` L${x.toFixed(1)},${y.toFixed(1)}`;
    }
    return d + " Z";
  }

  function el(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function buildMountains() {
    const rand = rng(20260926);
    const defs = el("defs", {}, svg);
    const grad = (id, stops, y2 = 1) => {
      const g = el("linearGradient", { id, x1: 0, y1: 0, x2: 0, y2 }, defs);
      stops.forEach(([o, c, a = 1]) => el("stop", { offset: o, "stop-color": c, "stop-opacity": a }, g));
    };
    // tun ranglari (tong yorug'i bilan) va kun ranglari (tumanli qorli tog')
    grad("gw-peak-n", [[0, "#e7a77e"], [0.35, "#4b3a58"], [1, "#16213a"]]);
    grad("gw-peak-d", [[0, "#fdfdfe"], [0.3, "#b9c3cf"], [1, "#7e8c9c"]]);
    grad("gw-shade-n", [[0, "#2a2442"], [1, "#0f1830"]]);
    grad("gw-shade-d", [[0, "#9aa7b6"], [1, "#6e7c8d"]]);
    grad("gw-snow-n", [[0, "#ffe2c6"], [1, "#d49a86"]]);
    grad("gw-snow-d", [[0, "#ffffff"], [1, "#e3e9ef"]]);
    grad("gw-mist", [[0, "#eef2f5", 0], [0.6, "#eef2f5", 0.75], [1, "#eef2f5", 1]]);
    grad("gw-mist-n", [[0, "#243452", 0], [1, "#243452", 0.85]]);

    const layers = [];
    const mk = (depth) => {
      const g = el("g", { "data-depth": depth }, svg);
      layers.push(g);
      return g;
    };

    // 0 — uzoqdagi tizma
    const far = ridge(rand, -200, 1800, 560, 590, 160, 8);
    const g0 = mk(0);
    el("path", { d: toPath(far), fill: "#1b2944" }, g0);
    el("path", { d: toPath(far), fill: "#c3ccd6", class: "day" }, g0);
    el("rect", { x: -200, y: 520, width: 2000, height: 380, fill: "url(#gw-mist-n)" }, g0);
    el("rect", { x: -200, y: 520, width: 2000, height: 380, fill: "url(#gw-mist)", class: "day" }, g0);

    // 1 — asosiy cho'qqi (qorli)
    const main = peak(rand, 800, 150, 520, 760);
    const g1 = mk(1);
    el("path", { d: toPath(main), fill: "url(#gw-peak-n)" }, g1);
    el("path", { d: toPath(main), fill: "url(#gw-peak-d)", class: "day" }, g1);
    // soyali (o'ng) yonbag'ir
    const apex = main.reduce((a, b) => (b[1] < a[1] ? b : a));
    const rightSide = main.filter(([x]) => x >= apex[0]);
    const shade = `M${apex[0]},${apex[1]} ` + rightSide.map(([x, y]) => `L${x.toFixed(1)},${y.toFixed(1)}`).join(" ") +
      ` L${apex[0] + 120},900 L${apex[0] + 40},520 Z`;
    el("path", { d: shade, fill: "url(#gw-shade-n)", opacity: 0.85 }, g1);
    el("path", { d: shade, fill: "url(#gw-shade-d)", opacity: 0.8, class: "day" }, g1);
    const snow = snowCap(main, 330, rand);
    el("path", { d: snow, fill: "url(#gw-snow-n)" }, g1);
    el("path", { d: snow, fill: "url(#gw-snow-d)", class: "day" }, g1);
    el("rect", { x: -200, y: 600, width: 2000, height: 300, fill: "url(#gw-mist-n)" }, g1);
    el("rect", { x: -200, y: 560, width: 2000, height: 340, fill: "url(#gw-mist)", class: "day" }, g1);

    // 2 — o'rta tizmalar (chap va o'ng yelkalar)
    const midL = peak(rand, 250, 430, 420, 800);
    const midR = peak(rand, 1360, 400, 460, 800);
    const g2 = mk(2);
    [midL, midR].forEach((pts) => {
      el("path", { d: toPath(pts), fill: "#131d33" }, g2);
      el("path", { d: toPath(pts), fill: "#8896a6", class: "day" }, g2);
      const c = snowCap(pts, 500, rand);
      el("path", { d: c, fill: "#b98a86", opacity: 0.6 }, g2);
      el("path", { d: c, fill: "#f4f7fa", class: "day" }, g2);
    });
    el("rect", { x: -200, y: 680, width: 2000, height: 220, fill: "url(#gw-mist-n)" }, g2);
    el("rect", { x: -200, y: 650, width: 2000, height: 250, fill: "url(#gw-mist)", class: "day" }, g2);

    // 3 — eng yaqin tepaliklar
    const near = ridge(rand, -200, 1800, 800, 780, 140, 8);
    const g3 = mk(3);
    el("path", { d: toPath(near), fill: "#0a1222" }, g3);
    el("path", { d: toPath(near), fill: "#6f7d8d", class: "day" }, g3);
    return layers;
  }

  /* ================= BULUTLAR (canvas) ================= */
  function cloudSprite(w, h, seed, dark) {
    const rand = rng(seed);
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    const ctx = c.getContext("2d");
    const puffs = dark ? 44 : 26;
    for (let i = 0; i < puffs; i++) {
      // puflar ellips ichida, pastki qismi tekisroq
      const a = rand() * Math.PI * 2;
      const rr = Math.sqrt(rand());
      const x = w / 2 + Math.cos(a) * rr * w * 0.34;
      const y = h * 0.58 + Math.sin(a) * rr * h * 0.22 - rand() * h * 0.12;
      const r = (dark ? 0.16 + rand() * 0.18 : 0.12 + rand() * 0.16) * w * (1 - rr * 0.4);
      const g = ctx.createRadialGradient(x, y - r * 0.25, r * 0.1, x, y, r);
      if (dark) {
        g.addColorStop(0, "rgba(118,130,146,0.32)");
        g.addColorStop(0.6, "rgba(72,84,100,0.2)");
        g.addColorStop(1, "rgba(40,50,64,0)");
      } else {
        g.addColorStop(0, "rgba(255,255,255,0.9)");
        g.addColorStop(0.5, "rgba(240,244,247,0.55)");
        g.addColorStop(1, "rgba(220,228,235,0)");
      }
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
    return c;
  }

  // [chap %, tepa %, kenglik vw, chuqurlik 0..2]
  const CLOUD_LAYOUT = [
    [-10, 42, 60, 0], [48, 38, 58, 0], [18, 58, 70, 0],
    [-18, 62, 64, 1], [58, 56, 66, 1], [22, 30, 52, 1],
    [-6, 74, 80, 2], [44, 70, 84, 2], [70, 20, 48, 2],
  ];
  function buildClouds(box, dark) {
    const depths = [0, 1, 2].map(() => {
      const d = document.createElement("div");
      d.className = "as-cloud-depth";
      box.appendChild(d);
      return d;
    });
    CLOUD_LAYOUT.forEach(([x, y, w, depth], i) => {
      const wrap = document.createElement("div");
      wrap.className = "as-cloud";
      wrap.style.left = x + "%";
      wrap.style.top = y + "%";
      wrap.style.width = w + "vw";
      wrap.style.marginTop = -w * 0.25 + "vw";
      wrap.style.setProperty("--dur", 40 + ((i * 7) % 30) + "s");
      wrap.style.setProperty("--dx", 2 + depth * 2 + "vw");
      wrap.style.animationDelay = -i * 5 + "s";
      wrap.appendChild(cloudSprite(640, 320, 100 + i * 17 + (dark ? 999 : 0), dark));
      depths[depth].appendChild(wrap);
    });
    return depths;
  }

  /* ================= YULDUZLAR ================= */
  function drawStars() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = starsCanvas.clientWidth, h = starsCanvas.clientHeight;
    starsCanvas.width = w * dpr;
    starsCanvas.height = h * dpr;
    const ctx = starsCanvas.getContext("2d");
    ctx.scale(dpr, dpr);
    const rand = rng(7);
    const n = Math.round((w * h) / 5000);
    for (let i = 0; i < n; i++) {
      const r = rand() * 1.1 + 0.2;
      ctx.fillStyle = `rgba(220,235,255,${0.25 + rand() * 0.65})`;
      ctx.beginPath();
      ctx.arc(rand() * w, rand() * h * 0.85, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  /* ================= YER SHARI ================= */
  const RAD = Math.PI / 180;
  const DOTS = window.GW_GLOBE_DOTS || [];
  // label: nom qaysi tomonda yoziladi (yaqin shaharlar nomi ustma-ust tushmasligi uchun faqat ba'zilari)
  const HOME = { lat: 41.31, lon: 69.24, key: "cityTashkent", label: "right" };
  const DESTS = [
    { lat: 52.52, lon: 13.4, key: "cityBerlin", label: "left" },
    { lat: 59.33, lon: 18.07, key: "cityStockholm", label: "up" },
    { lat: 52.23, lon: 21.01, key: "cityWarsaw" },
    { lat: 51.51, lon: -0.13, key: "cityLondon", label: "left" },
    { lat: 52.37, lon: 4.9, key: "cityAmsterdam" },
  ];
  const gctx = globeCanvas.getContext("2d");
  let gSize = 0, gDpr = 1;

  function sizeGlobe() {
    gDpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = stage.clientWidth, h = stage.clientHeight;
    const portrait = h > w;
    gSize = Math.round(portrait ? Math.min(w * 1.05, h * 0.62) : Math.min(h * 0.86, w * 0.6));
    globeCanvas.width = gSize * gDpr;
    globeCanvas.height = gSize * gDpr;
    globeCanvas.style.width = gSize + "px";
    globeCanvas.style.height = gSize + "px";
    globeCanvas.style.marginLeft = -gSize / 2 + "px";
    globeCanvas.style.marginTop = -gSize / 2 + (portrait ? h * 0.16 : 0) + "px";
    if (!portrait) globeCanvas.style.marginLeft = -gSize / 2 + w * 0.17 + "px"; // matn chapda, shar o'ngroqda
  }

  // Ortografik proyeksiya: [x, y, ko'rinish (cos c)]
  function project(lat, lon, lon0, lat0, R, lift = 0) {
    const phi = lat * RAD, lam = (lon - lon0) * RAD, phi0 = lat0 * RAD;
    const cosc = Math.sin(phi0) * Math.sin(phi) + Math.cos(phi0) * Math.cos(phi) * Math.cos(lam);
    const r = R * (1 + lift);
    return [r * Math.cos(phi) * Math.sin(lam), -r * (Math.cos(phi0) * Math.sin(phi) - Math.sin(phi0) * Math.cos(phi) * Math.cos(lam)), cosc];
  }

  // Ikki nuqta orasidagi katta aylana yoyi (slerp)
  function arcPoints(a, b, n) {
    const toV = (p) => [Math.cos(p.lat * RAD) * Math.cos(p.lon * RAD), Math.cos(p.lat * RAD) * Math.sin(p.lon * RAD), Math.sin(p.lat * RAD)];
    const va = toV(a), vb = toV(b);
    const w = Math.acos(clamp(va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2], -1, 1));
    const out = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      const s1 = Math.sin((1 - t) * w) / Math.sin(w), s2 = Math.sin(t * w) / Math.sin(w);
      const v = [s1 * va[0] + s2 * vb[0], s1 * va[1] + s2 * vb[1], s1 * va[2] + s2 * vb[2]];
      out.push({ lat: Math.asin(v[2]) / RAD, lon: Math.atan2(v[1], v[0]) / RAD, lift: Math.sin(t * Math.PI) * 0.16 * (w / 0.8) });
    }
    return out;
  }
  const ARCS = DESTS.map((d) => arcPoints(HOME, d, 48));

  function drawGlobe(p, time) {
    const S = gSize * gDpr;
    const ctx = gctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, S, S);
    const R = S * 0.4, cx = S / 2, cy = S / 2;
    const k = ramp(p, 0.8, 1);
    const sway = reduceMotion ? 0 : Math.sin(time / 4000) * 3;
    const lon0 = lerp(-20, 42, smooth(k)) + sway;
    const lat0 = lerp(20, 38, smooth(k));

    // atmosfera nuri
    const halo = ctx.createRadialGradient(cx, cy, R * 0.9, cx, cy, R * 1.25);
    halo.addColorStop(0, "rgba(64,224,208,0.28)");
    halo.addColorStop(1, "rgba(64,224,208,0)");
    ctx.fillStyle = halo;
    ctx.beginPath();
    ctx.arc(cx, cy, R * 1.25, 0, Math.PI * 2);
    ctx.fill();
    // shar tanasi
    const body = ctx.createRadialGradient(cx - R * 0.35, cy - R * 0.4, R * 0.1, cx, cy, R);
    body.addColorStop(0, "#15395a");
    body.addColorStop(0.7, "#0a1f36");
    body.addColorStop(1, "#061425");
    ctx.fillStyle = body;
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.fill();

    // quruqlik nuqtalari
    const dotR = Math.max(1, R / 230);
    for (let i = 0; i < DOTS.length; i += 3) {
      const [x, y, c] = project(DOTS[i] / 10, DOTS[i + 1] / 10, lon0, lat0, R);
      if (c <= 0) continue;
      const flag = DOTS[i + 2];
      const a = 0.25 + c * 0.75;
      ctx.fillStyle = flag === 1 ? `rgba(255,190,120,${a})` : flag === 2 ? `rgba(94,234,212,${a})` : `rgba(170,205,225,${a * 0.55})`;
      ctx.beginPath();
      ctx.arc(cx + x, cy + y, flag ? dotR * 1.5 : dotR, 0, Math.PI * 2);
      ctx.fill();
    }

    // Toshkentdan yo'llar — aylantirishga qarab birin-ketin chiziladi
    ctx.lineWidth = Math.max(1.5, R / 160);
    ctx.lineCap = "round";
    ARCS.forEach((arc, ai) => {
      const prog = ramp(p, 0.86 + ai * 0.018, 0.94 + ai * 0.018);
      if (prog <= 0) return;
      const n = Math.max(1, Math.floor(prog * (arc.length - 1)));
      ctx.strokeStyle = "rgba(94,234,212,0.9)";
      ctx.beginPath();
      let started = false, head = null;
      for (let i = 0; i <= n; i++) {
        const q = arc[i];
        const [x, y, c] = project(q.lat, q.lon, lon0, lat0, R, q.lift);
        if (c < -0.05) { started = false; continue; }
        if (!started) { ctx.moveTo(cx + x, cy + y); started = true; } else ctx.lineTo(cx + x, cy + y);
        head = [cx + x, cy + y];
      }
      ctx.stroke();
      if (head && prog < 1) {
        ctx.fillStyle = "#e6fffb";
        ctx.beginPath();
        ctx.arc(head[0], head[1], ctx.lineWidth * 1.6, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    // shaharlar va nomlari
    const fontPx = Math.round(Math.max(12 * gDpr, R / 20)); // retina ekranda ham o'qiladigan o'lcham
    ctx.font = `600 ${fontPx}px "DM Sans", system-ui, sans-serif`;
    [HOME, ...DESTS].forEach((city, i) => {
      const [x, y, c] = project(city.lat, city.lon, lon0, lat0, R);
      if (c <= 0.05) return;
      const shown = i === 0 ? ramp(p, 0.84, 0.88) : ramp(p, 0.92 + (i - 1) * 0.018, 0.95 + (i - 1) * 0.018);
      if (shown <= 0) return;
      ctx.globalAlpha = shown;
      ctx.fillStyle = i === 0 ? "#ffbe78" : "#5eead4";
      ctx.beginPath();
      ctx.arc(cx + x, cy + y, dotR * 3.2, 0, Math.PI * 2);
      ctx.fill();
      if (city.label) {
        ctx.fillStyle = "rgba(240,248,250,0.92)";
        const label = typeof t === "function" ? t(city.key) : city.key;
        const dx = city.label === "left" ? -ctx.measureText(label).width - dotR * 5 : dotR * 5;
        const dy = city.label === "up" ? -dotR * 5 : dotR * 1.5;
        ctx.fillText(label, cx + x + dx, cy + y + dy);
      }
      ctx.globalAlpha = 1;
    });
  }

  /* ================= ASOSIY TSIKL ================= */
  const mLayers = buildMountains();
  const lightDepths = buildClouds(root.querySelector('[data-clouds="light"]'), false);
  const darkDepths = buildClouds(root.querySelector('[data-clouds="dark"]'), true);
  const lightBox = root.querySelector('[data-clouds="light"]');
  const darkBox = root.querySelector('[data-clouds="dark"]');

  let progress = 0, ticking = false, globeLoop = false;

  function readProgress() {
    const r = root.getBoundingClientRect();
    const total = root.offsetHeight - window.innerHeight;
    return clamp(-r.top / Math.max(1, total));
  }

  function setScene(elm, vis, dy) {
    elm.style.opacity = vis.toFixed(3);
    elm.style.visibility = vis > 0.01 ? "visible" : "hidden";
    elm.style.transform = `translate(var(--bx), calc(var(--base) + ${dy.toFixed(1)}px))`;
  }

  function update() {
    ticking = false;
    const p = (progress = readProgress());

    // osmon
    L.dawn.style.opacity = band(p, 0.03, 0.14, 0.26, 0.36).toFixed(3);
    L.mist.style.opacity = band(p, 0.2, 0.32, 0.6, 0.68).toFixed(3);
    L.storm.style.opacity = band(p, 0.58, 0.66, 0.8, 0.88).toFixed(3);
    L.space.style.opacity = smooth(ramp(p, 0.78, 0.9)).toFixed(3);
    L.sun.style.opacity = band(p, 0, 0.08, 0.2, 0.32).toFixed(3);
    L.sun.style.transform = `translateY(${(-ramp(p, 0, 0.3) * 18).toFixed(2)}vh)`;

    // tog'lar: ko'tariladi, keyin kamera yaqinlashib bulutlarga kiradi
    svg.style.setProperty("--day", smooth(ramp(p, 0.1, 0.26)).toFixed(3));
    const rise = smooth(ramp(p, 0, 0.22));
    const approach = Math.pow(ramp(p, 0.18, 0.56), 1.6);
    mLayers.forEach((g, d) => {
      const s = 1 + approach * (0.5 + d * 0.7);
      const ty = (1 - rise) * (150 + d * 70) + approach * d * 60;
      g.style.transform = `translate(0px, ${ty.toFixed(1)}px) scale(${s.toFixed(4)})`;
    });
    svg.style.opacity = (1 - smooth(ramp(p, 0.46, 0.56))).toFixed(3);

    // yorug' bulutlar: tuman ichida paydo bo'ladi, kamera ular orasidan o'tadi
    lightBox.style.opacity = band(p, 0.14, 0.28, 0.56, 0.62).toFixed(3);
    const through = Math.pow(ramp(p, 0.26, 0.58), 2);
    lightDepths.forEach((d, i) => {
      d.style.transform = `translateY(${((1 - ramp(p, 0.12, 0.3)) * 20).toFixed(2)}vh) scale(${(1 + through * (1.2 + i * 2.2)).toFixed(4)})`;
    });
    L.fog.style.opacity = band(p, 0.42, 0.52, 0.58, 0.66).toFixed(3);

    // bo'ronli bulutlar — keyin pastga qolib ketadi (biz tepaga chiqamiz)
    darkBox.style.opacity = band(p, 0.58, 0.66, 0.8, 0.88).toFixed(3);
    const storm = ramp(p, 0.6, 0.86);
    darkDepths.forEach((d, i) => {
      d.style.transform = `translateY(${(storm * storm * (40 + i * 30)).toFixed(2)}vh) scale(${(1.1 + storm * (0.3 + i * 0.6)).toFixed(4)})`;
    });

    // Yer shari
    const gIn = smooth(ramp(p, 0.8, 0.92));
    globeCanvas.style.opacity = gIn.toFixed(3);
    globeCanvas.style.transform = `translateY(${((1 - gIn) * 35).toFixed(2)}vh) scale(${(1.35 - gIn * 0.35).toFixed(4)})`;
    if (gIn > 0) {
      drawGlobe(p, performance.now());
      if (!globeLoop && !reduceMotion) { globeLoop = true; requestAnimationFrame(spin); }
    }

    // matnlar
    const S = [
      [1 - smooth(ramp(p, 0.05, 0.11)), -ramp(p, 0, 0.11) * 60],
      [band(p, 0.16, 0.21, 0.31, 0.36), (1 - ramp(p, 0.16, 0.21)) * 40 - ramp(p, 0.31, 0.36) * 40],
      [band(p, 0.39, 0.44, 0.52, 0.57), (1 - ramp(p, 0.39, 0.44)) * 40 - ramp(p, 0.52, 0.57) * 40],
      [band(p, 0.62, 0.67, 0.75, 0.8), (1 - ramp(p, 0.62, 0.67)) * 40 - ramp(p, 0.75, 0.8) * 40],
      [smooth(ramp(p, 0.88, 0.95)), (1 - ramp(p, 0.88, 0.95)) * 40],
    ];
    scenes.forEach((s) => {
      const key = s.dataset.scene;
      if (key === "hint") {
        s.style.opacity = (1 - ramp(p, 0, 0.03)).toFixed(3);
        return;
      }
      const [vis, dy] = S[+key];
      setScene(s, vis, dy);
    });
    bar.style.transform = `scaleY(${p.toFixed(4)})`;
  }

  // Yer shari ko'rinib turganda sekin tebranadi (faqat shu paytda chiziladi)
  function spin(time) {
    if (progress < 0.79 || !inView) { globeLoop = false; return; }
    drawGlobe(progress, time);
    requestAnimationFrame(spin);
  }

  function onScroll() {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }

  let inView = true;
  new IntersectionObserver(([e]) => {
    inView = e.isIntersecting;
    if (inView) onScroll();
  }).observe(root);

  function onResize() {
    drawStars();
    sizeGlobe();
    onScroll();
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onResize);
  // til almashtirilganda (renderAll) shahar nomlarini qayta chizish uchun
  document.addEventListener("click", (e) => { if (e.target.closest("[data-lang-btn]")) setTimeout(onScroll, 0); });
  onResize();
})();
