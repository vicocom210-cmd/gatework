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
    tabs.classList.toggle("is-signup", name === "signup");
    tabs.querySelectorAll("[data-auth-tab]").forEach((b) => {
      b.classList.toggle("active", b.dataset.authTab === name);
    });
    panes.forEach((p) => p.classList.toggle("active", p.dataset.authPane === name));
    if (msg) msg.classList.remove("show", "err");
    history.replaceState(null, "", name === "signup" ? "#signup" : "#login");
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

      const isSignup = form.dataset.authPane === "signup";
      const email = form.querySelector('input[name="email"]').value.trim();
      const password = form.querySelector('input[name="password"]').value;

      btn.classList.add("loading");
      try {
        // UZ: RO'YXATDAN O'TISH — endi 2 bosqichli: avval kod yuboriladi
        //     (email + SMS), keyin foydalanuvchi kodni kiritib tasdiqlaydi.
        // RU: РЕГИСТРАЦИЯ — теперь в 2 шага: сначала код (email + SMS), затем ввод.
        // EN: SIGN-UP — now 2 steps: first send codes (email + SMS), then verify.
        // DE: REGISTRIERUNG — jetzt 2 Schritte: erst Codes senden, dann bestätigen.
        if (isSignup) {
          const phoneEl = form.querySelector('input[name="phone"]');
          const phone = phoneEl ? phoneEl.value.trim() : "";
          const payload = {
            firstName: form.querySelector('input[name="firstName"]').value.trim(),
            lastName: form.querySelector('input[name="lastName"]').value.trim(),
            birthDate: form.querySelector('input[name="birthDate"]').value,
            email,
            password,
            phone,
          };
          const res = await fetch("/api/register/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const data = await res.json();
          btn.classList.remove("loading");
          if (data.ok) {
            openVerifyModal(email, data.needPhone);
          } else {
            showMsg(data.error || t("authFillAll"), true);
          }
          return;
        }

        // UZ: KIRISH (login) — avvalgidek.
        const res = await fetch("/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        btn.classList.remove("loading");
        if (data.ok) {
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

  /* ---------- TASDIQLASH OYNASI (email + SMS kodi) ----------
     UZ: Kod kiritish uchun kichik oynani JS orqali yasaymiz (alohida HTML shart
         emas). Email kodi doim, SMS kodi faqat telefon kiritilган bo'lsa.
     RU: Небольшое окно для ввода кода строим через JS. Email-код всегда, SMS —
         только если указан телефон.
     EN: Build a small code-entry modal with JS (no separate HTML needed). The
         email code always, the SMS code only if a phone was given.
     DE: Kleines Code-Eingabefenster per JS. E-Mail-Code immer, SMS-Code nur bei
         angegebener Telefonnummer. */
  function openVerifyModal(email, needPhone) {
    const old = document.querySelector("[data-verify-modal]");
    if (old) old.remove();

    const wrap = document.createElement("div");
    wrap.setAttribute("data-verify-modal", "");
    wrap.style.cssText =
      "position:fixed;inset:0;z-index:200;display:grid;place-items:center;" +
      "background:rgba(0,0,0,.55);backdrop-filter:blur(4px);padding:16px;";
    wrap.innerHTML = `
      <div class="glass" style="max-width:420px;width:100%;border-radius:20px;padding:24px;border:1px solid var(--border);background:var(--background);">
        <h3 style="margin:0 0 6px;font-size:1.2rem;">${t("verifyTitle")}</h3>
        <p style="margin:0 0 16px;color:var(--muted-fg);font-size:14px;">${t("verifySub").replace("%s", email)}</p>
        <label style="display:block;font-size:13px;color:var(--muted-fg);margin-bottom:4px;">${t("verifyEmailCode")}</label>
        <input data-vcode-email inputmode="numeric" maxlength="6" placeholder="______"
          style="width:100%;padding:12px 14px;border-radius:12px;border:1px solid var(--border);background:transparent;color:var(--foreground);font-size:18px;letter-spacing:6px;text-align:center;margin-bottom:14px;" />
        ${needPhone ? `
        <label style="display:block;font-size:13px;color:var(--muted-fg);margin-bottom:4px;">${t("verifyPhoneCode")}</label>
        <input data-vcode-phone inputmode="numeric" maxlength="6" placeholder="______"
          style="width:100%;padding:12px 14px;border-radius:12px;border:1px solid var(--border);background:transparent;color:var(--foreground);font-size:18px;letter-spacing:6px;text-align:center;margin-bottom:14px;" />` : ""}
        <p data-vmsg style="min-height:18px;margin:0 0 10px;font-size:13px;color:#ff6b6b;"></p>
        <button class="btn-primary big" data-vsubmit style="width:100%;">${t("verifyBtn")}</button>
        <div style="display:flex;justify-content:space-between;margin-top:12px;font-size:13px;">
          <button type="button" class="link" data-vresend style="background:none;border:0;color:var(--primary);cursor:pointer;">${t("verifyResend")}</button>
          <button type="button" class="link" data-vcancel style="background:none;border:0;color:var(--muted-fg);cursor:pointer;">${t("verifyCancel")}</button>
        </div>
      </div>`;
    document.body.appendChild(wrap);

    const vmsg = wrap.querySelector("[data-vmsg]");
    const emailInput = wrap.querySelector("[data-vcode-email]");
    const phoneInput = wrap.querySelector("[data-vcode-phone]");
    emailInput.focus();

    wrap.querySelector("[data-vcancel]").addEventListener("click", () => wrap.remove());

    wrap.querySelector("[data-vresend]").addEventListener("click", async () => {
      vmsg.style.color = "var(--muted-fg)";
      vmsg.textContent = "...";
      try {
        await fetch("/api/register/resend", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });
        vmsg.textContent = t("verifyResent");
      } catch { vmsg.textContent = ""; }
    });

    wrap.querySelector("[data-vsubmit]").addEventListener("click", async () => {
      const body = { email, emailCode: emailInput.value.trim() };
      if (phoneInput) body.phoneCode = phoneInput.value.trim();
      vmsg.style.color = "#ff6b6b";
      vmsg.textContent = "";
      try {
        const res = await fetch("/api/register/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        if (data.ok) {
          window.location.href = pendingRedirect;
        } else {
          vmsg.textContent = data.error || "Xatolik";
        }
      } catch {
        vmsg.textContent = "Serverga ulanishda xatolik.";
      }
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
