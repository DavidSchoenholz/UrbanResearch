// Verification for the overview site. Run from the repository root after `git fetch origin`:
//   node docs/checks/check_site.js
// 1. Figures: every number visible on each page must appear in that page's source files
//    (read with `git show` at the pinned commits). Elements marked data-nocheck are skipped.
// 2. Links: relative hrefs/srcs must exist, #anchors must resolve, GitHub links must point at a
//    pinned commit and a path that exists there.
// 3. Clicks: search/sort/filter, row details, accordions, idea filters, chart toggle, tooltips.
// 4. Console: no errors or warnings on any page.
const path = require("path");
const fs = require("fs");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright");

const DOCS = path.resolve(__dirname, "..");
const ROOT = path.resolve(DOCS, "..");
const data = JSON.parse(fs.readFileSync(path.join(DOCS, "data", "site-data.json"), "utf8"));
const SRC = data.snapshot.sources;
const show = (key, p) => execFileSync("git", ["show", `${SRC[key].sha}:${p}`], { cwd: ROOT, encoding: "utf8", maxBuffer: 1 << 26 });

const FILES = {
  phase1: ["phase1/summary.md", "phase1/feasibility.md", "phase1/inventory.csv"],
  phase2: ["README.md", "phase2/README.md", "phase2/AUDIT_LOG.md", "phase2/pipeline/config.py"],
  hamilton: ["hamilton/parcel_zoning/output/summary.json", "hamilton/parcel_zoning/output/validation.json",
    "hamilton/parcel_zoning/README.md", "hamilton/parcel_zoning/scripts/build_parcel_zoning.py"],
};
const corpus = {};
for (const [k, files] of Object.entries(FILES)) {
  // Drop thousands separators so "177,753" and 177753 compare equal.
  corpus[k] = files.map((f) => show(k, f)).join("\n").replace(/(\d),(?=\d{3}\b)/g, "$1");
}
corpus.all = Object.values(corpus).join("\n");
const PAGES = {
  index: ["all"], toronto: ["phase1"], sources: ["phase1"], pipeline: ["phase2"],
  hamilton: ["hamilton"], ideas: ["phase2"], glossary: ["all"], about: ["all"],
};
// Numbers that are site furniture rather than figures: list positions, step numbers, counts of
// items on this site, and the commit-SHA fragments. Each is checked to occur only in these roles.
const FURNITURE = new Set(["1", "2", "3", "4", "5", "6", "7", "8", "15", "30"]);

// Figures the brief names explicitly; each must appear on the given page.
const REQUIRED = {
  index: ["177,753"],
  toronto: ["16,292", "16,296", "2022", "GO WITH LIMITS", "UNVERIFIED", "upper bounds", "only partly recoverable"],
  sources: ["Showing 30 of 30 sources"],
  hamilton: ["177,753", "4.2%", "2\nparcels with no zoning polygon", "Unexplained in the source", "1,745.155", "1,073.533", "571"],
  pipeline: ["synthetic"],
  ideas: ["still need to be verified"],
};

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function found(token, keys) {
  const t = token.replace(/,/g, "").replace(/%$/, "");
  const forms = [t];
  // "95%" may be written as the share 0.95 in the source.
  if (token.endsWith("%")) forms.push(String(Number(t) / 100));
  return forms.some((f) => {
    const re = new RegExp(`(?<![\\d.])${escapeRe(f)}(?![\\d])`);
    return keys.some((k) => re.test(corpus[k]));
  });
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const results = { figures: [], links: [], clicks: [], console: [] };
  let figureCount = 0, skipped = 0, external = 0;
  const idsByPage = {};
  const linksByPage = {};

  for (const [name, keys] of Object.entries(PAGES)) {
    const page = await ctx.newPage();
    page.on("console", (m) => { if (["error", "warning"].includes(m.type())) results.console.push(`${name}: ${m.text()}`); });
    page.on("pageerror", (e) => results.console.push(`${name}: ${e}`));
    await page.goto("file://" + path.join(DOCS, name + ".html"));
    await page.waitForTimeout(100);
    // Open every <details> and every hidden chart row so their text is checked too.
    await page.evaluate(() => {
      document.querySelectorAll("details").forEach((d) => (d.open = true));
      document.querySelectorAll("tr[hidden]").forEach((t) => (t.hidden = false));
    });
    const info = await page.evaluate(() => {
      const clone = document.body.cloneNode(true);
      const skipped = clone.querySelectorAll("[data-nocheck], script").length;
      clone.querySelectorAll("[data-nocheck], script").forEach((n) => n.remove());
      document.body.appendChild(clone);
      clone.style.position = "absolute";
      const text = clone.innerText;
      clone.remove();
      return {
        text, skipped, fullText: document.body.innerText,
        ids: [...document.querySelectorAll("[id]")].map((e) => e.id),
        links: [...document.querySelectorAll("a[href], link[href], script[src]")].map((e) => e.getAttribute("href") || e.getAttribute("src")),
      };
    });
    skipped += info.skipped;
    idsByPage[name + ".html"] = new Set(info.ids);
    linksByPage[name] = info.links;

    // Figures. Remove commit SHAs, branch names and file paths first: they are identifiers.
    let text = info.text
      .replace(/\b[0-9a-f]{7,40}\b/g, " ")
      .replace(/claude\/[a-z-]+[0-9a-z]*/g, " ")
      .replace(/\b[\w./-]+\.(md|csv|json|py|js|html)\b/g, " ");
    // Dates and dotted table ids (e.g. 1.1.2.11) are checked whole.
    const tokens = text.match(/\d{4}-\d{2}(?:-\d{2})?(?!\d)|\d+(?:\.\d+){2,}|\d[\d,]*(?:\.\d+)?%?/g) || [];
    for (const tok of tokens) {
      figureCount++;
      if (FURNITURE.has(tok)) continue;
      if (/^\d{4}-\d{2}/.test(tok)) {
        if (!found(tok, keys)) results.figures.push(`${name}: date ${tok} not in sources`);
        continue;
      }
      if (!found(tok, keys)) results.figures.push(`${name}: ${tok} not in sources`);
    }
    for (const req of REQUIRED[name] || []) {
      if (!info.fullText.includes(req)) results.figures.push(`${name}: required text "${req.replace("\n", "\\n")}" missing`);
    }
    await page.close();
  }

  // Links.
  for (const [name, links] of Object.entries(linksByPage)) {
    for (const href of links) {
      if (/^https:\/\/github\.com\/DavidSchoenholz\/UrbanResearch\/(blob|tree)\//.test(href)) {
        const rest = href.replace(/^.*?\/(blob|tree)\//, "");
        const br = Object.values(SRC).find((s) => rest === s.branch || rest.startsWith(s.branch + "/"));
        const ref = br ? br.branch : rest.split("/")[0];
        const p = br ? rest.slice(br.branch.length + 1) : rest.split("/").slice(1).join("/");
        const sha = Object.values(SRC).find((s) => s.sha === ref || s.branch === ref);
        if (!sha && !/^[0-9a-f]{40}$/.test(ref)) { results.links.push(`${name}: GitHub link to unknown ref ${href}`); continue; }
        const rev = /^[0-9a-f]{40}$/.test(ref) ? ref : `origin/${ref}`;
        try { execFileSync("git", ["cat-file", "-e", `${rev}:${p || ""}`], { cwd: ROOT, stdio: "ignore" }); }
        catch { results.links.push(`${name}: ${href} does not exist at that commit`); }
        continue;
      }
      if (/^(https?:|mailto:)/.test(href)) { external++; continue; }
      const [file, hash] = href.split("#");
      const target = file || name + ".html";
      if (!fs.existsSync(path.join(DOCS, target))) { results.links.push(`${name}: missing file ${href}`); continue; }
      if (hash && target.endsWith(".html")) {
        const ids = idsByPage[target];
        if (!ids || !ids.has(hash)) results.links.push(`${name}: anchor ${href} not found`);
      }
    }
  }

  // Clicks.
  const page = await ctx.newPage();
  page.on("pageerror", (e) => results.console.push(`click-test: ${e}`));
  const check = (ok, msg) => { if (!ok) results.clicks.push(msg); };
  const url = (n) => "file://" + path.join(DOCS, n + ".html");

  await page.goto(url("sources"));
  const rowCount = () => page.locator("#rows > tr:not(.detail)").count();
  check(await rowCount() === 30, "sources: expected 30 rows");
  await page.fill("#q", "census tract");
  const nSearch = await rowCount();
  check(nSearch > 0 && nSearch < 30, `sources: search gave ${nSearch} rows`);
  check((await page.textContent("#count")).includes(`Showing ${nSearch} of 30`), "sources: count text not updated");
  await page.click("#reset");
  await page.selectOption("#f-pub", "Canada Mortgage and Housing Corporation");
  const nPub = await rowCount();
  const expectedPub = data.inventory.filter((r) => r.publisher_org === "Canada Mortgage and Housing Corporation").length;
  check(nPub === expectedPub, `sources: publisher filter ${nPub} vs ${expectedPub}`);
  await page.click("#reset");
  await page.selectOption("#f-prov", "Not fully verified");
  const nProv = await rowCount();
  check(nProv === data.inventory.filter((r) => r.provenance_group === "Not fully verified").length, "sources: provenance filter wrong");
  await page.click("#reset");
  await page.click('button[data-sort="dataset"]');
  await page.click('button[data-sort="dataset"]');
  const firstDesc = await page.locator("#rows > tr:not(.detail) th").first().textContent();
  const sortedDesc = data.inventory.map((r) => r.dataset).sort((a, b) => b.localeCompare(a, "en", { numeric: true }))[0];
  check(firstDesc === sortedDesc, `sources: descending sort put "${firstDesc}" first`);
  check(await page.getAttribute('th:has(button[data-sort="dataset"])', "aria-sort") === "descending", "sources: aria-sort not updated");
  await page.click("#reset");
  await page.click('[aria-controls="d-D21"]');
  check(await page.locator("#d-D21").isVisible(), "sources: details row did not open");
  check((await page.textContent("#d-D21")).includes("Archived after 2022"), "sources: details text wrong");
  check(await page.evaluate(() => document.activeElement.getAttribute("aria-controls")) === "d-D21", "sources: focus lost after toggle");
  await page.keyboard.press("Enter");
  check(await page.locator("#d-D21").count() === 0, "sources: keyboard Enter did not close details");

  await page.goto(url("toronto"));
  const acc = page.locator("#limit-4 > summary");
  await acc.focus();
  await page.keyboard.press("Enter");
  check(await page.evaluate(() => document.getElementById("limit-4").open), "toronto: accordion did not open with keyboard");
  check((await page.textContent("#limit-4")).includes("22–62%"), "toronto: accordion body missing source text");
  check(await page.locator("#limitations details").count() === 8, "toronto: expected 8 limitations");
  await page.focus("a.term[data-term='census-tract']");
  check(await page.locator(".tip").isVisible(), "toronto: glossary tooltip did not show on focus");
  await page.keyboard.press("Escape");
  check(await page.locator(".tip").count() === 0, "toronto: Escape did not close tooltip");

  await page.goto(url("ideas"));
  const total = data.ideas.groups.reduce((n, g) => n + g.items.length, 0);
  check((await page.textContent("#count")).includes(`Showing ${total} ideas`), "ideas: initial count wrong");
  for (const g of data.ideas.groups) {
    await page.click(`#filters button[data-key="${g.key}"]`);
    check((await page.textContent("#count")).includes(`Showing ${g.items.length} ideas`), `ideas: filter ${g.key} count wrong`);
    check(await page.locator(".idea-group:not([hidden])").count() === 1, `ideas: filter ${g.key} shows other groups`);
    check(await page.getAttribute(`#filters button[data-key="${g.key}"]`, "aria-pressed") === "true", `ideas: aria-pressed not set for ${g.key}`);
  }

  await page.goto(url("hamilton"));
  const visibleCodes = () => page.locator("#c3 tbody tr:not([hidden])").count();
  check(await visibleCodes() === 15, "hamilton: expected 15 zone codes initially");
  await page.click("#c3-more");
  check(await visibleCodes() === 30, "hamilton: Show all 30 did not reveal 30 rows");
  await page.click("#c3-more");
  check(await visibleCodes() === 15, "hamilton: toggle back failed");

  await page.goto(url("glossary") + "#mzo");
  check(await page.locator("dt#mzo").isVisible(), "glossary: #mzo anchor missing");

  await browser.close();

  console.log(`Figures: ${figureCount} numeric tokens checked across ${Object.keys(PAGES).length} pages (${skipped} decorative elements skipped). ${results.figures.length ? "PROBLEMS:" : "All found in their source files."}`);
  results.figures.forEach((m) => console.log("  - " + m));
  console.log(`Links: ${Object.values(linksByPage).flat().length} links checked (${external} external non-GitHub links not fetched). ${results.links.length ? "PROBLEMS:" : "All resolve."}`);
  results.links.forEach((m) => console.log("  - " + m));
  console.log(`Clicks: ${results.clicks.length ? "PROBLEMS:" : "search, filters, sort, row details, accordions, idea filters, chart toggle, tooltips all behave."}`);
  results.clicks.forEach((m) => console.log("  - " + m));
  console.log(`Console: ${results.console.length ? "PROBLEMS:" : "no errors or warnings."}`);
  results.console.forEach((m) => console.log("  - " + m));
  const bad = results.figures.length + results.links.length + results.clicks.length + results.console.length;
  process.exit(bad ? 1 : 0);
})();
