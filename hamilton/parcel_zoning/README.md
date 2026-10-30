# Hamilton parcel zoning

The zone in force on every property parcel in the City of Hamilton, as a table and a web map.
Built from the City's own public ArcGIS layers, downloaded **2026-10-30**. This is a research
dataset, not a zoning confirmation: the City's legal by-law text governs.

- **Map:** [`site/index.html`](site/index.html) (static; serve the folder, see below)
- **Table:** [`output/hamilton_parcel_zoning.csv.gz`](output/hamilton_parcel_zoning.csv.gz), one row per parcel polygon (177,753 rows)
- **Overlaps:** [`output/hamilton_parcel_zone_pieces.csv.gz`](output/hamilton_parcel_zone_pieces.csv.gz), one row per parcel × zoning-polygon overlap (287,139 rows)
- **Numbers:** [`output/summary.json`](output/summary.json); validation in [`output/validation.json`](output/validation.json)
- **Why and how it was built, step by step:** [`../LOG.md`](../LOG.md)

## Headline numbers (2026-10-30 download)

| | |
|---|---|
| Parcel polygons | 177,753 (177,182 distinct roll numbers; 156,142 distinct footprints) |
| Zoning polygons | 11,868 downloaded, 11,837 with geometry |
| Parcels given a zone | 177,751 (99.999%); 2 have no zoning polygon under them |
| Split-zoned parcels (2+ zones, each ≥ 5% and ≥ 10 m²) | 7,528 (4.2%) |
| Governed by Zoning By-law 05-200 | 129,284 (72.7%) |
| Still governed by a former municipality's by-law | 48,467 (27.3%): Hamilton 6593 20,207 · Stoney Creek 3692-92 9,854 · Glanbrook 464 7,059 · Ancaster 87-57 5,862 · Flamborough 90-145-Z 4,154 · Dundas 3581-86 1,301 · Dundas 1964 30 |
| With a site-specific exception | 5,259 |
| With a holding provision | 2,733 |
| With a council-approved change not yet final and binding | 4,675 (4,217 under By-law 26-178) |
| Tagged with an OLT/OMB case number | 70,968 (see caveat below) |

## Validation

`scripts/validate.py` sends each sampled parcel's interior point to the City's live Zoning
Boundaries layer (a server-side query, independent of the local overlay) and compares codes.
Seed 20261030, 300 parcels per stratum:

- **Single-zone parcels: 300 of 300 agree.**
- **Split-zoned parcels:** 275 of 300 interior points fall in our primary zone. The other 25
  fall in a secondary zone that we already list in `all_zones`, which is expected: an interior
  point can land in either zone of a split parcel.

This confirms the projection and join are right. It does not check the City's layer against the
legal by-law.

## Method

1. `scripts/fetch.py` downloads the layers below as GeoJSON (EPSG:4326) into `raw/` (gitignored;
   about 210 MB) and records server counts and download times in `raw/manifest.json`.
2. `scripts/build_parcel_zoning.py` projects both layers to UTM 17N (EPSG:26917), intersects every
   parcel with the zoning polygons it touches and computes each piece's share of the parcel's area.
   - Pieces under **5%** of the parcel or under **10 m²** are treated as digitizing slivers
     (the two layers are drawn separately, so edges never line up exactly).
   - The **primary zone** is the zone label covering the largest share.
   - A parcel is **split-zoned** when two or more distinct zone labels survive the sliver filter.
   - A zone label is the code plus exceptions, holdings and temporary uses, the way the City's map
     labels it (e.g. `C5, 570` or `RM3-442-H`).
   - Council-approved changes, ward and community are attached where they cover ≥ 50% of the
     parcel; the interim-control, compliance-review and H-converted flags use the same 50% rule.
3. `scripts/validate.py` runs the check above.
4. `scripts/build_map.py` writes the web map's data files to `site/data/`.

### Rebuild

```bash
pip install geopandas pandas shapely pyogrio
```

```bash
cd hamilton/parcel_zoning && python scripts/fetch.py && python scripts/build_parcel_zoning.py && python scripts/validate.py && python scripts/build_map.py
```

The fetch takes about 2 minutes, the overlay about 3, the map files about 3. Re-running on a later
day gives the zoning as of that day; commit the outputs with the new date in the message.

### View the map locally

```bash
cd hamilton/parcel_zoning/site && python3 -m http.server 8000
```

Then open <http://localhost:8000>. Opening `index.html` directly from disk will not load the data.
On GitHub Pages it works from `/hamilton/parcel_zoning/site/`.

## Sources

All from `https://spatialsolutions.hamilton.ca/webgis/rest/services/General/` (City of Hamilton
Web GIS, "City of Hamilton - Web GIS Framework"). The City publishes these under its Open Data
Licence (per McMaster Library's catalogue record; the open.hamilton.ca page itself could not be
opened from this environment because of a Cloudflare challenge). Attribute the City of Hamilton.

| Key | Layer | Records |
|---|---|---|
| `zoning` | Zoning/MapServer/9 Zoning Boundaries | 11,868 |
| `zoning_council_approved` | Zoning/MapServer/8 Council Approved - Zoning Boundaries | 263 |
| `parcels` | Zoning/MapServer/15 Property Parcels (for Zoning Lookup) | 177,753 |
| `interim_control` | Zoning/MapServer/19 Interim Control Bylaw Zone | 1 |
| `compliance_review` | Zoning/MapServer/12 Zoning Compliance Review Required | 26 |
| `h_converted_parcels` | Zoning/MapServer/11 H-Converted Dwelling Parcel | 55 |
| `wards` | Political/MapServer/15 Post-2018 Election Wards | 15 |
| `communities` | Political/MapServer/7 Community Boundaries | 6 |

The server returns HTTP 403 to Python's default `Python-urllib` user agent; the scripts send their own.

## Columns in `hamilton_parcel_zoning.csv.gz`

| Column | Meaning |
|---|---|
| `parcel_oid` | OBJECTID of the parcel polygon in layer 15 (unique key of this table) |
| `property_num` | 15-digit assessment roll number. 571 rows repeat a roll (multi-part parcels) |
| `address` | City `LOCATOR` string, e.g. `14 BALSAM AVE S - HAMILTON` |
| `mpac_property_code` | MPAC property code (301 single detached, 370 condo unit, 309 townhouse, 311 semi, 100 vacant…) |
| `frontage`, `depth` | From the parcel layer, as published (units not documented) |
| `site_area`, `unit_of_measure` | Assessed site area and its unit: A acres, F square feet, M square metres, H hectares (inferred; see LOG) |
| `site_area_m2` | `site_area` converted to m² |
| `parcel_area_m2` | Area of the drawn polygon in m² (UTM 17N) |
| `geom_group`, `n_same_geometry` | Id of the distinct footprint and how many rows share it (condo units share one) |
| `geometry_suspect` | Polygon area is < 0.1× or > 10× the assessed site area, or the polygon is over 10 km² |
| `zone_label` | Primary zone label (code, exceptions, holdings, temporary uses) |
| `primary_share` | Share of the parcel's area in the primary zone |
| `n_zones`, `all_zones`, `second_share` | Count and list (largest first) of zones surviving the sliver filter; share of the second |
| `covered_share` | Share of the parcel covered by any zoning polygon |
| `zoning_code`, `zoning_desc`, `category` | Primary zone code, description and City category (`Low Density Residential` folded into `Residential`) |
| `bylaw` | Governing parent by-law: `05-200` or the former municipality's by-law |
| `by_law_number` | Latest amending by-law recorded on the zoning polygon |
| `exception1-3`, `holding1-3`, `temporary_use_1-2` | Special exception, holding and temporary-use provision numbers |
| `olt_case_no` | OLT/OMB case number on the zoning polygon (see caveat) |
| `urban_rural_settle`, `zoning_map` | Urban/Rural/Settlement code and zoning map sheet |
| `has_zoning`, `split_zoned`, `has_exception`, `has_holding`, `has_temporary_use`, `under_olt_appeal_tag`, `former_bylaw` | Flags derived from the above |
| `in_interim_control`, `in_compliance_review_area`, `h_converted_dwelling` | Parcel ≥ 50% inside those City layers |
| `pending_zoning_code`, `pending_by_law_number`, `pending_council_app_date` | Council-approved zoning not yet final and binding, where it covers ≥ 50% of the parcel |
| `ward`, `community` | Post-2018 ward and former municipality (≥ 50% overlap) |

`hamilton_parcel_zone_pieces.csv.gz` has `parcel_oid, property_num, zone_label, zoning_code,
category, bylaw, piece_m2, share` for every overlap before the sliver filter, so other thresholds can
be applied without re-running the overlay.

## Caveats

- **The OLT/OMB tag is not a live-appeal flag.** Each common tag lines up with the city-wide by-law
  that introduced that zone family: `24-000544` ↔ By-law 24-051 (low-density residential),
  `PL150805` ↔ 15-173 (rural), `PL171450` ↔ 17-240 (commercial and mixed use), `PL180548` ↔ 18-114
  (downtown), `PL100633`/`PL100634` ↔ 10-128 (industrial). It says the parent by-law was appealed,
  not that the parcel is under appeal today. A local news report says 24-051 is in force except at
  752 and 756 West 5th Street ([The Public Record](https://thepublicrecord.ca/?p=317361)); site-level status needs the OLT case file.
- **Current snapshot only.** There is no history of the zoning layer on the server. Use
  `by_law_number` and the City's `FINALBINDING_DATE` per polygon (in `raw/`) to tell when zoning last
  changed. Nine polygons carry impossible dates (up to 2105).
- **Former by-laws** still govern 27% of parcels; their codes (e.g. `D/S-1822`, `RM3-002`) are not
  comparable with 05-200 codes. Use `category` to compare across by-laws.
- **Shared and doubtful shapes.** 19,780 condo-unit rolls (MPAC 370) sit on 1,266 shared footprints;
  12 rolls share one 19.5 km² polygon covering the harbour; 495 rows are flagged `geometry_suspect`
  (mostly MPAC 561 and 597, i.e. rail and road-type property).
- **Exceptions and holdings change what is permitted.** The map shows that one applies, not what it says.
  Text is in Schedule C of 05-200 and in the former by-laws.

## Map colours

Zone categories use planning-map conventions (residential yellow, commercial red, industrial violet,
open space green, agricultural wheat) so the map reads like the City's. The eight coloured categories
were checked with the dataviz skill's palette validator in the legend order (agricultural, open space,
industrial, commercial, transit-oriented corridor, residential, institutional, waterfront), which puts
land uses that touch on the ground side by side. In that order every neighbouring pair passes the
colour-vision-deficiency check (worst ΔE 9.1 light, 8.4 dark) and the normal-vision check (worst 17.2
light, 17.0 dark). The one failure is agricultural's lightness band: it is deliberately pale, because
it is the background land use of rural Hamilton.

With 11 categories no palette separates every possible pair, and three light-mode colours are below
3:1 contrast on white. Identity therefore never relies on colour alone: every parcel's popup names
its category, and clicking a legend entry hides or shows that category. Governing by-law uses two
colours (05-200 blue, former by-law orange). Condition mode shows one condition in red against grey.

Basemap: Esri World Light/Dark Gray Canvas (no key needed). Leaflet 1.9.4 is vendored in
`site/vendor/leaflet` (copied from the TaxImpactMapping repo; BSD-2 licence included).
