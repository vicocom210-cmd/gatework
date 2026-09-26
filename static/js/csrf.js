/* ===== GATE WORK — CSRF himoyasi =====
   Saytning o'z serveriga yuboriladigan har bir o'zgartiruvchi so'rovga
   (POST/PUT/PATCH/DELETE) X-CSRFToken sarlavhasini avtomatik qo'shadi.
   Shu sababli boshqa JS fayllarni o'zgartirish shart emas.
   Token avval "csrftoken" cookie'dan olinadi (login'dan keyin Django uni
   yangilaydi), bo'lmasa — sahifadagi <meta name="csrf-token"> dan. */
(function () {
  const SAFE = ["GET", "HEAD", "OPTIONS", "TRACE"];

  function token() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  }

  function sameOrigin(url) {
    try {
      return new URL(url, location.href).origin === location.origin;
    } catch {
      return false;
    }
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    init = init || {};
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const method = (init.method || (input instanceof Request ? input.method : "GET")).toUpperCase();
    if (!SAFE.includes(method) && sameOrigin(url)) {
      const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
      if (!headers.has("X-CSRFToken")) headers.set("X-CSRFToken", token());
      init = { ...init, headers, credentials: init.credentials || "same-origin" };
    }
    return nativeFetch(input, init);
  };
})();
