/* ===== GATE WORK — eng faol foydalanuvchilar reytingi ===== */
(function () {
  const box = document.querySelector("[data-rating]");
  if (!box) return;

  const medal = (rank) => (rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : rank);

  async function load() {
    let users = [];
    try {
      const res = await fetch("/api/rating");
      const data = await res.json();
      users = data.users || [];
    } catch (e) {
      users = [];
    }

    if (!users.length) {
      box.innerHTML = `<p class="empty glass-soft">${t("ratingEmpty")}</p>`;
      return;
    }

    box.innerHTML = users
      .map((u, i) => {
        const av = u.avatar
          ? `<img src="${u.avatar}" alt="" />`
          : `<i>${(u.firstName || u.name || "?").trim()[0].toUpperCase()}</i>`;
        return `<article class="rank-row glass reveal" style="transition-delay:${Math.min(i * 0.06, 0.4)}s">
          <span class="rank-no top${u.rank <= 3 ? u.rank : ""}">${medal(u.rank)}</span>
          <span class="avatar-round">${av}</span>
          <span class="rank-name">${u.name || "—"}</span>
          <span class="rank-pts"><b>${u.points}</b> ${t("ratingPoints")}</span>
        </article>`;
      })
      .join("");

    requestAnimationFrame(() => box.querySelectorAll(".reveal").forEach((el) => el.classList.add("in")));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load);
  else load();
})();
