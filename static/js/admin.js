/* ===== GATE WORK — ADMIN PANEL =====
   - foydalanuvchilar ro'yxati, qidiruv, statistika
   - akkauntni tahrirlash (ism, email, tug'ilgan kun, ballar, parol,
     admin huquqi, hujjatlar, rasm), o'chirish
   - har bir foydalanuvchi arxivi (ko'rgan ishlar / arizalar)
   - chat: foydalanuvchilarga javob berish */
(function () {
  const usersBox = document.querySelector("[data-adm-users]");
  if (!usersBox) return;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const avatar = (u, cls = "") =>
    `<span class="avatar-round ${cls}">${u.avatar ? `<img src="${u.avatar}" alt="">` : `<i>${esc((u.firstName || u.name || "?").trim()[0] || "?").toUpperCase()}</i>`}</span>`;
  const isOnline = (u) => u.lastSeen && Date.now() - new Date(u.lastSeen.replace(" ", "T") + "Z").getTime() < 5 * 60 * 1000;

  let users = [];
  let tab = "users";
  let currentThread = null;
  let threadLastId = 0;
  let pollTimer = null;

  /* ---------- STATISTIKA ---------- */
  async function loadStats() {
    const res = await fetch("/api/admin/stats");
    if (!res.ok) { location.href = "/"; return; }
    const s = await res.json();
    const items = [
      ["adminStatUsers", s.users, "👥"], ["adminStatNew", s.newToday, "✨"], ["adminStatOnline", s.online, "🟢"],
      ["adminStatApplies", s.applies, "📨"], ["adminStatViews", s.views, "👁"], ["adminStatUnread", s.unread, "💬"],
      ["adminStatPro", s.pro || 0, "💎"], ["adminStatMax", s.max || 0, "👑"],
    ];
    document.querySelector("[data-adm-stats]").innerHTML = items
      .map(([k, v, ico], i) => `<div class="stat glass" style="animation-delay:${i * 0.06}s"><span>${ico}</span><b data-to="${v}">${v}</b><small>${t(k)}</small></div>`)
      .join("");
    const ub = document.querySelector("[data-adm-unread]");
    ub.textContent = s.unread; ub.hidden = !s.unread;
  }

  /* ---------- FOYDALANUVCHILAR ---------- */
  async function loadUsers() {
    const q = document.querySelector("[data-adm-search]").value.trim();
    const res = await fetch(`/api/admin/users?q=${encodeURIComponent(q)}`);
    if (!res.ok) return;
    users = (await res.json()).users;
    document.querySelector("[data-adm-total]").textContent = `${users.length} ${t("adminUsers").toLowerCase()}`;
    usersBox.innerHTML = users
      .map((u, i) => `
      <article class="adm-user glass ${u.isAdmin ? "is-admin" : ""}" style="animation-delay:${Math.min(i * 0.04, 0.4)}s" data-uid="${u.id}">
        <div class="au-top">
          ${avatar(u)}
          <div class="au-name">
            <b>${esc(u.name)} ${u.plan && u.plan !== "free" ? `<span class="plan-badge ${u.plan}">${u.plan.toUpperCase()}</span>` : ""} ${u.isAdmin ? `<em class="adm-badge sm">${t("adminBadge")}</em>` : ""} ${isOnline(u) ? `<i class="on">● ${t("adminOnline")}</i>` : ""}</b>
            <small>${esc(u.email)}</small>
          </div>
          ${u.unread ? `<span class="unread">${u.unread}</span>` : ""}
        </div>
        <div class="au-meta">
          <span>🏅 ${u.points}</span>
          <span>📨 ${u.applies}</span>
          <span>👁 ${u.views}</span>
          <span title="${t("adminJoined")}">📅 ${(u.createdAt || "").slice(0, 10)}</span>
          <span title="${t("adminLastSeen")}">⏱ ${u.lastSeen ? timeAgo(u.lastSeen) : "—"}</span>
        </div>
        <div class="au-assets">${(u.assets || []).map((a) => { const f = ASSETS.find((x) => x.key === a); return f ? `<span class="req">${f.icon} ${t(f.label)}</span>` : ""; }).join("")}</div>
        <div class="au-actions">
          <button class="btn-ghost sm plan-btn" data-act="plan">💎 ${t("adminPlan")}${u.plan && u.plan !== "free" ? ` · ${(u.planUntil || "").slice(0, 10)}` : ""}</button>
          <button class="btn-ghost sm" data-act="edit">✎ ${t("adminEdit")}</button>
          <button class="btn-ghost sm" data-act="archive">🗂 ${t("adminArchive")}</button>
          <button class="btn-ghost sm" data-act="chat">💬 ${t("adminWrite")}</button>
          ${u.id !== currentUser.id ? `<button class="btn-ghost sm danger" data-act="delete">🗑 ${t("adminDelete")}</button>` : ""}
        </div>
      </article>`)
      .join("");

    usersBox.querySelectorAll("[data-act]").forEach((b) =>
      b.addEventListener("click", () => {
        const uid = Number(b.closest("[data-uid]").dataset.uid);
        const u = users.find((x) => x.id === uid);
        ({ edit: openEdit, archive: openArchive, chat: openThreadFromUsers, delete: deleteUser, plan: openPlan })[b.dataset.act](u);
      }),
    );
  }

  /* ---------- MODAL ---------- */
  const modal = document.querySelector("[data-adm-modal]");
  const modalBody = document.querySelector("[data-adm-modal-body]");
  function showModal(html) {
    modalBody.innerHTML = html;
    modal.hidden = false;
    requestAnimationFrame(() => modal.classList.add("open"));
  }
  function hideModal() {
    modal.classList.remove("open");
    setTimeout(() => (modal.hidden = true), 250);
  }
  document.querySelector("[data-adm-modal-close]").addEventListener("click", hideModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) hideModal(); });

  function openEdit(u) {
    let selected = [...(u.assets || [])];
    showModal(`
      <h2>${t("adminEditTitle")}</h2>
      <form class="adm-form" data-edit-form>
        <div class="avatar-row">
          ${avatar(u, "big-av")}
          <label class="btn-ghost file"><input type="file" name="avatar" accept="image/*" hidden /><span>${t("profileChange")}</span></label>
        </div>
        <div class="two">
          <label class="field"><input name="firstName" value="${esc(u.firstName)}" placeholder=" " /><span>${t("profileFirst")}</span></label>
          <label class="field"><input name="lastName" value="${esc(u.lastName)}" placeholder=" " /><span>${t("profileLast")}</span></label>
        </div>
        <label class="field"><input name="email" type="email" value="${esc(u.email)}" placeholder=" " required /><span>${t("adminEmail")}</span></label>
        <div class="two">
          <label class="field date"><input name="birthDate" type="date" value="${esc(u.birthDate)}" placeholder=" " /><span>${t("profileBirth")}</span></label>
          <label class="field"><input name="points" type="number" min="0" value="${u.points}" placeholder=" " /><span>${t("adminPoints")}</span></label>
        </div>
        <label class="field"><input name="password" type="password" minlength="6" placeholder=" " autocomplete="new-password" /><span>${t("adminNewPass")}</span></label>
        ${u.id !== currentUser.id ? `<label class="adm-check"><input type="checkbox" name="isAdmin" ${u.isAdmin ? "checked" : ""} /> <span>${t("adminIsAdmin")}</span></label>` : ""}
        <h4 class="have-title">${t("haveTitle")}</h4>
        <div class="chips" data-edit-assets></div>
        <div class="adm-form-foot">
          <button type="button" class="btn-ghost" data-cancel>${t("adminCancel")}</button>
          <button type="submit" class="btn-primary big">${t("adminSave")}</button>
        </div>
        <p class="auth-note" data-edit-msg></p>
      </form>`);

    const form = modalBody.querySelector("[data-edit-form]");
    const chips = form.querySelector("[data-edit-assets]");
    const paint = () => {
      chips.innerHTML = ASSETS.map((a) => `<button type="button" class="chip ${selected.includes(a.key) ? "on" : ""}" data-asset="${a.key}"><span>${a.icon}</span>${t(a.label)}</button>`).join("");
      chips.querySelectorAll("[data-asset]").forEach((b) => b.addEventListener("click", () => {
        const k = b.dataset.asset;
        selected = selected.includes(k) ? selected.filter((x) => x !== k) : [...selected, k];
        paint();
      }));
    };
    paint();
    form.querySelector("[data-cancel]").addEventListener("click", hideModal);
    form.avatar.addEventListener("change", () => {
      const f = form.avatar.files[0];
      if (f) modalBody.querySelector(".big-av").innerHTML = `<img src="${URL.createObjectURL(f)}" alt="">`;
    });
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      fd.set("isAdmin", form.isAdmin && form.isAdmin.checked ? "1" : "0");
      if (!form.isAdmin) fd.delete("isAdmin");
      fd.set("assets", JSON.stringify(selected));
      if (!form.password.value) fd.delete("password");
      if (!form.avatar.files[0]) fd.delete("avatar");
      const res = await fetch(`/api/admin/users/${u.id}`, { method: "POST", body: fd });
      const data = await res.json();
      const msg = form.querySelector("[data-edit-msg]");
      msg.classList.remove("err");
      msg.textContent = data.ok ? t("adminSaved") : data.error;
      msg.classList.add("show");
      if (!data.ok) msg.classList.add("err");
      else { setTimeout(hideModal, 700); loadUsers(); loadStats(); }
    });
  }

  /* ---------- TARIF BERISH (PRO / MAX) ---------- */
  async function setPlan(uid, plan, planUntil) {
    const res = await fetch(`/api/admin/users/${uid}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan, planUntil: planUntil || "" }),
    });
    const data = await res.json();
    if (!data.ok) { alert(data.error); return null; }
    loadUsers(); loadStats(); loadThreads();
    return data.user;
  }

  function openPlan(u) {
    const cur = u.plan && u.plan !== "free" ? u.plan : "free";
    showModal(`
      <div class="adm-arc-head">${avatar(u)}<div><h2>${esc(u.name)}</h2><small>${esc(u.email)}</small></div></div>
      <h3 class="have-title">💎 ${t("adminPlanTitle")}</h3>
      <p class="auth-note show">${t("adminPlanHint")}</p>
      <p class="plan-now">${t("planYourPlan")}: <span class="plan-badge ${cur}">${cur.toUpperCase()}</span> ${u.planUntil ? `<small>· ${(u.planUntil || "").slice(0, 10)} ${t("planActiveUntil")}</small>` : ""}</p>
      <label class="field date"><input type="date" data-plan-until placeholder=" " /><span>${t("adminPlanUntil")}</span></label>
      <div class="plan-grant">
        <button class="btn-primary big" data-set-plan="pro">💎 ${t("adminGivePro")} · $20</button>
        <button class="btn-primary big max" data-set-plan="max">👑 ${t("adminGiveMax")} · $180</button>
        ${cur !== "free" ? `<button class="btn-ghost danger" data-set-plan="free">✕ ${t("adminRevokePlan")}</button>` : ""}
      </div>`);
    modalBody.querySelectorAll("[data-set-plan]").forEach((b) =>
      b.addEventListener("click", async () => {
        const until = modalBody.querySelector("[data-plan-until]").value;
        const user = await setPlan(u.id, b.dataset.setPlan, until);
        if (user) { Object.assign(u, user); hideModal(); }
      }),
    );
  }

  async function openArchive(u) {
    const res = await fetch(`/api/admin/users/${u.id}`);
    const data = await res.json();
    if (!data.ok) return;
    let sub = "applies";
    showModal(`
      <div class="adm-arc-head">${avatar(u)}<div><h2>${esc(u.name)}</h2><small>${esc(u.email)}</small></div></div>
      <div class="arc-tabs">
        <button class="pill active" data-sub="applies">📨 ${t("archiveApplies")} <b>${data.archive.applies.length}</b></button>
        <button class="pill" data-sub="views">👁 ${t("archiveViews")} <b>${data.archive.views.length}</b></button>
      </div>
      <div class="arc-list compact" data-sub-list></div>`);
    const listEl = modalBody.querySelector("[data-sub-list]");
    const paint = () => {
      modalBody.querySelectorAll("[data-sub]").forEach((b) => b.classList.toggle("active", b.dataset.sub === sub));
      renderArchiveList(data.archive[sub], sub, listEl);
    };
    modalBody.querySelectorAll("[data-sub]").forEach((b) => b.addEventListener("click", () => { sub = b.dataset.sub; paint(); }));
    paint();
  }

  async function deleteUser(u) {
    if (!confirm(`${t("adminDeleteConfirm")}\n${u.name} (${u.email})`)) return;
    await fetch(`/api/admin/users/${u.id}`, { method: "DELETE" });
    loadUsers(); loadStats(); loadThreads();
  }

  /* ---------- CHAT ---------- */
  const threadsBox = document.querySelector("[data-adm-threads]");
  const threadHead = document.querySelector("[data-adm-thread-head]");
  const threadBody = document.querySelector("[data-adm-thread-body]");
  const threadForm = document.querySelector("[data-adm-thread-form]");

  async function loadThreads() {
    const res = await fetch("/api/chat/threads");
    if (!res.ok) return;
    const { threads } = await res.json();
    if (!threads.length) { threadsBox.innerHTML = `<p class="empty">${t("adminNoThreads")}</p>`; return; }
    threadsBox.innerHTML = threads
      .map((u) => `<button class="th ${currentThread && currentThread.id === u.id ? "active" : ""}" data-tid="${u.id}">
        ${avatar(u, "sm")}
        <span class="th-txt"><b>${esc(u.name)}</b><small>${esc(u.lastText || "—").slice(0, 60)}</small></span>
        <span class="th-side">${u.lastAt ? `<time>${timeAgo(u.lastAt)}</time>` : ""}${u.unread ? `<span class="unread">${u.unread}</span>` : ""}</span>
      </button>`)
      .join("");
    threadsBox.querySelectorAll("[data-tid]").forEach((b) =>
      b.addEventListener("click", () => openThread(threads.find((x) => x.id === Number(b.dataset.tid)))),
    );
  }

  function bubble(m) {
    const mine = m.senderId === currentUser.id;
    return `<div class="msg ${mine ? "mine" : "theirs"} ${m.attachment ? "has-att" : ""}">${GWChatMedia.renderAttachment(m)}${m.text ? `<p>${esc(m.text).replace(/\n/g, "<br>")}</p>` : ""}<time>${mine ? t("chatYou") : esc(currentThread.firstName || currentThread.name)} · ${timeAgo(m.createdAt)}</time></div>`;
  }

  async function openThread(u, keep) {
    if (!u) return;
    if (!keep) { currentThread = u; threadLastId = 0; threadBody.innerHTML = ""; }
    threadHead.innerHTML = `${avatar(u, "sm")}<div><b>${esc(u.name)}</b><small>${esc(u.email)} ${isOnline(u) ? `· <i class="on">● ${t("adminOnline")}</i>` : ""}</small></div>
      <button class="btn-ghost sm plan-btn" data-head-plan>💎 ${u.plan && u.plan !== "free" ? u.plan.toUpperCase() : t("adminPlan")}</button>
      <button class="btn-ghost sm" data-head-edit>✎ ${t("adminEdit")}</button>`;
    threadHead.querySelector("[data-head-edit]").addEventListener("click", () => openEdit(u));
    threadHead.querySelector("[data-head-plan]").addEventListener("click", () => openPlan(u));
    threadForm.hidden = false;
    const res = await fetch(`/api/chat/messages?with=${u.id}&after=${threadLastId}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.messages.length) {
      threadBody.insertAdjacentHTML("beforeend", data.messages.map(bubble).join(""));
      threadLastId = data.messages[data.messages.length - 1].id;
      threadBody.scrollTop = threadBody.scrollHeight;
    }
    if (!keep) { loadThreads(); loadStats(); }
  }

  function openThreadFromUsers(u) {
    switchTab("chat");
    openThread(u);
  }

  GWChatMedia.attachMedia(threadForm, async ({ text, file }) => {
    if (!currentThread) return;
    const data = await GWChatMedia.sendMessage({ text, file, to: currentThread.id });
    if (data.ok) {
      threadBody.insertAdjacentHTML("beforeend", bubble(data.message));
      threadLastId = data.message.id;
      threadBody.scrollTop = threadBody.scrollHeight;
      loadThreads();
    } else if (data.error) alert(data.error);
  });

  /* ---------- TABLAR ---------- */
  function switchTab(name) {
    tab = name;
    document.querySelectorAll("[data-adm-tab]").forEach((b) => b.classList.toggle("active", b.dataset.admTab === name));
    document.querySelectorAll("[data-adm-pane]").forEach((p) => (p.hidden = p.dataset.admPane !== name));
    if (name === "chat") loadThreads();
  }
  document.querySelectorAll("[data-adm-tab]").forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.admTab)));

  let searchTimer;
  document.querySelector("[data-adm-search]").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadUsers, 250);
  });

  async function init() {
    if (!window.isLoggedIn || !currentUser || !currentUser.isAdmin) { location.href = "/"; return; }
    await loadStats();
    await loadUsers();
    pollTimer = setInterval(() => {
      if (tab === "chat") { loadThreads(); if (currentThread) openThread(currentThread, true); }
      loadStats();
    }, 4000);
  }

  // app.js /api/me ni tekshirib bo'lgach ishga tushamiz
  const wait = setInterval(() => {
    if (typeof window.isLoggedIn !== "undefined") { clearInterval(wait); init(); }
  }, 50);
})();
