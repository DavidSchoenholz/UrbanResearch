# Hamilton research log

A dated record of what was done, what was found and why each decision was made, so the work can be
picked up later without redoing it. Newest session at the top. Add a new dated section each session.

---

## Resume here (state as of 2026-10-30)

- **Branch:** `claude/nice-davinci-kpvdwk` (made from `main`, which only had the initial commit).
- **Done:** Phase 1 for Hamilton (`phase1/`), parcel zoning table, validation and web map
  (`parcel_zoning/`).
- **Data date:** all City layers downloaded 2026-10-30 (`parcel_zoning/output/summary.json` →
  `source_manifest`). The raw download is committed gzip-compressed in `parcel_zoning/raw/`
  (39 MB); `python scripts/fetch.py` replaces it with a fresh download in ~2 minutes.
- **To refresh the map with newer City data:** run the four scripts in `parcel_zoning/README.md`
  ("Rebuild"), check that `validation.json` still shows 300/300 for single-zone parcels, and commit
  the outputs with the new date.
- **Open questions** (also in `phase1/summary.md`, "Must-verify checklist"):
  1. Licence wording on open.hamilton.ca (blocked here by Cloudflare).
  2. A machine-readable building-permit source (City extract, or check the third-party compilation).
  3. Meaning of `OLT_CASE_NO` and the live status of case 24-000544.
  4. Whether By-law 26-178 (pending on 4,217 parcels) is the mid-rise expansion; whether ICBL 22-258 is still in force.
  5. Units of `FRONTAGE`/`DEPTH`; confirm the `UNIT_OF_MEASURE` decoding with the City.
- **Suggested next steps:**
  1. Join Committee of Adjustment records (by `ROLL_NUMBER`) and development applications (point in
     parcel) to the parcel table; tabulate variance and rezoning activity by zone and by governing by-law.
  2. Code unit permissions for the 05-200 residential zones (R1-R4a) from the by-law text, to get a
     zoned-capacity measure (the layer has no FSI or height fields).
  3. Use the 2022-08-12 (22-197) and 2024-04-10 (24-051) residential markers with parcels still under
     former by-laws as a comparison group.
  4. Add a "pending change" view to the map once 26-178 is final, by re-running the scripts.

---

## 2026-10-30: Phase 1 and parcel zoning map

### Request
"Do very similar to phase 1 of the main branch, but for the city of Hamilton. I am looking to create
a zoning per parcel map. Look at my other GitHub repositories if needed."

### What "phase 1" was
`main` only had the initial commit. The Toronto Phase 1 is on branch
`claude/determined-lovelace-oc32xm` (`phase1/summary.md`, `feasibility.md`, `inventory.csv`): a data
inventory and a five-question feasibility gate for zoning → application → permit → completion. A
Phase 2 code skeleton is on `claude/optimistic-fermat-c1mogk`. The Hamilton work copies Phase 1's
structure and adds the parcel zoning map.

### Other repositories checked
- `TaxImpactMapping`: Hamilton 2021 tax-impact site. Its parcels came from
  `spatialsolutions.hamilton.ca/.../General/Property/MapServer/5`, which pointed us to the City's
  ArcGIS server. Reused: its per-ward parcel-file pattern for the map, and its vendored Leaflet 1.9.4.
- `ontario-municipality-map`: province-wide municipal map; not needed.
- `Programming`: unrelated.

### Access
- Reachable: `spatialsolutions.hamilton.ca` (ArcGIS 11.5 REST), `www.hamilton.ca`,
  `hub.arcgis.com`, `library.mcmaster.ca` (via the fetch tool), CMHC, OLT.
- `open.hamilton.ca` serves a Cloudflare JavaScript challenge to scripts, so its catalogue and licence
  pages could not be read.
- **The REST server answers 403 to the `Python-urllib` user agent** (curl worked, Python did not).
  Fixed by sending a descriptive `User-Agent`. An early fetch run failed silently because of this.
- CARTO basemap tiles now return "API key required" watermarks; switched the map to Esri Gray Canvas.

### Data found (all counts from our own queries, 2026-10-30)
- `General/Zoning/MapServer`: 22 layers. Used 9 (Zoning Boundaries, 11,868), 8 (Council Approved,
  263), 15 (Property Parcels for Zoning Lookup, 177,753), 19 (ICBL, 1), 12 (Compliance Review, 26),
  11 (H-Converted Dwelling Parcel, 55).
- `General/Political/MapServer` 15 (wards) and 7 (communities).
- `General/Development/MapServer`: Committee of Adjustment (16,891, has `ROLL_NUMBER`) and
  Development Applications (13,276). Not downloaded; inspected with statistics queries.
- `General/Property/MapServer`: tax parcels for 2012, 2013, 2016, 2018-2021.
- Zoning parent by-laws: 05-200 (7,625 polygons) and six former by-laws, plus 9 Dundas polygons
  under a "1964" by-law and 3 with none.

### Decisions
| Decision | Why |
|---|---|
| Parcel layer = Zoning/MapServer/15 (not Property/5 used by TaxImpactMapping) | It is the layer the City uses for zoning lookups, has address, MPAC code and site area, and uses 15-digit roll numbers that match CoA `ROLL_NUMBER`. |
| Area overlay in EPSG:26917, primary zone = largest share | Zoning polygons form a clean coverage (overlap 0.0009% of area), so shares are well defined. UTM 17N matches TaxImpactMapping. |
| Sliver filter 5% and 10 m² | Without it, nearly every parcel touching a zone edge looks split. The long pieces table keeps every overlap so the threshold can be changed later. |
| Zone label includes exceptions, holdings and temporary uses | Matches how the City labels zones; an exception can change permissions entirely. |
| Keep one row per parcel polygon; add `geom_group` | 571 rolls repeat (multi-part parcels) and condo units share footprints; collapsing would lose rows, so we keep them and draw each footprint once on the map. |
| Decode `UNIT_OF_MEASURE` from area ratios | Not documented. Median ratio of `SITE_AREA` to polygon area: A 0.000246 (acres), F 10.77 (sq ft), M 1.0006 (m²), H 0.0001 (ha). |
| Flag `geometry_suspect` | Parcel areas summed to 1,745 km² against a 1,074 km² union. Traced to stacked condo footprints, 12 rolls sharing a 19.5 km² harbour polygon (385 Burlington St E and others, MPAC 840/842/588), and ~238 genuine overlaps. |
| Treat OLT tags as by-law-level | Crosstab: each big tag sits only on the zones introduced by one appealed city-wide by-law (e.g. 24-000544 on 44,605 parcels with amending by-law 24-051). |
| Validate against the live service, not just locally | The server does its own point-in-polygon query, which independently checks projection and join. |
| Map colours re-stepped after validation | The first palette failed the colour-vision check on agricultural vs open space, which touch everywhere in rural Hamilton. Final palette and legend order pass adjacent-pair checks in both themes (see `parcel_zoning/README.md`). |

### Results
- 177,751 of 177,753 parcels zoned; 7,528 split-zoned; 27% under former by-laws; 5,259 with an
  exception; 2,733 with a holding provision; 4,675 with a pending change.
- Validation (seed 20261030): single-zone 300/300; split-zoned 275/300 in the primary zone, the other
  25 in a listed secondary zone.
- Map data: 65 MB in `parcel_zoning/site/data/` (per-ward parcel files 1.7-4.7 MB, zoning 4.5 MB,
  search index 13 MB loaded on first search).

### Commits on this branch
1. Fetch City layers and assign zoning to every parcel.
2. Web map and live-service validation.
3. Validated palette, legend order, parcel_zoning README.
4. Phase 1 documents (summary, feasibility, inventory), this log, READMEs.
5. Raw City downloads committed as `.geojson.gz` (user asked for everything to be committed).
   `parcels.geojson` is 136 MB, over GitHub's 100 MB per-file limit, so fetch.py now writes gzip
   and the scripts read through `scripts/rawio.py` (GDAL `/vsigzip/`). Re-running the overlay from the
   compressed files reproduced both output CSVs and summary.json exactly.
