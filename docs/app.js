(function () {
  var D = window.DATA, H = D.hamilton;
  var REPO = "https://github.com/DavidSchoenholz/UrbanResearch";
  var BR = {
    toronto: "claude/determined-lovelace-oc32xm",
    phase2: "claude/optimistic-fermat-c1mogk",
    hamilton: "claude/nice-davinci-kpvdwk"
  };
  function gh(branch, path) { return REPO + "/blob/" + branch + "/" + path; }
  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in (attrs || {})) e.setAttribute(k, attrs[k]);
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); }
  function fmt(n) { return Number(n).toLocaleString("en-US"); }
  function setHref(id, url) { var a = document.getElementById(id); if (a) a.href = url; }

  setHref("lnk-summary", gh(BR.toronto, "phase1/summary.md"));
  setHref("lnk-feas", gh(BR.toronto, "phase1/feasibility.md"));
  setHref("lnk-p2", gh(BR.phase2, "phase2/README.md"));
  setHref("lnk-ham-map", REPO + "/tree/" + BR.hamilton + "/hamilton/parcel_zoning/site");
  setHref("lnk-ham-readme", gh(BR.hamilton, "hamilton/parcel_zoning/README.md"));
  setHref("lnk-trreb", gh(BR.phase2, "trreb_marketwatch/README.md"));

  /* ---- data sources explorer ---- */
  var rows = D.inventory.slice(), sortKey = "id", sortDir = 1, open = {};
  var pubs = Array.from(new Set(rows.map(function (r) { return r.publisher; }))).sort();
  var pubSel = document.getElementById("pub");
  pubs.forEach(function (p) { pubSel.appendChild(el("option", {value: p}, esc(p.length > 60 ? p.slice(0, 57) + "…" : p))); });
  var tbody = document.querySelector("#inv tbody");
  function idNum(s) { var m = /(\d+)/.exec(s); return m ? +m[1] : 0; }
  function renderInv() {
    var q = document.getElementById("q").value.toLowerCase(), p = pubSel.value;
    var list = rows.filter(function (r) {
      return (!p || r.publisher === p) && (!q || Object.keys(r).some(function (k) { return String(r[k]).toLowerCase().indexOf(q) >= 0; }));
    });
    list.sort(function (a, b) {
      var x = sortKey === "id" ? idNum(a.id) : (a[sortKey] || "").toLowerCase();
      var y = sortKey === "id" ? idNum(b.id) : (b[sortKey] || "").toLowerCase();
      return (x < y ? -1 : x > y ? 1 : 0) * sortDir;
    });
    tbody.innerHTML = "";
    list.forEach(function (r) {
      var tr = el("tr", {"class": "row", tabindex: "0", "aria-expanded": open[r.id] ? "true" : "false"},
        "<td>" + esc(r.id) + "</td><td>" + esc(r.dataset) + "</td><td>" + esc(r.publisher) + "</td><td>" + esc(r.temporal_coverage) + "</td>");
      function toggle() { open[r.id] = !open[r.id]; renderInv(); }
      tr.addEventListener("click", toggle);
      tr.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
      tbody.appendChild(tr);
      if (open[r.id]) {
        var d = el("tr", {"class": "detail"});
        var td = el("td", {colspan: "4"});
        var dl = "<dl>";
        [["Limitations", "limitations"], ["Join keys", "join_keys"], ["Key fields", "key_fields"], ["Geography", "geographic_coverage"], ["Licence / access", "license_access"], ["Last updated", "last_updated"], ["Provenance", "provenance"]].forEach(function (f) {
          if (r[f[1]]) dl += "<dt>" + f[0] + "</dt><dd>" + esc(r[f[1]]) + "</dd>";
        });
        if (/^https?:/.test(r.url)) dl += '<dt>Source</dt><dd><a href="' + esc(r.url) + '" rel="noopener">' + esc(r.url) + "</a></dd>";
        td.innerHTML = dl + "</dl>";
        d.appendChild(td); tbody.appendChild(d);
      }
    });
    document.getElementById("count").textContent = list.length + " of " + rows.length + " sources";
  }
  document.getElementById("q").addEventListener("input", renderInv);
  pubSel.addEventListener("change", renderInv);
  Array.prototype.forEach.call(document.querySelectorAll("#inv th button"), function (b) {
    b.addEventListener("click", function () {
      var k = b.getAttribute("data-k");
      if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = 1; }
      renderInv();
    });
  });
  renderInv();

  /* ---- Hamilton ---- */
  var stats = [
    [fmt(H.n_parcel_polygons), "parcel polygons"],
    [fmt(H.n_parcels_without_zoning), "parcels without a zoning polygon"],
    [(H.share_split_zoned * 100).toFixed(1) + "%", "split-zoned (" + fmt(H.n_split_zoned) + " parcels)"],
    [fmt(H.n_pending_council_approved), "parcels with a council-approved change not yet final"]
  ];
  var hs = document.getElementById("hstats");
  stats.forEach(function (s) { hs.appendChild(el("div", {"class": "card stat"}, esc(s[0]) + "<small>" + esc(s[1]) + "</small>")); });
  var V = D.hamilton_validation;
  document.getElementById("hvalid").innerHTML = "<strong>Check against the City's live service:</strong> single-zone parcels " + V.single_zone.agree + " of " + V.single_zone.checked + " agree; split-zoned parcels " + V.split_zoned.agree + " of " + V.split_zoned.checked + " fall in our primary zone (the other " + (V.split_zoned.checked - V.split_zoned.agree) + " land in a secondary zone we already list, which is expected).";
  document.getElementById("susp").textContent = fmt(H.n_geometry_suspect);
  document.getElementById("asum").textContent = fmt(H.parcel_area_sum_km2);
  document.getElementById("aun").textContent = fmt(H.parcel_union_km2);

  function bars(id, obj, opts) {
    opts = opts || {};
    var host = document.getElementById(id);
    var entries = Object.keys(obj).filter(function (k) { return k !== "none"; }).map(function (k) { return [k, obj[k]]; });
    if (opts.limit) entries = entries.slice(0, opts.limit);
    var max = Math.max.apply(null, entries.map(function (e) { return e[1]; }));
    var total = H.n_parcel_polygons;
    entries.forEach(function (e, i) {
      var w = (e[1] / max * 52).toFixed(1) + "%";
      var row = el("div", {"class": "bar" + (opts.altFrom != null && i >= opts.altFrom ? " alt" : "")});
      row.innerHTML = '<div class="lab">' + esc(e[0]) + '</div><div class="track" style="--w:' + w + '"><div class="fill" style="width:' + w + '"></div><span class="val">' + fmt(e[1]) + " (" + (e[1] / total * 100).toFixed(1) + "%)</span></div>";
      host.appendChild(row);
    });
  }
  bars("c-bylaw", H.by_bylaw, {altFrom: 1});
  bars("c-cat", H.by_category);
  bars("c-code", H.top_zone_codes, {limit: 12});

  /* ---- ideas (from the README on the Phase 2 branch) ---- */
  var IDEAS = [
    ["Good first project", "Street-name demographics", "Who do streets honor (gender, race, era, colonial or Confederate figures), and how do renaming debates play out?", "OpenStreetMap street names plus public biographical records"],
    ["Good first project", "Who gets to sit down?", "How much public seating is there per capita and along walking routes, and how does it vary with age, disability, and income?", "OpenStreetMap, city asset inventories, a field audit"],
    ["Good first project", "Geography of waiting", "Where do people wait for buses, benefits, and clinics, and what do those spots offer (shelter, shade, seating, safety)?", "Transit stop data (GTFS), city facility lists, field observation"],
    ["Good first project", "Soundscape and gentrification", "How does what a neighborhood sounds like change as it changes (construction, vendors, bells, children)?", "311 noise complaints, public audio archives"],
    ["More idea", "Urban smell mapping", "Who lives with sewage, rendering plants, or cannabis odors, and who gets to complain?"],
    ["More idea", "Nighttime cities", "Lighting, night-shift transit access, and how safe the night feels by neighborhood."],
    ["More idea", "Death and the city", "Cemetery land use, cremation trends, and roadside memorials."],
    ["More idea", "Ghost infrastructure", "Unfinished highways, closed stations, and orphaned plazas. What predicts failure, and does reuse work?"],
    ["More idea", "Urban wildlife as a stakeholder", "Camera-trap and community-science data (iNaturalist) across income lines."],
    ["More idea", "Informal city in rich countries", "Unpermitted units, garage conversions, street vending, ad-hoc parking markets."],
    ["More idea", "Elevators and the vertical city", "Subway elevator outages and who is trapped when they fail."],
    ["More idea", "Loneliness geography", "Free places to be alone or together (libraries, plazas, laundromats) against indicators of isolation."],
    ["More idea", "Delivery-economy footprints", "How ghost kitchens, dark stores, and delivery bikes reshape curbs and commercial streets."],
    ["More idea", "Teenagers and the city", "Where 13-18-year-olds can legally hang out, and what happens when they cannot."],
    ["Housing & transit follow-up", "Transit access vs. home values", "Distance to stations against census-tract home values, using a new line as a natural experiment. Property-level sales data (TRREB) and bulk assessment data (MPAC) are licensed, so aggregates and census data are the realistic route."],
    ["Housing & transit follow-up", "Multiplex reform as a natural experiment", "Did permitting rules allowing multiplexes citywide change what gets built? Pairs naturally with the Phase 2 pipeline."],
    ["Housing & transit follow-up", "Downtown recovery", "Foot traffic across cities and what explains the differences."],
    ["Housing & transit follow-up", "Legacy of redlining", "Historical maps against today's health, wealth, and environmental burdens."],
    ["Housing & transit follow-up", "Heat-island equity", "Tree canopy and surface materials against heat-related ER visits, by income and race."]
  ];
  var ig = document.getElementById("ideas-grid"), isel = document.getElementById("ifilter");
  function renderIdeas() {
    var f = isel.value.replace("&amp;", "&");
    ig.innerHTML = "";
    IDEAS.filter(function (i) { return !f || i[0] === f; }).forEach(function (i) {
      ig.appendChild(el("div", {"class": "card"}, '<span class="badge">' + esc(i[0]) + "</span><h3>" + esc(i[1]) + "</h3><p>" + esc(i[2]) + "</p>" + (i[3] ? '<p class="sans" style="font-size:14px;color:var(--mut)"><strong>Likely data (unverified):</strong> ' + esc(i[3]) + "</p>" : "")));
    });
  }
  isel.addEventListener("change", renderIdeas);
  renderIdeas();

  /* ---- provenance ---- */
  var P = [
    ["Toronto feasibility; data sources", BR.toronto, "phase1/summary.md, phase1/feasibility.md, phase1/inventory.csv", D.snapshot.toronto],
    ["Phase 2 pipeline; ideas; TRREB price map", BR.phase2, "README.md, phase2/README.md, trreb_marketwatch/README.md", D.snapshot.phase2],
    ["Hamilton parcel zoning", BR.hamilton, "hamilton/README.md, hamilton/parcel_zoning/README.md, hamilton/parcel_zoning/output/summary.json, validation.json", D.snapshot.hamilton]
  ];
  var pv = document.getElementById("prov");
  P.forEach(function (p) {
    pv.appendChild(el("tr", {}, "<td>" + esc(p[0]) + '</td><td><a href="' + REPO + "/tree/" + p[1] + '">' + esc(p[1]) + "</a></td><td>" + esc(p[2]) + "</td><td><code>" + esc(p[3]) + "</code></td>"));
  });
})();
