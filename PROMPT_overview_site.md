# Prompt: build a reader-friendly overview of UrbanResearch

Paste everything below the line into a fresh session with the repo `DavidSchoenholz/UrbanResearch` attached.

---

## Role and goal

You are building a **visual, reader-friendly overview** of an urban-research repository for a non-technical reader (the repo owner, plus anyone they share it with). Today the repo's front page shows only a two-line README, and the real work is spread across three unmerged branches. The reader should be able to open one page and understand in five minutes: what has been done, what was found, how solid it is, and what could come next.

You are a presenter, not a researcher. You are **not** producing new findings.

## Where the content lives (read all of it first)

`main` contains only `README.md`. Read the other branches with `git fetch origin` then `git show origin/<branch>:<path>`. Do **not** merge, rebase, or modify those branches.

| Branch | Work | Files to read |
|---|---|---|
| `claude/determined-lovelace-oc32xm` | **Phase 1: Toronto feasibility study.** Verdict "GO WITH LIMITS" on studying how zoning relates to housing completions. | `phase1/summary.md` (start here), `phase1/feasibility.md`, `phase1/inventory.csv` (30 data sources, columns: id, dataset, url, publisher, license_access, geographic_coverage, temporal_coverage, last_updated, key_fields, limitations, join_keys, provenance, evidence_url) |
| `claude/optimistic-fermat-c1mogk` | **Phase 2: analysis code skeleton**, plus the "Ideas to try next" list. Tested on synthetic data only. | `README.md` (ideas tables), `phase2/README.md`, `phase2/AUDIT_LOG.md` |
| `claude/nice-davinci-kpvdwk` | **Hamilton parcel-to-zoning match.** | `hamilton/parcel_zoning/output/summary.json`, `hamilton/parcel_zoning/scripts/*.py` (to understand what the numbers mean). The two `.csv.gz` files are 2-4 MB; do not embed them. |

## Deliverable

A **static website with no build step**, in a new `docs/` folder, on the branch you are told to develop on (it should start from `main`, so the site does not depend on the unmerged work branches; do not push elsewhere). Plain HTML, CSS and a little vanilla JS, so it can be served by GitHub Pages ("deploy from branch, /docs") and also opened by double-clicking `docs/index.html`. Keep all data in local files; no network calls at runtime; if you use a library (e.g. a chart library), vendor a pinned copy into `docs/vendor/`.

Suggested structure (adjust if the content argues otherwise):

1. **Home / "Where things stand"**: one screen. Three project cards (Toronto feasibility, Phase 2 pipeline, Hamilton zoning), each with a plain-language one-liner and an honest **status badge** (see below). Below them, a short "what to read first" pointer.
2. **Toronto feasibility**: the GO WITH LIMITS verdict up top, then the eight key limitations as scannable cards or an accordion (one headline sentence each, detail on expand). Include the recommended study frame (period, unit of analysis) and the "still unverified" list, clearly separated from verified facts.
3. **Data sources explorer**: the 30 rows of `inventory.csv` as a searchable, sortable, filterable table (filter by publisher / geography / coverage years if the data supports it; do not invent categories the CSV lacks). Row expands to show limitations, join keys and a link to the source URL.
4. **Phase 2 pipeline**: a simple diagram of zoning -> application -> permit -> completion with each pipeline module mapped to its step; the key design decisions in plain English; the known limitations; what is blocked on real data.
5. **Hamilton zoning**: charts from `summary.json` (e.g. parcels by by-law, by zone category, top zone codes, share split across zones) with a one-line plain-language takeaway per chart, and a "how to read this / caveats" note.
6. **Ideas to try next**: the idea tables as filterable cards (first projects vs. more ideas vs. housing/transit follow-ups), keeping the "data sources are suggestions and still need verification" caveat visible.
7. **About / provenance**: for each page section, which branch and file it came from, with links to GitHub; date of the snapshot (record the commit SHAs you read).

## Non-negotiable accuracy rules

- **Every number and claim must trace to a file above.** Copy figures exactly (e.g. 177,753 parcel polygons; 2 without zoning; 4.2% split-zoned; 30 sources; census-tract completions end in 2022; 16,292 vs 16,296 reconciliation). If you restate a finding in plainer words, keep its qualifiers ("upper bounds", "only partly recoverable", "UNVERIFIED").
- **Do not upgrade confidence.** Phase 1 is a feasibility study, not a finding about Toronto's housing. Phase 2 has run only on synthetic data and says nothing about Toronto. Hamilton is a spatial-match result, not a policy conclusion. Say so on the page, near the relevant content, not only in a footer.
- Items marked UNVERIFIED in the source (e.g. Bill 23 / Bill 185 royal-assent dates, multiplex and garden-suite in-force dates, StatCan fields) must remain visibly marked as unverified.
- If a number in `summary.json` is not explained anywhere (for example parcel area summing to 1,745 km² versus a union of 1,074 km², or 571 duplicate property numbers), either present it with a neutral "unexplained in the source" note or leave it out. Do not invent an explanation. Read the Hamilton scripts to see whether one exists, and cite it if so.
- **Status badges must be honest.** Suggested vocabulary: *Study complete (with limits)*, *Code only, synthetic data*, *Output produced, not yet interpreted*, *Idea, unverified*. Pick the ones that fit; do not use "Done" or "Validated".
- No stock-photo filler, no invented quotes, no fabricated charts or trends. If the data does not support a visual, use a table.

## Design guidance

- Reader is smart but not a programmer or planner. Plain language first, jargon (e.g. "Aalen-Johansen", "OLT", "CMHC", "MZO", "holding provision") explained on first use via a glossary tooltip or short inline definition; add a small glossary section.
- Layered detail: headline -> summary -> expand for the full reasoning. Never dump `feasibility.md` as a wall of text; link to the full source file on GitHub for those who want it.
- Works on a phone (no horizontal page scroll; tables scroll inside their own container), supports light and dark mode (`prefers-color-scheme`), accessible contrast, keyboard-navigable, semantic headings, alt text or text equivalents for every chart.
- Charts: direct labels where possible, one clear takeaway title per chart, colorblind-safe palette, no 3D, no dual axes. Use the `dataviz` and `artifact-design` skills if available.
- Restrained, editorial visual style (strong typography, generous whitespace). Avoid generic dashboard clutter.

## How to work

1. Read all source files listed above before designing anything. Write a short content map (section -> source file -> key facts) in your scratchpad, not in the repo.
2. Generate page data from the sources with a small script (e.g. `docs/data/*.json` from `inventory.csv` and `summary.json`) so figures are copied, not retyped. Keep the script at `docs/build_data.py` and note in the About section how to re-run it.
3. Build the pages. Keep files small and readable; no frameworks unless there is a clear reason.
4. In `README.md` on your working branch (the version inherited from `main`), add a short "Start here" section linking to the site (or to `docs/index.html`), with one-line summaries of the three projects and the branch each lives on. Leave the existing text intact.

## Verification (do all of these before saying you are done)

- Open the site in headless Chromium (Playwright is preinstalled) at 390px and 1280px widths in both light and dark mode. Take screenshots and actually look at them. Check no horizontal scroll, no clipped text, no unreadable chart labels.
- Write and run a script that checks every figure shown on the page against its source file, and a link checker for internal links and relative paths. Report the result.
- Click-test: table search/sort/filter, accordions, and any tabs, in the browser. Confirm there are no console errors.
- **Self-audit as a skeptical reviewer**: for each of the three projects, reread the source summary and then your page, and list anything your page overstates, omits that matters (especially caveats), or phrases more strongly than the source. Fix them and note what you changed.

## Git

Commit in logical steps with clear messages and push to the designated branch with `git push -u origin <branch>`. **Do not open a pull request** unless asked. At the end, report: what was built, how to view it (the exact path/URL steps, including enabling GitHub Pages if wanted), the commit SHAs of the source branches you read, the verification results, and anything you could not verify or chose to leave out.
