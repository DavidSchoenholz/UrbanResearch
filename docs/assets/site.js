// Shared helpers: glossary tooltips, number formatting, source-provenance lines.
(function () {
  "use strict";

  const D = window.SITE_DATA || {};
  const fmt = (n) => Number(n).toLocaleString("en-US");

  // Look up "a.b.c" in SITE_DATA.
  function get(path) {
    return path.split(".").reduce((o, k) => (o == null ? o : o[k]), D);
  }

  function el(tag, attrs, html) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") e.className = v;
      else if (k === "text") e.textContent = v;
      else e.setAttribute(k, v);
    }
    if (html != null) e.innerHTML = html;
    return e;
  }

  // Render a list of {html, sub[]} items (from build_data.py) into a <ul>/<ol>.
  function renderList(items, ordered) {
    const list = el(ordered ? "ol" : "ul");
    for (const it of items) {
      const li = el("li", null, it.html);
      if (it.sub && it.sub.length) {
        const sub = el("ul");
        it.sub.forEach((s) => sub.appendChild(el("li", null, s)));
        li.appendChild(sub);
      }
      list.appendChild(li);
    }
    return list;
  }

  // Fill <span data-fig="hamilton.summary.n_parcel_polygons"> with formatted figures.
  function fillFigures(root) {
    root.querySelectorAll("[data-fig]").forEach((n) => {
      const v = get(n.dataset.fig);
      if (v == null) { n.textContent = "?"; n.classList.add("missing"); return; }
      n.textContent = typeof v === "number" ? fmt(v) : v;
    });
  }

  // Provenance links: <p class="prov" data-prov="phase1:phase1/summary.md,phase1/feasibility.md">.
  function fillProvenance(root) {
    const src = (D.snapshot || {}).sources || {};
    root.querySelectorAll("[data-prov]").forEach((n) => {
      const parts = n.dataset.prov.split(";").map((group) => {
        const [key, files] = group.split(":");
        const s = src[key];
        if (!s) return "";
        const links = files.split(",").map((f) =>
          `<a href="https://github.com/DavidSchoenholz/UrbanResearch/blob/${s.sha}/${f}">${f}</a>`).join(", ");
        return `${links} on branch <code>${s.branch}</code> at commit <code>${s.sha.slice(0, 7)}</code>`;
      });
      n.innerHTML = "Source: " + parts.filter(Boolean).join("; ") + ".";
    });
  }

  // ---------- glossary tooltips
  const terms = {};
  (window.GLOSSARY || []).forEach((g) => { terms[g.id] = g; });
  let tip = null;

  function showTip(a) {
    const g = terms[a.dataset.term];
    if (!g) return;
    hideTip();
    tip = el("div", { class: "tip", role: "tooltip", id: "tip-" + g.id });
    tip.appendChild(el("strong", { text: g.term }));
    tip.appendChild(document.createTextNode(g.def));
    document.body.appendChild(tip);
    a.setAttribute("aria-describedby", tip.id);
    const r = a.getBoundingClientRect();
    const w = tip.offsetWidth;
    let left = window.scrollX + r.left;
    left = Math.max(window.scrollX + 16, Math.min(left, window.scrollX + document.documentElement.clientWidth - w - 16));
    let top = window.scrollY + r.bottom + 6;
    if (r.bottom + tip.offsetHeight + 12 > window.innerHeight && r.top > tip.offsetHeight + 12) {
      top = window.scrollY + r.top - tip.offsetHeight - 6;
    }
    tip.style.left = left + "px";
    tip.style.top = top + "px";
  }
  function hideTip() {
    if (!tip) return;
    document.querySelectorAll("[aria-describedby='" + tip.id + "']").forEach((a) => a.removeAttribute("aria-describedby"));
    tip.remove();
    tip = null;
  }

  function initTerms(root) {
    root.querySelectorAll("a.term[data-term]").forEach((a) => {
      if (a.dataset.bound) return;
      a.dataset.bound = "1";
      if (!a.getAttribute("href")) a.setAttribute("href", "glossary.html#" + a.dataset.term);
      a.addEventListener("mouseenter", () => showTip(a));
      a.addEventListener("mouseleave", hideTip);
      a.addEventListener("focus", () => showTip(a));
      a.addEventListener("blur", hideTip);
    });
  }
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideTip(); });
  // No hide-on-scroll: the tip is positioned in document coordinates, and focusing an
  // off-screen term scrolls the page, which would otherwise close the tip immediately.

  window.Site = { D, get, el, fmt, renderList, fillFigures, fillProvenance, initTerms };

  document.addEventListener("DOMContentLoaded", () => {
    // Page scripts run first (they are loaded after this file and also listen for
    // DOMContentLoaded), so defer the shared pass to pick up what they rendered.
    setTimeout(() => {
      fillFigures(document);
      fillProvenance(document);
      initTerms(document);
    }, 0);
  });
})();
