// Ideas page: idea cards grouped as in the README, with filter buttons.
document.addEventListener("DOMContentLoaded", () => {
  const { D, el } = window.Site;
  const ideas = D.ideas;
  if (!ideas) return;
  document.getElementById("caveat").innerHTML = ideas.caveat;

  const host = document.getElementById("groups");
  const sections = {};
  ideas.groups.forEach((g) => {
    const sec = el("section", { class: "idea-group", "data-group": g.key, "aria-labelledby": "g-" + g.key });
    sec.appendChild(el("h3", { id: "g-" + g.key }, g.title + (g.note ? ` <span class="muted small" style="font-family:var(--sans);font-weight:400">${g.note}</span>` : "")));
    const cards = el("div", { class: "cards" });
    g.items.forEach((it) => {
      const c = el("article", { class: "card idea" });
      c.appendChild(el("h4", { style: "margin:0;font:600 18px/1.3 var(--serif)" }, it.name));
      // The README says "the Phase 2 pipeline below"; on this site it is a separate page.
      const q = it.question.replace("the Phase 2 pipeline below", 'the <a href="pipeline.html">Phase 2 pipeline</a>');
      c.appendChild(el("p", null, q.charAt(0).toUpperCase() + q.slice(1)));
      if (it.data) c.appendChild(el("p", { class: "data" }, `<strong>Suggested data (unverified):</strong> ${it.data}`));
      cards.appendChild(c);
    });
    sec.appendChild(cards);
    host.appendChild(sec);
    sections[g.key] = sec;
  });

  const filters = document.getElementById("filters");
  const count = document.getElementById("count");
  const opts = [["all", "All ideas"], ...ideas.groups.map((g) => [g.key, g.title])];
  function apply(key) {
    let n = 0;
    ideas.groups.forEach((g) => {
      const show = key === "all" || key === g.key;
      sections[g.key].hidden = !show;
      if (show) n += g.items.length;
    });
    filters.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.key === key)));
    count.textContent = `Showing ${n} ideas`;
  }
  opts.forEach(([key, label]) => {
    const b = el("button", { type: "button", "data-key": key, "aria-pressed": "false", text: label });
    b.addEventListener("click", () => apply(key));
    filters.appendChild(b);
  });
  apply("all");
});
