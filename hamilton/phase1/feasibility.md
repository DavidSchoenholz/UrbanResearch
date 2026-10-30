# Phase 1 feasibility: Hamilton zoning → application → approval → permit → completion

Prepared 2026-10-30. Descriptive and associational only; no causal claims. Same structure as the
Toronto feasibility note (branch `claude/determined-lovelace-oc32xm`, `phase1/feasibility.md`).

## 0. Access and evidence labels (read first)

- **Reachable and used:** the City's ArcGIS REST server
  `https://spatialsolutions.hamilton.ca/webgis/rest/services/` (every layer listed in `inventory.csv`
  was queried for its schema and record count, and the zoning, parcel and context layers were
  downloaded in full), `www.hamilton.ca` (zoning by-law pages read), `library.mcmaster.ca`,
  `www.cmhc-schl.gc.ca`, `olt.gov.on.ca` (reachable; content not assessed).
- **Blocked:** `open.hamilton.ca` returns a Cloudflare challenge to scripts, so the open-data
  catalogue pages (licence text, extra datasets) were not opened. `www150.statcan.gc.ca` /
  `www12.statcan.gc.ca` returned 403/redirects.
- **Gotcha:** the REST server returns HTTP 403 to Python's default `Python-urllib` user agent. Send a
  descriptive `User-Agent` (the scripts in `../parcel_zoning/scripts/` do).

Labels:
- **[V]**: opened and verified this session: a query we ran against the City service, a file we
  downloaded and computed on, or a City page we read.
- **[S]**: seen in a search-engine result for the cited URL; the page itself was not opened.
- **[R]**: recalled from background knowledge, not opened. Treat as **UNVERIFIED**.
- **[I]**: our inference from verified data; stated with its basis.

---

## 1. Operational definitions

### 1.1 Zoning of a parcel (built)
- **Primary zone** = the zone label covering the largest share of the parcel's area, after dropping
  overlap pieces under 5% of the parcel or under 10 m² (digitizing slivers). Computed in EPSG:26917.
- **Zone label** = `ZONING_CODE` + `EXCEPTION1-3` + `HOLDING1-3` + `TEMPORARY_USE_1-2`, the way the
  City's map labels zones [V].
- **Split-zoned** = two or more distinct labels survive the sliver filter (7,528 parcels, 4.2%) [V].
- **Governing by-law** = `PARENT_BY_LAW_NUMBER` of the primary zone polygon: `05-200` or a former
  municipality's by-law [V].
- **Category** = the City's `ZONING_CATEGORY` (Residential, Commercial, Industrial, …), which is the
  only field comparable across by-laws [V].

### 1.2 Zoned capacity (not built; feasibility only)
Hamilton's layers carry zone codes but **no numeric FSI or height fields** [V: the 52 fields of the
Zoning Boundaries layer have none]. Toronto's layer had `FSI_TOTAL`. Capacity would have to be coded
from the by-law text per zone. 05-200 polygons use 62 distinct codes; former-by-law polygons use 2,065,
because their site-specific variants are written into the code (e.g. `D/S-1822`) [V]. Recommendation:
code capacity for the 05-200 residential zones only (R1, R1a, R2, R3, R4, R4a: 100,858 parcels [V]),
using unit permissions rather than floor area where the by-law caps units.

Lot attributes available per parcel: assessed `SITE_AREA` with a unit code, `FRONTAGE`, `DEPTH` [V].
The unit codes were decoded by comparing with polygon area: A = acres, F = square feet, M = square
metres, H = hectares (median ratios 0.000246, 10.77, 1.0006, 0.0001) [I from V]. After conversion the
median ratio of assessed to drawn area is 0.998 [V].

### 1.3 As-of-right vs. rezoning vs. minor variance
| Class | Rule (data fields) |
|---|---|
| **Rezoning** | Development Applications point (`FILE_TYPE` = Zoning Amendment or Official Plan Amendment) inside the parcel [V fields] |
| **Minor variance** | Committee of Adjustment record with `FILE_NUMBER` starting `A-` and the parcel's `ROLL_NUMBER` [V fields; `A-`/`B-` meaning is R, consistent with `B-` files appearing as "Land Division" in the other layer] |
| **Consent (severance)** | CoA `B-` file, or Development Applications `FILE_TYPE` = Land Division [V] |
| **As-of-right** | None of the above within the look-back window |

Selection bias is the same as in Toronto: rezonings are chosen where zoning binds, so classes must be
reported separately.

### 1.4 Project and completion
No official open permit data was found, so projects cannot yet be built from permits. Completion
measures are the same family as Toronto's: CMHC Starts & Completions for the Hamilton CMA/CSD [R:
CSD 3525005], and Census net dwelling change. The City's monthly Building Activity reports count
permits issued, not completions [S].

---

## 2. Verification items

| Item | Finding | Status |
|---|---|---|
| Does one zoning by-law cover the city? | **No.** 05-200 "came into effect on May 25, 2005" and has been introduced in phases; "the remaining properties … are regulated by the Zoning By-laws from" Ancaster 87-57, Dundas 3581-86, Flamborough 90-145-Z, Glanbrook 464, former City of Hamilton 6593 and Stoney Creek 3692-92 (each consolidated as of October 2026). The "Remnant Zones Project" is moving the rest in. In the layer: 05-200 governs 7,625 of 11,868 polygons and 72.7% of parcels. 9 polygons in Dundas carry a "1964" parent by-law. | [V] hamilton.ca pages + layer |
| Zoning history | No past vintage on the server or in McMaster Library ("Current" only). Polygons carry `BY_LAW_NUMBER`, `COUNCIL_APP_DATE` (6,934 filled), `FINALBINDING_DATE` (8,776 filled), `CREATED_DATE` (2009-11-11 to 2026-10-27) and `LAST_EDITED_DATE` (2025-06-25 to 2026-10-29). 9 polygons have dates after today (max 2105). | [V] |
| Pending zoning | "Council Approved - Zoning Boundaries" layer: 263 polygons, Council dates 2010-05-26 to 2026-10-07, mostly By-law 26-178 (183 polygons) changing `E`, `DE-2`, `RT-20` and similar former-Hamilton zones to `R3`, `R4`, `R4a` on 4,217 parcels. | [V]; purpose of 26-178 [I] |
| Exceptions and holding provisions in open data | Yes, as attributes: `EXCEPTION1-3` (1,488 polygons with at least one), `HOLDING1-3` (237), each with the by-law number and a URL field; temporary-use provisions `TEMPORARY_USE_1-2` (T6, T8 on 1,685 polygons). Text of exceptions is in Schedule C of 05-200, not in the layer. | [V] |
| Appeals | `OLT_CASE_NO` / `OLT_LEAD_CASE_NO` on 5,890 polygons. Main tags match the by-law that introduced the zone family (24-000544 ↔ 24-051 on 44,605 parcels; PL150805 ↔ 15-173; PL171450 ↔ 17-240; PL180548 ↔ 18-114; PL100633/PL100634 ↔ 10-128). A news report says 24-051 is in force except at 752/756 West 5th St. No open appeal dataset. | [V] layer; [S] news |
| Interim control | One interim control by-law area (22-258, Melville Street Heritage Conservation District, Dundas, Council 2022-09-28), 89 parcels. Whether it is still in effect is UNVERIFIED (ICBLs normally last one year, extendable to two [R]). | [V] layer |
| Parcels | "Property Parcels (for Zoning Lookup)": 177,753 polygons, 15-digit `PROPERTY_NUM` on all, 571 repeated rolls, 13 invalid geometries (repaired). Condo units share footprints (22,877 rows on 1,266 shared shapes). Tax-parcel vintages 2012 (173,841), 2013 (175,932), 2016 (181,331), 2018 (183,585), 2019 (186,265), 2020 (184,306), 2021 (186,525). | [V] |
| Development applications | 13,276 points. `FILE_TYPE`: Site Plan 3,703; Land Division 3,465; Formal Consultation 2,284; Zoning Amendment 1,266; Subdivision 877; Condominium 522; Part Lot Control 448; OPA 445. `FILE_YEAR` 1972-2026, mostly 2000+; zoning amendments 31-80 per year 2008-2026. Fill rates: `APP_DATE` 2,099; `STAT_DATE` 1,894; `PRPS_UNITS` 5,458 (3,813 > 0); `APPEALED` 314; status 12,729. | [V] |
| Committee of Adjustment | 16,891 points with `FILE_NUMBER` (e.g. A-26:062, B-26:007) and `ROLL_NUMBER`. `STATUS` filled for about 3,800 (Granted 1,967; Denied 147; …). `APPLICATION_FILE_YEAR` only for 2024-2026; year is in the file number. Records created 2009-10-29 onward. | [V] |
| Building permits | No City open dataset found. Monthly "Building Activity" PDFs on hamilton.ca. The Public Record's Hamilton permit tracker compiles them (113,433 permits, 2010-01 to 2026-05, CC BY-SA 4.0). | [S] |
| Completions | CMHC portal host reachable; Hamilton CT-level completions after 2023 not checked. | Not assessed |

**Policy time markers** (05-200 phases, from the City's 05-200 page [V] unless marked).

| Date | Event |
|---|---|
| 2001-01-01 | Amalgamation of the six former municipalities [R] |
| 2005-05-25 | 05-200 in effect (Sections 1-6, Downtown boundaries) |
| 2006-06-14 | Open Space and Parks zones, urban (06-166) |
| 2007-03-28 | Institutional zones, urban (07-101) |
| 2011-06-28 | Industrial zones, urban (10-128) |
| 2015-04-10 | Airport Employment Growth District industrial zones (10-288) |
| 2015-07-10 | Rural zones, Conservation/Hazard and Extractive zones (15-173) |
| 2016-10-12 / 2018-02-14 | Transit Oriented Corridor zones phase 1 (16-265) / phase 2 (18-032) |
| 2017-05-24 | Waterfront zones (17-095) |
| 2017-11-08 | Commercial and Mixed Use zones, urban (17-240) |
| 2018 | Downtown zones comprehensively amended (18-114) |
| 2022-08-12 | Low Density Residential zones, urban (22-197) |
| 2022-11-28 | Bill 23 royal assent [S, from the Toronto note] |
| 2024-04-10 | Third Low Density Residential zone (24-051) |
| 2025 | Mid Rise Residential zones passed (25-189; effective date not stated on the page) |
| 2026-09-29 / 2026-10-07 | Mid-rise expansion report to Planning Committee [V page]; By-law 26-178 council-approved, not yet final [V layer] |

**Recommended markers.** 2022-08-12 and 2024-04-10 are single, city-wide, as-of-right residential
changes, the Hamilton analogue of Toronto's 2023-05-12 multiplex marker. Parcels still under former
by-laws on those dates are a natural comparison group (they did not get the new zones). Check the
exact permission changes (units per lot) in the by-law text before using them.

---

## 3. Feasibility gate

**Q1. Can zoning be obtained as of each application date?**
**Partially, and better than Toronto.** The layer is a current snapshot, but each polygon records its
amending by-law and final-and-binding date. Rule: a parcel's current zoning applied on date *d* if its
polygon's `FINALBINDING_DATE` (else `COUNCIL_APP_DATE`) is before *d* and no pending or later by-law
touches it. Parcels failing the rule need backcasting from the by-law text. Parcel geometry can be
traced with the 2012-2021 tax-parcel layers.

**Q2. Is there a project-level link between applications and permits?**
**Applications to parcels: yes. Permits: not yet.** CoA records carry the roll number; development
applications are points inside parcels. There is no open permit dataset with permit or application
numbers, so the permit stage depends on the third-party compilation or a request to the City.

**Q3. Is there a completions measure finer than the whole city?**
Not assessed this session. Expected: CMHC CMA/CSD, possibly census tract; Census net dwelling change.

**Q4. How many years have consistent coverage across all four stages?**
| Stage | Coverage |
|---|---|
| Zoning | Current snapshot; per-polygon dates back to the 1980s |
| Parcels | Current + tax years 2012-2021 |
| Development applications | Mostly 2000+, zoning amendments steady from 2008; dates sparse |
| Committee of Adjustment | Records from 2009 onward (by creation date) |
| Permits | 2010-01 to 2026-05 (third party) [S] |
| Completions | CMHC long series [R] |

Recommended study window: **2010-2025**.

**Q5. What is the finest reliable unit of analysis?**
**The parcel (roll number)** for zoning, applications and CoA. Census tract for completions.

---

## 4. Verdict

**GO** for the parcel zoning map: built, validated against the City's live service, and published in
this repository (`../parcel_zoning/`).

**GO WITH LIMITS** for the pipeline:
1. Use attribute dates to restrict to parcels with stable zoning; report the excluded share.
2. Treat the OLT tags as by-law-level, not parcel-level, appeal information.
3. Permits need an external source; completions need CMHC.
4. Cross-by-law comparisons use `category`, not codes.

**Fallback:** a parcel-level description of zoning (done), plus CoA and rezoning activity by zone and
by governing by-law around the 2022-08-12 and 2024-04-10 markers, without permits or completions.
