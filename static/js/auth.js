/* ===== GATE WORK — kirish / ro'yxatdan o'tish mantiqi (HAQIQIY, backendga ulangan) ===== */

const GOOGLE_CLIENT_ID = "509245131008-kib34dra6sb7djvqjqjh85ac9ucma0av.apps.googleusercontent.com";

(function () {
  const tabs = document.querySelector("[data-auth-tabs]");
  if (!tabs) return;

  const panes = document.querySelectorAll("[data-auth-pane]");
  const msg = document.querySelector("[data-auth-msg]");

  const params = new URLSearchParams(window.location.search);
  const pendingRedirect = params.get("redirect") ? decodeURIComponent(params.get("redirect")) : "/";

  function show(name) {
    const tab = name === "verify" ? "signup" : name; // tasdiqlash — ro'yxatdan o'tishning davomi
    tabs.classList.toggle("is-signup", tab === "signup");
    tabs.querySelectorAll("[data-auth-tab]").forEach((b) => {
      b.classList.toggle("active", b.dataset.authTab === tab);
    });
    panes.forEach((p) => p.classList.toggle("active", p.dataset.authPane === name));
    if (msg) msg.classList.remove("show", "err");
    if (name !== "verify") history.replaceState(null, "", name === "signup" ? "#signup" : "#login");
  }

  /* ---------- email tasdiqlash oynasi ---------- */
  const verifyForm = document.querySelector('[data-auth-pane="verify"]');
  let verifyEmail = "";

  function openVerify(email) {
    verifyEmail = email;
    verifyForm.querySelector("[data-verify-email]").textContent = email;
    verifyForm.querySelector('input[name="code"]').value = "";
    show("verify");
    verifyForm.querySelector('input[name="code"]').focus();
  }

  tabs.querySelectorAll("[data-auth-tab]").forEach((b) => {
    b.addEventListener("click", () => show(b.dataset.authTab));
  });
  document.querySelectorAll("[data-auth-goto]").forEach((b) => {
    b.addEventListener("click", () => show(b.dataset.authGoto));
  });
  if (location.hash === "#signup" || params.get("mode") === "signup") show("signup");

  /* parolni ko'rsatish (o'zgarishsiz, faqat UI) */
  document.querySelectorAll("[data-peek]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = btn.parentElement.querySelector("input");
      input.type = input.type === "password" ? "text" : "password";
      btn.textContent = input.type === "password" ? "👁" : "🙈";
    });
  });

  /* profil rasmini oldindan ko'rish */
  const avatarInput = document.querySelector("[data-avatar-input]");
  const avatarPreview = document.querySelector("[data-avatar-preview]");
  if (avatarInput && avatarPreview) {
    avatarInput.addEventListener("change", () => {
      const file = avatarInput.files[0];
      if (file) avatarPreview.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="" />`;
    });
  }

  /* parol kuchi (o'zgarishsiz, faqat UI) */
  const meter = document.querySelector("[data-meter]");
  const meterLabel = document.querySelector("[data-meter-label]");
  const signupPass = document.querySelector('[data-auth-pane="signup"] input[name="password"]');
  if (meter && signupPass) {
    signupPass.addEventListener("input", () => {
      const v = signupPass.value;
      let score = 0;
      if (v.length >= 6) score++;
      if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
      if (/\d/.test(v) || /[^\w]/.test(v)) score++;
      if (!v) score = 0;
      meter.dataset.level = String(score);
      meter.querySelector("i").style.width = `${(score / 3) * 100}%`;
      const keys = ["", "authWeak", "authMedium", "authStrong"];
      meterLabel.textContent = score ? t(keys[score]) : "";
    });
  }

  function showMsg(text, isError) {
    msg.textContent = text;
    msg.classList.remove("show", "err");
    void msg.offsetWidth; // reflow — animatsiya qayta ishga tushishi uchun
    msg.classList.add("show");
    if (isError) msg.classList.add("err");
  }

  /* ---------- HAQIQIY yuborish (email/parol) ---------- */
  document.querySelectorAll("[data-auth-pane]").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = form.querySelector('button[type="submit"]');
      if (!form.checkValidity()) {
        showMsg(t("authFillAll"), true);
        form.querySelectorAll("input").forEach((i) => {
          if (!i.checkValidity()) i.reportValidity();
        });
        return;
      }

      if (form === verifyForm) {
        btn.classList.add("loading");
        try {
          const res = await fetch("/api/verify-email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: verifyEmail, code: form.querySelector('input[name="code"]').value.trim() }),
          });
          const data = await res.json();
          btn.classList.remove("loading");
          if (data.ok) window.location.href = pendingRedirect;
          else showMsg(data.error || t("authFillAll"), true);
        } catch (err) {
          btn.classList.remove("loading");
          console.error(err);
          showMsg("Serverga ulanishda xatolik yuz berdi.", true);
        }
        return;
      }

      const isSignup = form.dataset.authPane === "signup";
      const email = form.querySelector('input[name="email"]').value.trim();
      const password = form.querySelector('input[name="password"]').value;

      btn.classList.add("loading");
      try {
        let res, data;
        if (isSignup) {
          const fd = new FormData();
          fd.append("firstName", form.querySelector('input[name="firstName"]').value.trim());
          fd.append("lastName", form.querySelector('input[name="lastName"]').value.trim());
          fd.append("birthDate", form.querySelector('input[name="birthDate"]').value);
          fd.append("email", email);
          fd.append("password", password);
          const avatarFile = form.querySelector('input[name="avatar"]');
          if (avatarFile && avatarFile.files[0]) fd.append("avatar", avatarFile.files[0]);
          res = await fetch("/api/register", { method: "POST", body: fd });
        } else {
          res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          });
        }
        data = await res.json();
        btn.classList.remove("loading");

        if (data.needVerify) {
          // ro'yxatdan o'tildi (yoki email hali tasdiqlanmagan) — kod oynasiga o'tamiz
          openVerify(data.email);
          if (data.error) showMsg(data.error, true);
        } else if (data.ok) {
          window.location.href = pendingRedirect;
        } else {
          showMsg(data.error || t("authFillAll"), true);
        }
      } catch (err) {
        btn.classList.remove("loading");
        console.error(err);
        showMsg("Serverga ulanishda xatolik yuz berdi.", true);
      }
    });
  });

  /* ---------- kodni qayta yuborish ---------- */
  const resendBtn = document.querySelector("[data-verify-resend]");
  if (resendBtn) {
    resendBtn.addEventListener("click", async () => {
      resendBtn.disabled = true;
      try {
        const res = await fetch("/api/resend-code", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: verifyEmail }),
        });
        const data = await res.json();
        if (data.ok) showMsg(t("authVerifySent"), false);
        else showMsg(data.error, true);
      } catch (err) {
        console.error(err);
        showMsg("Serverga ulanishda xatolik yuz berdi.", true);
      }
      resendBtn.disabled = false;
    });
  }

  /* ---------- HAQIQIY Google Sign-In ---------- */
  // Har bir .btn-google tugmasi uchun ko'rinmas, haqiqiy Google
  // tugmasini yaratamiz va bosilganda o'shani "bosamiz" — shunda
  // tugma dizayni o'zgarishsiz qoladi, lekin haqiqiy Google oynasi
  // ochiladi.
  function setupGoogleButton(visibleBtn, idx) {
    if (!visibleBtn) return;
    const hiddenId = `googleHidden${idx}`;
    let hidden = document.getElementById(hiddenId);
    if (!hidden) {
      hidden = document.createElement("div");
      hidden.id = hiddenId;
      hidden.style.cssText = "position:absolute; width:1px; height:1px; overflow:hidden; opacity:0; pointer-events:none;";
      document.body.appendChild(hidden);
    }

    if (typeof google === "undefined" || !google.accounts) {
      console.warn("Google Identity Services hali yuklanmadi.");
      return;
    }

    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleGoogleCredential,
    });
    google.accounts.id.renderButton(hidden, { theme: "outline", size: "large" });

    visibleBtn.addEventListener("click", () => {
      const realBtn = hidden.querySelector('div[role="button"]');
      if (realBtn) realBtn.click();
      else console.warn("Google tugmasi topilmadi — sahifani yangilab ko'ring.");
    });
  }

  async function handleGoogleCredential(response) {
    showMsg("Kirish muvaffaqiyatli, yo'naltirilmoqda...", false);
    try {
      const res = await fetch("/auth/google/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: response.credential }),
      });
      const data = await res.json();
      if (!data.ok) {
        showMsg("Google orqali kirishda xatolik: " + data.error, true);
        return;
      }
      window.location.href = pendingRedirect;
    } catch (err) {
      console.error(err);
      showMsg("Serverga ulanishda xatolik yuz berdi.", true);
    }
  }

  window.addEventListener("load", () => {
    setTimeout(() => {
      document.querySelectorAll(".btn-google").forEach((btn, i) => setupGoogleButton(btn, i));
    }, 300);
  });
})();
