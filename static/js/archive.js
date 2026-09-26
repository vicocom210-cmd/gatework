/* ===== GATE WORK — foydalanuvchi arxivi (ko'rilgan ishlar / arizalar) ===== */
(function () {
  const list = document.querySelector("[data-arc-list]");
  if (!list) return;

  let data = { applies: [], views: [] };
  let tab = "applies";
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  window.renderArchiveList = function (items, kind, target) {
    target = target || list;
    if (!items.length) {
      target.innerHTML = `<p class="empty glass-soft">${t(kind === "applies" ? "archiveEmptyApplies" : "archiveEmptyViews")}</p>`;
      return;
    }
    target.innerHTML = items
      .map((e, i) => {
        const c = COUNTRIES.find((x) => x.code === e.country);
        return `<article class="arc-row glass reveal in" style="transition-delay:${Math.min(i * 0.04, 0.3)}s">
          <span class="arc-ico ${kind === "applies" ? "ap" : "vw"}">${kind === "applies" ? "📨" : "👁"}</span>
          <div class="arc-main">
            <h3>${esc(e.title) || "—"}</h3>
            <p>${esc(e.employer) || ""} ${e.city ? "· " + esc(e.city) : ""} ${c ? c.flag : ""}</p>
          </div>
          <time>${timeAgo(e.createdAt)}</time>
          ${e.url ? `<a class="btn-apply" href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${t(kind === "applies" ? "archiveAgain" : "archiveOpen")} ↗</a>` : ""}
        </article>`;
      })
      .join("");
  };

  function render() {
    document.querySelectorAll("[data-arc-tab]").forEach((b) => b.classList.toggle("active", b.dataset.arcTab === tab));
    document.querySelector("[data-arc-n='applies']").textContent = data.applies.length;
    document.querySelector("[data-arc-n='views']").textContent = data.views.length;
    renderArchiveList(data[tab], tab);
  }

  async function load() {
    const res = await fetch("/api/archive");
    if (!res.ok) { location.href = "/login?redirect=/archive"; return; }
    data = await res.json();
    render();
  }

  document.querySelectorAll("[data-arc-tab]").forEach((b) =>
    b.addEventListener("click", () => { tab = b.dataset.arcTab; render(); }),
  );
  document.querySelector("[data-arc-clear]").addEventListener("click", async () => {
    if (!confirm(t("archiveClear") + "?")) return;
    await fetch("/api/archive/clear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind: tab === "applies" ? "apply" : "view" }) });
    load();
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
  else load();
})();
