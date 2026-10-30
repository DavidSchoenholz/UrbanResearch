// Hamilton parcel zoning map. Data files are built by scripts/build_map.py.
// Zoomed out: zoning polygons (data/zoning.json). Zoomed in (PARCEL_ZOOM+): parcels, loaded per ward.
(async function () {
  const PARCEL_ZOOM = 15;
  const BYLAW_05_200_URL = "https://www.hamilton.ca/build-invest-grow/planning-development/zoning/zoning-by-law-05-200";
  const FORMER_URL = "https://www.hamilton.ca/build-invest-grow/planning-development/zoning/zoning-by-laws-former-communities";

  const css = getComputedStyle(document.documentElement);
  const v = (name) => css.getPropertyValue(name).trim();
  const fmt = (n) => Number(n).toLocaleString("en-CA");
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const meta = await (await fetch("data/meta.json")).json();
  const F = meta.flags;
  document.getElementById("asof").textContent = meta.downloaded_at.slice(0, 10);

  const state = { mode: "category", flag: 1, hidden: new Set() };
  const isDark = () => matchMedia("(prefers-color-scheme: dark)").matches;

  const map = L.map("map", { preferCanvas: true, minZoom: 9, maxZoom: 20 }).setView([43.235, -79.87], 11);
  // Esri Gray Canvas basemap: no API key needed (CARTO tiles now require one). Native tiles stop at z16.
  const canvas = isDark() ? "World_Dark_Gray_Base" : "World_Light_Gray_Base";
  L.tileLayer(`https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/${canvas}/MapServer/tile/{z}/{y}/{x}`, {
    maxZoom: 20, maxNativeZoom: 16,
    attribution: "Basemap &copy; Esri, HERE, Garmin, &copy; OpenStreetMap contributors | Zoning &amp; parcels: City of Hamilton",
  }).addTo(map);
  const renderer = L.canvas({ padding: 0.3 });

  // ---- colour rules -------------------------------------------------------
  const catColor = (c) => v(`--c${c}`);
  const bylawClass = (b) => (b === 0 ? 0 : 1); // bylaws[0] is 05-200 (build_map sorts it first)
  function legendItems() {
    if (state.mode === "category") {
      return meta.categories.map((name, i) => ({ key: i, name, color: catColor(i), n: meta.stats.by_category[name] || 0 }));
    }
    if (state.mode === "bylaw") {
      const by = meta.stats.by_bylaw;
      const former = Object.entries(by).filter(([k]) => k !== "05-200" && k !== "none").reduce((s, [, n]) => s + n, 0);
      return [
        { key: 0, name: "Zoning By-law 05-200 (city-wide)", color: v("--by0"), n: by["05-200"] || 0 },
        { key: 1, name: "Former municipality by-law", color: v("--by1"), n: former },
      ];
    }
    return [
      { key: 1, name: document.querySelector(`#flag option[value="${state.flag}"]`).textContent, color: v("--hi"), n: null },
      { key: 0, name: "Other parcels", color: v("--muted-fill"), n: null },
    ];
  }
  function classOf(c, b, f) {
    if (state.mode === "category") return c;
    if (state.mode === "bylaw") return bylawClass(b);
    return f & state.flag ? 1 : 0;
  }
  function colorOf(cls) {
    if (state.mode === "category") return catColor(cls);
    if (state.mode === "bylaw") return v(cls === 0 ? "--by0" : "--by1");
    return cls ? v("--hi") : v("--muted-fill");
  }

  // ---- zoning polygons (zoomed out) --------------------------------------
  const zoning = await (await fetch("data/zoning.json")).json();
  const zoningLayer = L.geoJSON(zoning, {
    renderer,
    style: (f) => zoneStyle(f.properties),
    onEachFeature: (f, layer) => layer.on("click", (e) => {
      const p = f.properties;
      L.popup().setLatLng(e.latlng).setContent(
        `<div class="pop"><h3>${esc(p.zc || "No zone")}</h3><table>
         <tr><td>Category</td><td>${esc(meta.categories[p.c])}</td></tr>
         <tr><td>Governing by-law</td><td>${esc(meta.bylaws[p.b] ?? "Unknown")}</td></tr></table>
         <p class="note">Zoom in to see individual parcels.</p></div>`).openOn(map);
    }),
  });
  function zoneStyle(p) {
    // Conditions are parcel attributes, so the zoomed-out view stays neutral in that mode.
    const cls = state.mode === "flag" ? 0 : classOf(p.c, p.b, 0);
    const hidden = state.hidden.has(cls);
    return { stroke: false, fillColor: colorOf(cls), fillOpacity: hidden ? 0 : 0.55 };
  }

  // ---- parcels (zoomed in, per ward) -------------------------------------
  const wards = await (await fetch("data/wards.json")).json();
  const wardBounds = wards.features.map((f) => ({ ward: Number(f.properties.WARD), bounds: L.geoJSON(f).getBounds() }));
  const parcelLayers = new Map(); // ward -> L.GeoJSON
  const loading = new Map();
  const byRoll = new Map(); // roll -> layer, for search

  function parcelStyle(p) {
    const z = meta.zones[p.k] || [null, null, 10, null];
    const cls = classOf(z[2], z[3], p.f);
    const hidden = state.hidden.has(cls);
    return { color: v("--panel"), weight: 0.6, fillColor: colorOf(cls), fillOpacity: hidden ? 0.04 : 0.78, opacity: hidden ? 0.2 : 0.9 };
  }

  function popupHtml(p) {
    const z = meta.zones[p.k] || [];
    const bylaw = meta.bylaws[z[3]];
    const tags = Object.entries({
      "Split-zoned": F.split_zoned, "Exception": F.has_exception, "Holding (H)": F.has_holding,
      "Temporary use": F.has_temporary_use, "OLT/OMB case": F.under_olt_appeal_tag, "Change pending": F.pending,
      "Interim control": F.in_interim_control, "Compliance review area": F.in_compliance_review_area,
      "H-converted dwelling": F.h_converted_dwelling, "Shape doubtful": F.geometry_suspect,
    }).filter(([, bit]) => p.f & bit).map(([t]) => `<span class="tag">${t}</span>`).join("");
    const rows = [
      ["Zone", `<b>${esc(p.z)}</b>${z[1] ? `<br>${esc(z[1])}` : ""}`],
      ["Category", esc(meta.categories[z[2]] ?? "")],
      ["Governing by-law", `<a href="${bylaw === "05-200" ? BYLAW_05_200_URL : FORMER_URL}" target="_blank" rel="noopener">${esc(bylaw ?? "Unknown")}</a>`],
    ];
    if (p.y) rows.push(["Amending by-law", esc(p.y)]);
    if (p.s != null) rows.push(["All zones", `${esc(p.o)}<br><small>primary zone covers ${p.s}% of the parcel</small>`]);
    if (p.l) rows.push(["OLT/OMB case", esc(p.l)]);
    if (p.p) rows.push(["Pending change", esc(p.p)]);
    rows.push(["Roll number", esc(p.r) + (p.n > 1 ? `<br><small>${p.n} rolls share this footprint (e.g. condo units)</small>` : "")]);
    rows.push(["Parcel area", `${fmt(p.m)} m²`]);
    return `<div class="pop"><h3>${esc(p.a || "No address")}</h3><table>${rows.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join("")}</table>${tags ? `<div>${tags}</div>` : ""}</div>`;
  }

  function loadWard(ward) {
    if (parcelLayers.has(ward)) return Promise.resolve(parcelLayers.get(ward));
    if (loading.has(ward)) return loading.get(ward);
    const pr = fetch(`data/parcels/ward-${ward}.json`).then((r) => r.json()).then((geo) => {
      const layer = L.geoJSON(geo, {
        renderer,
        style: (f) => parcelStyle(f.properties),
        onEachFeature: (f, l) => { l.bindPopup(() => popupHtml(f.properties)); byRoll.set(f.properties.r, l); },
      });
      parcelLayers.set(ward, layer);
      if (map.getZoom() >= PARCEL_ZOOM) layer.addTo(map);
      return layer;
    });
    loading.set(ward, pr);
    return pr;
  }

  const hint = document.getElementById("hint");
  function refreshView() {
    const zoomedIn = map.getZoom() >= PARCEL_ZOOM;
    hint.hidden = zoomedIn;
    if (zoomedIn) {
      map.removeLayer(zoningLayer);
      const view = map.getBounds();
      wardBounds.filter((w) => w.bounds.intersects(view)).forEach((w) => loadWard(w.ward));
      parcelLayers.forEach((l) => { if (!map.hasLayer(l)) l.addTo(map); });
    } else {
      parcelLayers.forEach((l) => map.removeLayer(l));
      if (!map.hasLayer(zoningLayer)) zoningLayer.addTo(map);
    }
  }
  map.on("moveend", refreshView);
  refreshView();

  // ---- legend and controls -----------------------------------------------
  const legend = document.getElementById("legend");
  function drawLegend() {
    document.getElementById("legend-title").textContent =
      { category: "Zone category", bylaw: "Governing by-law", flag: "Special condition" }[state.mode];
    legend.innerHTML = legendItems().map((it) =>
      `<button type="button" data-key="${it.key}" aria-pressed="${!state.hidden.has(it.key)}">
         <span class="sw" style="background:${it.color}"></span><span>${esc(it.name)}</span>
         <span class="n">${it.n == null ? "" : fmt(it.n)}</span></button>`).join("");
    document.getElementById("legend-note").hidden = state.mode === "flag";
  }
  legend.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const k = Number(b.dataset.key);
    state.hidden.has(k) ? state.hidden.delete(k) : state.hidden.add(k);
    restyle();
  });
  function restyle() {
    zoningLayer.setStyle((f) => zoneStyle(f.properties));
    parcelLayers.forEach((l) => l.setStyle((f) => parcelStyle(f.properties)));
    drawLegend();
  }
  const modeSel = document.getElementById("mode");
  const flagSel = document.getElementById("flag");
  modeSel.addEventListener("change", () => {
    state.mode = modeSel.value; state.hidden.clear();
    document.getElementById("flagwrap").hidden = state.mode !== "flag";
    if (state.mode === "flag" && map.getZoom() < PARCEL_ZOOM) hint.textContent = "Conditions are shown on parcels: zoom in";
    else hint.textContent = "Zoom in to see individual parcels";
    restyle();
  });
  flagSel.addEventListener("change", () => { state.flag = Number(flagSel.value); restyle(); });
  drawLegend();

  // ---- search ---------------------------------------------------------------
  // data/search.json rows: [address, roll, ward, lat, lon, roll of the map feature or 0 if the same]. Loaded on first use (it is large).
  let index = null;
  const q = document.getElementById("q");
  const results = document.getElementById("results");
  async function getIndex() {
    if (!index) index = (await (await fetch("data/search.json")).json()).map((r) => [r[0].toUpperCase(), ...r]);
    return index;
  }
  q.addEventListener("focus", getIndex, { once: true });
  let timer;
  q.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const term = q.value.trim().toUpperCase().replace(/\s+/g, " ");
      if (term.length < 3) { results.innerHTML = ""; return; }
      const idx = await getIndex();
      // Addresses that start with the term first (so "75 BALSAM" finds 75 before 175), then any
      // other match; one entry per roll (a few rolls have several parcel polygons).
      const starts = [], contains = [], seen = new Set();
      for (const row of idx) {
        if (seen.has(row[2])) continue;
        if (row[0].startsWith(term) || row[2].startsWith(term)) { starts.push(row); seen.add(row[2]); }
        else if (contains.length < 12 && row[0].includes(term)) { contains.push(row); seen.add(row[2]); }
        if (starts.length >= 12) break;
      }
      const hits = starts.concat(contains).slice(0, 12);
      results.innerHTML = hits.map((h, i) =>
        `<li role="option" data-i="${i}">${esc(h[1])}<br><small>Roll ${esc(h[2])} · Ward ${h[3]}</small></li>`).join("")
        || `<li><small>No match</small></li>`;
      results._hits = hits;
    }, 150);
  });
  results.addEventListener("click", async (e) => {
    const li = e.target.closest("li[data-i]");
    if (!li) return;
    const [, addr, roll, ward, lat, lon, featureRoll] = results._hits[Number(li.dataset.i)];
    results.innerHTML = ""; q.value = addr;
    map.setView([lat, lon], 18);
    await loadWard(ward);
    const layer = byRoll.get(featureRoll || roll);
    if (layer) layer.openPopup([lat, lon]);
    else L.popup().setLatLng([lat, lon]).setContent(esc(addr)).openOn(map);
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".search")) results.innerHTML = ""; });
})();
