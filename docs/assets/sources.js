// Data sources explorer: search, filter and sort phase1/inventory.csv rows.
document.addEventListener("DOMContentLoaded", () => {
  const { D, el } = window.Site;
  const rows = (D.inventory || []).slice();
  const tbody = document.getElementById("rows");
  const q = document.getElementById("q");
  const fPub = document.getElementById("f-pub");
  const fProv = document.getElementById("f-prov");
  const count = document.getElementById("count");
  const open = new Set();
  let sortKey = "id", sortDir = 1;

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const linkify = (s) => esc(s).replace(/https?:\/\/[^\s);,']+/g, (u) => `<a href="${u}">${u}</a>`);

  [...new Set(rows.map((r) => r.publisher_org))].sort().forEach((v) => fPub.appendChild(el("option", { value: v, text: v })));
  [...new Set(rows.map((r) => r.provenance_group))].sort().forEach((v) => fProv.appendChild(el("option", { value: v, text: v })));

  const FIELDS = [
    ["Publisher", "publisher"], ["Licence / access", "license_access"], ["Geographic coverage", "geographic_coverage"],
    ["Years covered", "temporal_coverage"], ["Last updated", "last_updated"], ["Key fields", "key_fields"],
    ["Limitations", "limitations"], ["Join keys", "join_keys"], ["Provenance", "provenance"],
  ];

  function render() {
    const needle = q.value.trim().toLowerCase();
    const list = rows.filter((r) =>
      (!fPub.value || r.publisher_org === fPub.value) &&
      (!fProv.value || r.provenance_group === fProv.value) &&
      (!needle || Object.values(r).join(" ").toLowerCase().includes(needle)));
    list.sort((a, b) => sortDir * String(a[sortKey]).localeCompare(String(b[sortKey]), "en", { numeric: true }));
    tbody.innerHTML = "";
    list.forEach((r) => {
      const isOpen = open.has(r.id);
      const tr = el("tr");
      tr.appendChild(el("td", { text: r.id }));
      tr.appendChild(el("th", { scope: "row", style: "font-weight:600" }, esc(r.dataset)));
      tr.appendChild(el("td", { "data-label": "Publisher", text: r.publisher }));
      tr.appendChild(el("td", { "data-label": "Years", text: r.temporal_coverage }));
      const warn = r.provenance_group !== "Opened and verified";
      tr.appendChild(el("td", null, `<span class="pill${warn ? " warn" : ""}">${esc(r.provenance_group)}</span>`));
      const td = el("td");
      const b = el("button", { type: "button", class: "rowtoggle", "aria-expanded": String(isOpen), "aria-controls": "d-" + r.id, text: isOpen ? "Hide" : "Details" });
      b.setAttribute("aria-label", (isOpen ? "Hide details for " : "Show details for ") + r.id);
      b.addEventListener("click", () => { isOpen ? open.delete(r.id) : open.add(r.id); render(); document.querySelector(`[aria-controls="d-${r.id}"]`).focus(); });
      td.appendChild(b);
      tr.appendChild(td);
      tbody.appendChild(tr);
      if (isOpen) {
        const dtr = el("tr", { class: "detail", id: "d-" + r.id });
        const cell = el("td", { colspan: "6" });
        const dl = el("dl");
        FIELDS.forEach(([label, key]) => {
          dl.appendChild(el("dt", { text: label }));
          dl.appendChild(el("dd", null, linkify(r[key])));
        });
        dl.appendChild(el("dt", { text: "Links" }));
        dl.appendChild(el("dd", null, `<a href="${esc(r.url)}">Source page</a> · <a href="${esc(r.evidence_url)}">Evidence the study used</a>`));
        cell.appendChild(dl);
        dtr.appendChild(cell);
        tbody.appendChild(dtr);
      }
    });
    count.textContent = `Showing ${list.length} of ${rows.length} sources`;
  }

  document.querySelectorAll("#sources-table th button[data-sort]").forEach((b) => {
    b.addEventListener("click", () => {
      const k = b.dataset.sort;
      sortDir = k === sortKey ? -sortDir : 1;
      sortKey = k;
      document.querySelectorAll("#sources-table th[aria-sort]").forEach((th) => {
        const bb = th.querySelector("button");
        const active = bb.dataset.sort === sortKey;
        th.setAttribute("aria-sort", active ? (sortDir > 0 ? "ascending" : "descending") : "none");
        bb.querySelector(".arrow").textContent = active ? (sortDir > 0 ? "▲" : "▼") : "";
      });
      render();
    });
  });
  q.addEventListener("input", render);
  fPub.addEventListener("change", render);
  fProv.addEventListener("change", render);
  document.getElementById("reset").addEventListener("click", () => {
    q.value = ""; fPub.value = ""; fProv.value = ""; open.clear(); render();
  });
  render();
});
