// Toronto feasibility page: renders Phase 1 content from SITE_DATA.phase1.
document.addEventListener("DOMContentLoaded", () => {
  const { D, el, renderList } = window.Site;
  const p = D.phase1;
  if (!p) return;

  document.getElementById("verdict").textContent = p.verdict;
  document.getElementById("prepared-note").innerHTML = p.prepared_note;

  // ---------- the feasibility gate (Q1-Q3 have a one-line answer; Q4 and Q5 are summarized)
  const gate = document.getElementById("gate-body");
  const extra = {
    "Q4": p.overlap,
    "Q5": "Address or parcel for application-to-permit timing and attrition; 2021 census tract for anything involving completions or starts. Wards are too coarse and were redrawn in 2018.",
  };
  p.gate.forEach((g) => {
    const key = g.q.slice(0, 2);
    const tr = el("tr");
    tr.appendChild(el("th", { scope: "row", style: "font-weight:400" }, g.q.replace(/^Q\d\.\s*/, "")));
    tr.appendChild(el("td", null, g.a || extra[key] || ""));
    gate.appendChild(tr);
  });

  // ---------- coverage timeline. Start years are read from the coverage table text in
  // phase1/feasibility.md section 3 (Q4); "open" bars continue to the snapshot date.
  const T0 = 2000, T1 = 2027;
  const x = (y) => ((y - T0) / (T1 - T0)) * 100;
  const rows = [
    { label: "Rezoning and site-plan applications", start: 2008.0, open: true, note: "2008-01 →" },
    { label: "Committee of Adjustment applications", term: "coa", start: 2001, open: true, note: "2001 →" },
    { label: "TLAB appeals", term: "tlab", start: 2017 + 4 / 12, open: true, note: "2017-05 →" },
    { label: "Approval / appeal outcomes", none: "Current status only; no dates" },
    { label: "Zoning (By-law 569-2013)", term: "zoning-bylaw", start: 2013 + 4 / 12, open: true, note: "from 2013-05-09 (layer as of 2023-06)" },
    { label: "Building permits", start: 2002, open: true, note: "reliable from ~2002" },
    { label: "Completions by census tract", term: "census-tract", start: 2010, end: 2023, note: "2010–2022" },
  ];
  const tl = document.getElementById("timeline");
  const overlap = el("div", { class: "tl-overlap", "aria-hidden": "true" });
  rows.forEach((r) => {
    const row = el("div", { class: "tl-row" });
    const name = r.term ? `<a class="term" data-term="${r.term}">${r.label}</a>` : r.label;
    row.appendChild(el("div", { class: "lab" }, `${name}<small>${r.note || ""}</small>`));
    const track = el("div", { class: "tl-track" });
    if (r.none) {
      track.appendChild(el("span", { class: "tl-none", text: r.none }));
    } else {
      const end = r.open ? T1 : r.end;
      track.appendChild(el("div", {
        class: "tl-bar" + (r.open ? " open" : ""),
        style: `left:${x(r.start)}%;width:${x(end) - x(r.start)}%`,
      }));
    }
    row.appendChild(track);
    tl.appendChild(row);
  });
  // Axis + overlap band (2013-05 to 2022-12) drawn over the tracks column.
  const axis = el("div", { class: "tl-axis", "aria-hidden": "true", "data-nocheck": "axis ticks" });
  axis.appendChild(el("div"));
  const ticks = el("div", { class: "ticks" });
  [2000, 2005, 2010, 2015, 2020, 2025].forEach((y) => ticks.appendChild(el("span", { style: `left:${x(y)}%`, text: String(y) })));
  axis.appendChild(ticks);
  tl.appendChild(axis);
  // Position the band over the right-hand column once layout is known.
  function placeOverlap() {
    const firstTrack = tl.querySelector(".tl-track");
    const box = tl.getBoundingClientRect();
    const t = firstTrack.getBoundingClientRect();
    const left = t.left - box.left + (x(2013 + 4 / 12) / 100) * t.width;
    const right = t.left - box.left + (x(2023) / 100) * t.width;
    overlap.style.left = left + "px";
    overlap.style.width = right - left + "px";
  }
  tl.prepend(overlap);
  placeOverlap();
  window.addEventListener("resize", placeOverlap);

  document.getElementById("overlap-text").innerHTML = p.overlap +
    " That window is what the recommended study period is built around.";
  const cov = document.getElementById("cov-body");
  p.coverage_table.rows.forEach((r) => {
    const tr = el("tr");
    tr.appendChild(el("th", { scope: "row" }, r[0]));
    tr.appendChild(el("td", null, r[1]));
    cov.appendChild(tr);
  });

  // ---------- eight limitations
  // Plain-language headline for each (this site's wording) and the matching condition from the
  // verdict section of feasibility.md (index into verdict_conditions, or null).
  const plain = [
    ["Counts of completed homes below the whole-city level stop in 2022.", 1],
    ["What the zoning was on a past date can be reconstructed only in part.", 0],
    ["Toronto's 2013 city-wide zoning by-law still does not cover the whole city.", 0],
    ["A closed-out building permit is not the same as a finished home.", 1],
    ["The open data overwrites appeal history, so older appeals are mostly invisible.", 2],
    ["Applications can be tied to permits reliably only for larger projects; the rest are matched by address.", null],
    ["The projects are far from a random sample: most large ones are linked to a rezoning, most small ones to a minor variance (upper bounds).", 3],
    ["Lost units from demolitions are recorded patchily, so “net new homes” is a weak measure.", 4],
  ];
  const terms = {
    3: ' <a class="term" data-term="cleared-permit">What is a cleared permit?</a>',
    5: ' <a class="term" data-term="olt">Who hears appeals?</a>',
    6: ' <a class="term" data-term="planning-act">What is a Planning-Act project?</a>',
    7: ' <a class="term" data-term="rezoning">Rezoning</a> · <a class="term" data-term="minor-variance">minor variance</a> · <a class="term" data-term="as-of-right">as-of-right</a>',
  };
  const host = document.getElementById("limitations");
  p.limitations.forEach((lim, i) => {
    const [headline, cond] = plain[i] || [lim.lead, null];
    const d = el("details", { class: "acc", id: "limit-" + (i + 1) });
    d.appendChild(el("summary", null,
      `<span class="num">${i + 1}</span><span class="head">${headline}</span><span class="sub">Source heading: ${lim.lead}</span>`));
    const body = el("div", { class: "body" });
    body.appendChild(el("h4", { text: "What the study found" }));
    const q = el("blockquote");
    if (lim.body) q.appendChild(el("p", null, lim.body));
    if (lim.sub.length) {
      const ul = el("ul");
      lim.sub.forEach((s) => ul.appendChild(el("li", null, s)));
      q.appendChild(ul);
    }
    body.appendChild(q);
    if (i === 6) {
      body.appendChild(el("h4", { text: "Share of new-residential permit projects linked to each kind of planning file (2018–2025 applications)" }));
      const wrap = el("div", { class: "table-scroll" });
      const t = el("table");
      t.appendChild(el("caption", null, "Upper bounds: the address match has no date window, and an address can have unrelated past files. MV = minor variance, OZ = rezoning."));
      const thead = el("thead");
      const hr = el("tr");
      p.link_table.header.forEach((h, j) => hr.appendChild(el("th", { scope: "col", class: j ? "num" : "" }, h)));
      thead.appendChild(hr);
      t.appendChild(thead);
      const tb = el("tbody");
      p.link_table.rows.forEach((r) => {
        const tr = el("tr");
        r.forEach((c, j) => tr.appendChild(el(j ? "td" : "th", j ? { class: "num" } : { scope: "row" }, c)));
        tb.appendChild(tr);
      });
      t.appendChild(tb);
      wrap.appendChild(t);
      body.appendChild(wrap);
    }
    if (cond != null && p.verdict_conditions[cond]) {
      const c = p.verdict_conditions[cond];
      body.appendChild(el("h4", { text: "How the plan handles it" }));
      body.appendChild(el("blockquote", null, `<p><strong>${c.lead}</strong> ${c.body}</p>`));
    }
    if (terms[i]) body.appendChild(el("p", { class: "small" }, "Terms:" + terms[i]));
    d.appendChild(body);
    host.appendChild(d);
  });
  const fb = el("div", { class: "callout prose", style: "margin-top:18px" },
    `<p><strong>If Phase 2 finds the zoning reconstruction unreliable</strong>, the study has a fallback:</p><p>${p.fallback.replace(/^<strong>Fallback[^<]*<\/strong>\s*/, "")}</p>`);
  host.appendChild(fb);

  // ---------- frame
  const period = p.frame[0];
  const ul = document.getElementById("frame-period");
  period.sub.forEach((s) => ul.appendChild(el("li", null, s)));
  document.getElementById("frame-unit").innerHTML = p.frame[1].html.replace(/^<strong>[^<]*<\/strong>\s*/, "");

  // ---------- multiplex permit columns (2026 is a partial year)
  const mx = p.multiplex_table;
  const years = mx.header.slice(1);
  const vals = mx.rows[0].slice(1).map(Number);
  const max = Math.max(...vals);
  const cols = el("div", { class: "cols", style: `--n:${years.length}` });
  const xs = el("div", { class: "cols-x", style: `--n:${years.length}` });
  years.forEach((y, i) => {
    const partial = /YTD/.test(y);
    const c = el("div", { class: "col" + (partial ? " partial" : ""), title: `${y}: ${vals[i]} permits` });
    c.appendChild(el("span", { class: "cv", text: String(vals[i]) }));
    c.appendChild(el("span", { class: "cb", style: `height:${(vals[i] / max) * 100}%` }));
    cols.appendChild(c);
    xs.appendChild(el("span", { text: y.replace(" YTD", "*") }));
  });
  const chart = document.getElementById("mx-chart");
  chart.setAttribute("aria-label", "Column chart. " + years.map((y, i) => `${y}: ${vals[i]}`).join("; ") + ".");
  chart.appendChild(cols);
  chart.appendChild(xs);
  document.getElementById("mx-note").innerHTML =
    "* 2026 is year-to-date at the time of the study (hatched), so it is not comparable with full years. These are permits issued, not homes completed. Toronto Council adopted the multiplex by-laws on 2023-05-10.";

  // ---------- unverified, corrections, links
  document.getElementById("unverified-list").replaceWith(Object.assign(renderList(p.unverified), { id: "unverified-list" }));
  document.getElementById("corrections").appendChild(renderList(p.corrections));
  const L = p.links;
  document.getElementById("full-links").innerHTML = [
    `<li><a href="${L.summary}">phase1/summary.md</a>: the two-page summary this page is built from.</li>`,
    `<li><a href="${L.feasibility}">phase1/feasibility.md</a>: definitions, verification, the feasibility questions and the verdict in full.</li>`,
    `<li><a href="${L.inventory}">phase1/inventory.csv</a>: the 30 data sources (also browsable on the <a href="sources.html">Data sources</a> page).</li>`,
    `<li><a href="${L.scripts}">phase1/scripts/</a>: the profiling and linkage code. The data itself is not committed.</li>`,
  ].join("");
});
