// Hamilton page: stats, charts and tables from SITE_DATA.hamilton (summary.json, validation.json).
document.addEventListener("DOMContentLoaded", () => {
  const { D, el, fmt } = window.Site;
  const h = D.hamilton;
  if (!h) return;
  const s = h.summary;
  const v = h.validation;
  const man = s.source_manifest;

  document.getElementById("dl-date").textContent = man.parcels.downloaded_at.slice(0, 10);

  // ---------- headline stats
  const stats = [
    [fmt(s.n_parcel_polygons), "parcel polygons in the City's parcel layer"],
    [fmt(s.n_parcels_without_zoning), "parcels with no zoning polygon under them"],
    [fmt(s.n_split_zoned), "split-zoned parcels (4.2%)"],
    [fmt(s.n_zoning_polygons), `zoning polygons with geometry (${fmt(man.zoning.downloaded)} downloaded)`],
  ];
  const sh = document.getElementById("stats");
  stats.forEach(([val, lab]) => sh.appendChild(el("div", { class: "stat" }, `<div class="v">${val}</div><div class="l">${lab}</div>`)));

  // ---------- validation
  document.getElementById("validation").innerHTML = [
    `<li><strong>Parcels in a single zone: ${fmt(v.single_zone.agree)} of ${fmt(v.single_zone.checked)} agree.</strong></li>`,
    `<li><strong>Split-zoned parcels: ${fmt(v.split_zoned.agree)} of ${fmt(v.split_zoned.checked)}</strong> sample points fall in the parcel's primary zone. The other 25 fall in a secondary zone already listed for that parcel, which is expected: a point inside a split parcel can land in either zone.</li>`,
    `<li class="small muted">Random seed ${v.seed}; checked ${v.checked_at.slice(0, 10)}.</li>`,
  ].join("");

  // ---------- horizontal bar charts as tables
  function bars(hostId, entries, opts = {}) {
    const max = Math.max(...entries.map((e) => e[1]));
    const t = el("table", { class: "bars" });
    if (opts.caption) t.appendChild(el("caption", { class: "skip", text: opts.caption }));
    const thead = el("thead", { class: "skip" });
    thead.innerHTML = `<tr><th scope="col">${opts.keyLabel || "Group"}</th><th scope="col">Parcels</th></tr>`;
    t.appendChild(thead);
    const tb = el("tbody");
    entries.forEach(([k, n], i) => {
      const tr = el("tr");
      if (opts.hideFrom != null && i >= opts.hideFrom) tr.hidden = true;
      tr.appendChild(el("th", { scope: "row", text: opts.label ? opts.label(k) : k }));
      const td = el("td", { class: "bar" });
      const cls = "fill" + (opts.alt && opts.alt(k) ? " alt" : "");
      td.innerHTML = `<div class="track"><span class="${cls}" style="width:calc(${(n / max) * 100}% - 5em)"></span><span class="val">${fmt(n)}</span></div>`;
      tr.appendChild(td);
      tb.appendChild(tr);
    });
    t.appendChild(tb);
    document.getElementById(hostId).appendChild(t);
    return t;
  }

  const byBylaw = Object.entries(s.by_bylaw);
  bars("c1", byBylaw, {
    keyLabel: "Governing by-law", caption: "Parcels by governing by-law",
    alt: (k) => k !== "05-200" && k !== "none",
    label: (k) => (k === "05-200" ? "05-200 (city-wide)" : k),
  });
  document.getElementById("c1-take").textContent =
    `${fmt(s.by_bylaw["05-200"])} parcels (72.7%) are governed by Hamilton's city-wide Zoning By-law 05-200. ` +
    "The other 48,467 (27.3%) are still governed by the by-law of one of the former municipalities merged into today's city.";

  bars("c2", Object.entries(s.by_category), { keyLabel: "Zone category", caption: "Parcels by zone category" });
  document.getElementById("c2-take").textContent =
    `${fmt(s.by_category.Residential)} of ${fmt(s.n_parcel_polygons)} parcels are in a residential zone. Agricultural is a distant second at ${fmt(s.by_category.Agricultural)}.`;

  const codes = Object.entries(s.top_zone_codes);
  const t3 = bars("c3", codes, { keyLabel: "Zone code", caption: "Parcels by primary zone code, top 30", hideFrom: 15 });
  document.getElementById("c3-take").textContent =
    `R1 is the primary zone of ${fmt(s.top_zone_codes.R1)} parcels, nearly three times the next code, R1a (${fmt(s.top_zone_codes.R1a)}). Showing the top 15 of 30.`;
  const more = document.getElementById("c3-more");
  more.addEventListener("click", () => {
    const showing = more.getAttribute("aria-expanded") === "true";
    t3.querySelectorAll("tbody tr").forEach((tr, i) => { if (i >= 15) tr.hidden = showing; });
    more.setAttribute("aria-expanded", String(!showing));
    more.textContent = showing ? "Show all 30" : "Show top 15 only";
    document.getElementById("c3-take").textContent = document.getElementById("c3-take").textContent
      .replace(showing ? "all 30." : "the top 15 of 30.", showing ? "the top 15 of 30." : "all 30.");
  });

  // ---------- split zoning
  document.getElementById("c4-take").innerHTML =
    `${fmt(s.n_split_zoned)} parcels (4.2%) are split-zoned. For at least 90% of parcels the primary zone's share is 1.0, i.e. the whole parcel to four decimal places; ` +
    `${fmt(s["covered_share_lt_0.95"])} parcels are less than 95% covered by any zoning polygon.`;
  const q = s.primary_share_quantiles;
  const qLabel = { "0.01": "1st", "0.05": "5th", "0.1": "10th", "0.5": "50th (median)" };
  const c4 = document.querySelector("#c4 tbody");
  Object.entries(q).forEach(([k, val]) => {
    c4.appendChild(el("tr", null, `<th scope="row" style="font-weight:400">${qLabel[k] || k}</th><td class="num">${val}</td>`));
  });

  // ---------- conditions
  const olt = Object.entries(s.olt_cases)[0];
  const conds = [
    ["Site-specific exception", s.n_has_exception, "An exception applies. Its text is in Schedule C of 05-200 and in the former by-laws, and is not part of this data."],
    ["Holding provision", s.n_has_holding, "A holding symbol applies: some permissions wait until conditions are met."],
    ["Temporary-use provision", s.n_has_temporary_use, "A temporary-use provision number is recorded on the zoning polygon. The README does not discuss this count."],
    ["Council-approved change not yet final and binding", s.n_pending_council_approved, `Council has approved new zoning covering at least 50% of the parcel that is not yet final and binding; ${fmt(s.pending_bylaws["26-178"])} of these are under By-law 26-178.`],
    ["Tagged with an OLT/OMB case number", s.n_olt_tag, `<strong>Not a live-appeal flag.</strong> Common tags match the city-wide by-law that introduced a zone family; the largest, ${olt[0]} (${fmt(olt[1])} parcels), lines up with By-law 24-051 (low-density residential). It means the parent by-law was appealed, not that the parcel is under appeal today.`],
    ["Inside the interim control by-law area", s.n_interim_control, `At least 50% inside the City's Interim Control By-law Zone layer (${man.interim_control.downloaded} polygon).`],
    ["Inside a zoning compliance review area", s.n_compliance_review_area, `At least 50% inside the "Zoning Compliance Review Required" layer (${man.compliance_review.downloaded} polygons). The README does not say what the review involves.`],
    ["H-converted dwelling parcel", s.n_h_converted, `At least 50% inside the "H-Converted Dwelling Parcel" layer (${man.h_converted_parcels.downloaded} polygons). What this layer means is unexplained in the source.`],
  ];
  const ct = document.querySelector("#conds tbody");
  conds.forEach(([name, n, how]) => {
    const tr = el("tr");
    tr.appendChild(el("th", { scope: "row" }, name));
    tr.appendChild(el("td", { class: "num", text: fmt(n) }));
    tr.appendChild(el("td", null, how));
    ct.appendChild(tr);
  });

  // ---------- data quality
  const unexplained = '<span class="pill warn">Unexplained in the source</span> ';
  const dq = [
    ["Rows that repeat an assessment roll number", fmt(s.n_duplicate_property_num_rows),
      `${fmt(s.n_unique_property_num)} distinct roll numbers. README: "571 rows repeat a roll (multi-part parcels)".`],
    ["Distinct parcel footprints", fmt(s.n_distinct_footprints),
      `${fmt(s.n_rows_sharing_footprint)} rows share a footprint with another row. Build script: "Condo units (MPAC code 370) and some multi-roll properties share one identical footprint." README: 19,780 condo-unit rolls sit on 1,266 shared footprints.`],
    ["Rows flagged as suspect geometry", fmt(s.n_geometry_suspect),
      "Polygon area is under 0.1× or over 10× the assessed site area, or the polygon is over 10 km². README: mostly MPAC 561 and 597, i.e. rail and road-type property."],
    ["Sum of all parcel areas vs. area of their union", `${fmt(s.parcel_area_sum_km2)} km² vs. ${fmt(s.parcel_union_km2)} km²`,
      unexplained + 'The build script computes the union as a check on "parcel layer self-overlap (stacked condo or duplicate polygons would show up here)", but neither it nor the README says how much of the gap each cause accounts for.'],
    ["Parcels with no ward", fmt(s.n_no_ward),
      unexplained + "A ward is attached only where one ward covers at least 50% of the parcel. The source does not say why these parcels have none."],
    ["Zoning polygons with geometry vs. downloaded", `${fmt(s.n_zoning_polygons)} vs. ${fmt(man.zoning.downloaded)}`,
      "README: “11,868 downloaded, 11,837 with geometry”. The build script drops polygons without a shape before the overlay."],
    ["Median of assessed site area ÷ drawn polygon area", String(s.site_area_vs_polygon_median_ratio),
      "Computed by the build script. The README does not discuss it."],
  ];
  const dt = document.querySelector("#dq tbody");
  dq.forEach(([what, val, how]) => {
    const tr = el("tr");
    tr.appendChild(el("th", { scope: "row" }, what));
    tr.appendChild(el("td", { class: "num", text: val }));
    tr.appendChild(el("td", null, how));
    dt.appendChild(tr);
  });

  document.getElementById("map-link").href = h.links.map;
});
