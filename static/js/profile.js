/* ===== GATE WORK — profilni tahrirlash ===== */
(function () {
  const form = document.querySelector("[data-profile-form]");
  if (!form) return;

  const preview = document.querySelector("[data-avatar-preview]");
  const fileInput = document.querySelector("[data-avatar-input]");
  const chipsBox = document.querySelector("[data-profile-assets]");
  const msg = document.querySelector("[data-profile-msg]");
  const pointsEl = document.querySelector("[data-profile-points]");
  let selected = [];

  function initials(user) {
    const a = (user.firstName || user.name || "?").trim()[0] || "?";
    const b = (user.lastName || "").trim()[0] || "";
    return (a + b).toUpperCase();
  }

  function paintAvatar(user, url) {
    const src = url || user.avatar;
    preview.innerHTML = src ? `<img src="${src}" alt="" />` : `<i>${initials(user)}</i>`;
  }

  function renderChips() {
    chipsBox.innerHTML = ASSETS.map(
      (a) => `<button type="button" class="chip ${selected.includes(a.key) ? "on" : ""}" data-asset="${a.key}">
        <span>${a.icon}</span>${t(a.label)}</button>`,
    ).join("");
    chipsBox.querySelectorAll("[data-asset]").forEach((b) =>
      b.addEventListener("click", () => {
        const key = b.dataset.asset;
        selected = selected.includes(key) ? selected.filter((x) => x !== key) : [...selected, key];
        renderChips();
      }),
    );
  }

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file) preview.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="" />`;
  });

  async function load() {
    const res = await fetch("/api/me");
    if (!res.ok) {
      window.location.href = "/login?redirect=/profile";
      return;
    }
    const { user } = await res.json();
    form.firstName.value = user.firstName || "";
    form.lastName.value = user.lastName || "";
    form.birthDate.value = user.birthDate || "";
    pointsEl.textContent = user.points || 0;
    selected = user.assets || [];
    paintAvatar(user);
    renderChips();
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData();
    fd.append("firstName", form.firstName.value.trim());
    fd.append("lastName", form.lastName.value.trim());
    fd.append("birthDate", form.birthDate.value);
    if (form.password.value) fd.append("password", form.password.value);
    fd.append("assets", JSON.stringify(selected));
    if (fileInput.files[0]) fd.append("avatar", fileInput.files[0]);

    const btn = form.querySelector('button[type="submit"]');
    btn.classList.add("loading");
    try {
      const res = await fetch("/api/profile", { method: "POST", body: fd });
      const data = await res.json();
      btn.classList.remove("loading");
      msg.classList.remove("show", "err");
      void msg.offsetWidth;
      msg.textContent = data.ok ? t("profileSaved") : data.error;
      msg.classList.add("show");
      if (!data.ok) msg.classList.add("err");
      else {
        pointsEl.textContent = data.user.points;
        paintAvatar(data.user);
        form.password.value = "";
      }
    } catch (err) {
      btn.classList.remove("loading");
      msg.textContent = "Serverga ulanishda xatolik.";
      msg.classList.add("show", "err");
    }
  });

  document.addEventListener("DOMContentLoaded", load);
  if (document.readyState !== "loading") load();
})();
