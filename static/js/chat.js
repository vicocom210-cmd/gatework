/* ===== GATE WORK — jonli chat (foydalanuvchi <-> admin) =====
   Barcha sahifalarda o'ng pastdagi tugma. Polling: har 4 soniyada
   yangi xabarlar tekshiriladi. Admin o'zining panelida (admin.js)
   javob beradi. Matn + rasm / video / fayl / ovozli xabar. */
(function () {
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  window.timeAgo = function (iso) {
    if (!iso) return "";
    const d = new Date(iso.replace(" ", "T") + (iso.endsWith("Z") ? "" : "Z"));
    const diff = Math.max(0, (Date.now() - d.getTime()) / 1000);
    if (diff < 60) return t("timeNow");
    if (diff < 3600) return `${Math.floor(diff / 60)} ${t("timeMin")}`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} ${t("timeHour")}`;
    if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} ${t("timeDay")}`;
    return d.toLocaleDateString();
  };

  /* ---------- UMUMIY: ilova ko'rsatish (chat.js va admin.js uchun) ---------- */
  function renderAttachment(m) {
    if (!m.attachment) return "";
    const url = m.attachment;
    const name = esc(m.attachmentName || t("chatFile"));
    switch (m.attachmentType) {
      case "image":
        return `<a class="att att-img" href="${url}" target="_blank" rel="noopener"><img src="${url}" alt="${name}" loading="lazy" /></a>`;
      case "video":
        return `<video class="att att-video" src="${url}" controls preload="metadata"></video>`;
      case "audio":
        return `<div class="att att-audio"><span>🎤 ${t("chatVoiceMsg")}</span><audio src="${url}" controls preload="metadata"></audio></div>`;
      default:
        return `<a class="att att-file" href="${url}" download="${name}" target="_blank" rel="noopener"><span class="ico">📄</span><span class="nm">${name}</span><span class="dl">⬇</span></a>`;
    }
  }

  /* ---------- UMUMIY: yuborish (JSON yoki multipart) ---------- */
  async function sendMessage({ text, file, to }) {
    let res;
    if (file) {
      const fd = new FormData();
      fd.append("text", text || "");
      fd.append("file", file, file.name || "voice.webm");
      if (to) fd.append("to", to);
      res = await fetch("/api/chat/send", { method: "POST", body: fd });
    } else {
      res = await fetch("/api/chat/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, to }),
      });
    }
    return res.json().catch(() => ({ ok: false, error: "network" }));
  }

  /* ---------- UMUMIY: formaga 📎 va 🎤 tugmalarini ulash ---------- */
  function attachMedia(form, onSend) {
    if (form.dataset.mediaBound) return;
    form.dataset.mediaBound = "1";
    const input = form.querySelector("input[type=text]");
    const submit = form.querySelector("button[type=submit]");

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.hidden = true;
    fileInput.accept = "image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip,.rar,.7z,.csv";

    const attBtn = document.createElement("button");
    attBtn.type = "button";
    attBtn.className = "chat-tool";
    attBtn.innerHTML = "📎";
    attBtn.title = t("chatAttach");

    const micBtn = document.createElement("button");
    micBtn.type = "button";
    micBtn.className = "chat-tool mic";
    micBtn.innerHTML = "🎤";
    micBtn.title = t("chatVoice");

    const preview = document.createElement("div");
    preview.className = "chat-preview";
    preview.hidden = true;

    form.insertBefore(attBtn, input);
    form.insertBefore(fileInput, input);
    form.insertBefore(micBtn, submit);
    form.parentNode.insertBefore(preview, form);

    let pending = null;
    const setPending = (file) => {
      pending = file;
      if (!file) { preview.hidden = true; preview.innerHTML = ""; return; }
      const isImg = file.type.startsWith("image/");
      preview.innerHTML = `${isImg ? `<img src="${URL.createObjectURL(file)}" alt="" />` : `<span class="ico">${file.type.startsWith("video/") ? "🎬" : file.type.startsWith("audio/") ? "🎤" : "📄"}</span>`}
        <span class="nm">${esc(file.name || t("chatVoiceMsg"))}</span>
        <button type="button" class="icon-btn" data-clear>✕</button>`;
      preview.hidden = false;
      preview.querySelector("[data-clear]").addEventListener("click", () => setPending(null));
      input.focus();
    };

    attBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
      const f = fileInput.files[0];
      fileInput.value = "";
      if (!f) return;
      if (f.size > 25 * 1024 * 1024) { alert(t("chatTooBig")); return; }
      setPending(f);
    });

    /* Ovozli xabar — MediaRecorder */
    let rec = null, chunks = [];
    micBtn.addEventListener("click", async () => {
      if (rec && rec.state === "recording") { rec.stop(); return; }
      if (!navigator.mediaDevices || !window.MediaRecorder) { alert(t("chatMicDenied")); return; }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
        rec = new MediaRecorder(stream, { mimeType: mime });
        chunks = [];
        rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
        rec.onstop = () => {
          stream.getTracks().forEach((tr) => tr.stop());
          micBtn.classList.remove("rec");
          input.placeholder = t("chatPlaceholder");
          const blob = new Blob(chunks, { type: "audio/webm" });
          if (blob.size < 500) return;
          const file = new File([blob], `voice_${Date.now()}.webm`, { type: "audio/webm" });
          onSend({ text: "", file });
        };
        rec.start();
        micBtn.classList.add("rec");
        input.placeholder = t("chatRecording");
      } catch {
        alert(t("chatMicDenied"));
      }
    });

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      const text = input.value.trim();
      if (!text && !pending) return;
      const file = pending;
      input.value = "";
      setPending(null);
      onSend({ text, file });
    }, true);
  }

  window.GWChatMedia = { renderAttachment, sendMessage, attachMedia, esc };

  /* ================= FOYDALANUVCHI VIDJETI ================= */
  const box = document.querySelector("[data-chat-box]");
  if (!box) return;

  const body = box.querySelector("[data-chat-body]");
  const quick = box.querySelector("[data-chat-quick]");
  const form = box.querySelector("[data-chat-form]");
  const input = form.querySelector("input");
  const badges = document.querySelectorAll("[data-chat-unread]");

  let open = false;
  let lastId = 0;
  let me = null;
  let pollTimer = null;
  let loaded = false;
  let pendingText = null;

  // app.js /api/me ni tekshirib bo'lguncha kutamiz (aks holda admin ham "kiring" ko'rardi)
  function authReady() {
    return new Promise((resolve) => {
      if (typeof window.isLoggedIn !== "undefined") return resolve();
      const iv = setInterval(() => {
        if (typeof window.isLoggedIn !== "undefined") { clearInterval(iv); resolve(); }
      }, 50);
      setTimeout(() => { clearInterval(iv); resolve(); }, 6000);
    });
  }
  const isAdmin = () => !!(window.currentUser && window.currentUser.isAdmin);

  function setBadge(n) {
    badges.forEach((b) => {
      b.textContent = n > 99 ? "99+" : n;
      b.hidden = !n;
    });
    document.querySelector(".chat-fab")?.classList.toggle("has-unread", n > 0);
  }

  function bubble(m) {
    const mine = m.senderId === me;
    return `<div class="msg ${mine ? "mine" : "theirs"} ${m.attachment ? "has-att" : ""}" data-mid="${m.id}">
      ${renderAttachment(m)}
      ${m.text ? `<p>${esc(m.text).replace(/\n/g, "<br>")}</p>` : ""}
      <time>${mine ? t("chatYou") : t("chatAdmin")} · ${timeAgo(m.createdAt)}</time>
    </div>`;
  }

  function renderLoginGate() {
    body.innerHTML = `<div class="chat-gate">
      <span class="big">🔒</span>
      <p>${t("chatLoginNeeded")}</p>
      <a class="btn-primary" href="/login?redirect=${encodeURIComponent(location.pathname)}#login">${t("chatLoginBtn")}</a>
    </div>`;
    quick.innerHTML = "";
    form.hidden = true;
  }

  function renderAdminGate() {
    body.innerHTML = `<div class="chat-gate">
      <span class="big">🛡</span>
      <p>${t("chatAdminMode")}</p>
      <a class="btn-primary" href="/admin">${t("chatOpenAdmin")}</a>
    </div>`;
    quick.innerHTML = "";
    form.hidden = true;
  }

  function renderQuick() {
    if (lastId) { quick.innerHTML = ""; return; }
    quick.innerHTML = ["chatQuick1", "chatQuick2", "chatQuick3"]
      .map((k) => `<button type="button" class="chip">${t(k)}</button>`)
      .join("");
    quick.querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => send({ text: b.textContent })),
    );
  }

  async function load(initial) {
    await authReady();
    if (!window.isLoggedIn) { renderLoginGate(); return; }
    if (isAdmin()) { renderAdminGate(); return; }
    form.hidden = false;
    try {
      const res = await fetch(`/api/chat/messages?after=${initial ? 0 : lastId}`);
      if (res.status === 401) { renderLoginGate(); return; }
      if (!res.ok) return;
      const data = await res.json();
      me = data.me;
      if (initial) body.innerHTML = "";
      if (initial && !data.messages.length) {
        body.innerHTML = `<div class="msg theirs hello"><p>${t("chatEmpty")}</p></div>`;
      }
      if (data.messages.length) {
        body.querySelector(".hello")?.remove();
        body.insertAdjacentHTML("beforeend", data.messages.map(bubble).join(""));
        lastId = data.messages[data.messages.length - 1].id;
        body.scrollTop = body.scrollHeight;
      }
      loaded = true;
      renderQuick();
      setBadge(0);
      if (pendingText) { const tx = pendingText; pendingText = null; input.value = tx; input.focus(); }
    } catch {}
  }

  async function send({ text, file }) {
    text = (text || "").trim();
    if (!text && !file) return;
    const tmp = document.createElement("div");
    tmp.className = "msg mine sending";
    tmp.innerHTML = `<p>${file ? "📎 " : ""}${esc(text) || t("chatSending")}</p>`;
    body.querySelector(".hello")?.remove();
    body.appendChild(tmp);
    body.scrollTop = body.scrollHeight;
    const data = await sendMessage({ text, file });
    tmp.remove();
    if (data.ok) {
      body.insertAdjacentHTML("beforeend", bubble(data.message));
      lastId = data.message.id;
      body.scrollTop = body.scrollHeight;
      renderQuick();
    } else if (data.error) {
      alert(data.error);
    }
  }

  /* Polling: chat ochiq — 4 soniyada, yopiq — 15 soniyada bir marta.
     Sahifa (tab) yashirin bo'lsa — umuman so'ramaymiz. 500+ foydalanuvchida
     serverga keladigan so'rovlar sonini bir necha barobar kamaytiradi. */
  function schedulePoll() {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(async () => {
      if (!document.hidden) await pollUnread();
      schedulePoll();
    }, open ? 4000 : 15000);
  }
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && pollTimer) { pollUnread(); schedulePoll(); }
  });

  async function pollUnread() {
    if (!window.isLoggedIn || isAdmin()) return;
    if (open) { load(false); return; }
    try {
      const res = await fetch("/api/chat/unread");
      if (res.ok) setBadge((await res.json()).count || 0);
    } catch {}
  }

  function setOpen(v) {
    open = v;
    box.hidden = false;
    requestAnimationFrame(() => box.classList.toggle("open", v));
    document.querySelector(".chat-fab")?.classList.toggle("active", v);
    if (pollTimer) schedulePoll(); // ochiq/yopiqqa qarab tezlikni o'zgartiramiz
    if (v) {
      load(!loaded);
      setTimeout(() => input.focus(), 250);
    } else {
      setTimeout(() => { if (!open) box.hidden = true; }, 350);
    }
  }

  document.querySelectorAll("[data-open-chat]").forEach((b) => b.addEventListener("click", () => setOpen(!open)));
  box.querySelector("[data-close-chat]").addEventListener("click", () => setOpen(false));
  attachMedia(form, send);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && open) setOpen(false); });

  window.GWChat = {
    open: () => setOpen(true),
    // To'lov oynasidan: chatni ochib, tayyor matnni kiritish maydoniga qo'yadi
    openWith(text) {
      pendingText = text;
      setOpen(true);
      if (loaded && !form.hidden) { input.value = text; pendingText = null; input.focus(); }
    },
    refresh() {
      if (open) { loaded = false; lastId = 0; load(true); }
      if (window.isLoggedIn && !pollTimer) {
        pollUnread();
        schedulePoll();
      }
    },
  };
})();
