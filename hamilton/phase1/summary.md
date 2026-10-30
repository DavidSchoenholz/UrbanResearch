# Phase 1 summary: Hamilton zoning and the housing pipeline

Prepared 2026-10-30. This mirrors the Toronto Phase 1 (branch `claude/determined-lovelace-oc32xm`,
`phase1/`), with the same questions and file layout, and adds the deliverable asked for this time:
**a zoning-per-parcel map** (`../parcel_zoning/`).

**Verdict: GO for the parcel zoning map (built and validated). GO WITH LIMITS for the full
zoning → application → permit → completion pipeline.**

Unlike Toronto's Phase 1, most Hamilton claims here were **opened and verified [V]**: the City's
ArcGIS REST server and www.hamilton.ca were reachable, and the counts below come from our own
queries and downloads. Evidence labels are explained in `feasibility.md` §0. The full evidence is in
`feasibility.md`, and dataset details are in `inventory.csv`.

## What was built
- Every one of 177,753 parcel polygons assigned a zone by area overlay. 99.999% are matched; 4.2%
  are split-zoned. The parcels joined to the City's live service agreed on 300 of 300 single-zone
  samples. See `../parcel_zoning/README.md`.
- A static web map (`../parcel_zoning/site/`) colours parcels by zone category, governing by-law or
  special condition (exception, holding, appeal tag, pending change), with an address and roll search.

## Key findings and limitations
1. **Two zoning regimes at once.** Zoning By-law 05-200 (in effect 2005-05-25) has been rolled out
   one zone family at a time; residential zones are the final phase. **27% of parcels (48,467) are
   still governed by one of six former-municipality by-laws** (Hamilton 6593, Stoney Creek 3692-92,
   Glanbrook 464, Ancaster 87-57, Flamborough 90-145-Z, Dundas 3581-86) [V]. Their zone codes are not
   comparable with 05-200, so cross-city analysis must use the City's `ZONING_CATEGORY`.
2. **Zoning is a current snapshot, but each polygon is dated.** No past vintage of the layer was found
   (McMaster Library lists only "Current" [V]). Each polygon carries its amending by-law, Council
   approval date and final-and-binding date [V], so "has this lot's zoning changed since date X?" can
   be answered from attributes, which Toronto could not do. Nine polygons have impossible dates (up to 2105).
3. **Pending changes are published.** A separate "Council Approved" layer holds zoning passed but not
   yet final and binding: 263 polygons covering 4,675 parcels, most under By-law 26-178, which moves
   former-Hamilton `E`/`DE`/`RT` zones to the new mid-rise `R3`/`R4`/`R4a` zones [V; the link to the
   mid-rise expansion project is an inference].
4. **Appeal tags mark appealed by-laws, not live appeals.** 70,968 parcels sit on polygons tagged with
   an OLT/OMB case. The big tags correspond one-to-one with the city-wide by-laws that introduced each
   zone family (24-000544 ↔ 24-051; PL150805 ↔ 15-173; PL171450 ↔ 17-240; PL180548 ↔ 18-114;
   PL100633/4 ↔ 10-128) [V]. Site-level status needs the OLT case file.
5. **Applications link to parcels.** Committee of Adjustment records carry a **roll number** [V], a
   direct key to the parcel table. Development applications (13,276 points; 1,266 zoning amendments,
   445 OPAs, 3,703 site plans) link by location [V]. But application dates are sparse (`APP_DATE` filled
   for 2,099 of 13,276), and CoA status is filled for about a quarter of records.
6. **No official open building-permit dataset was found.** The City publishes monthly Building
   Activity PDFs [S]. A third-party compilation (The Public Record, CC BY-SA 4.0, 113,433 permits,
   2010-01 to 2026-05, parsed from those PDFs) exists [S, not opened]. Permits are the weakest stage.
7. **Parcel geometry has known quirks.** 19,780 condo-unit rolls share 1,266 footprints; 12 rolls share a
   19.5 km² harbour polygon; 495 rows have shapes far from their assessed site area [V]. Parcel layers
   for tax years 2012, 2013, 2016, 2018, 2019, 2020 and 2021 are on the same server [V], so lot splits
   and consolidations can be traced.

## Recommended frame (to confirm in Phase 2)
- **Unit of analysis:** the parcel (roll number) for zoning and CoA; the census tract for completions.
- **Classes:** rezoning (ZAC/OPA), minor variance (CoA `A-` files), consent (`B-` files) and as-of-right,
  reported separately because of selection bias.
- **Natural experiments:** the phased 05-200 roll-out gives dated, city-wide zoning changes. The
  cleanest residential markers are **2022-08-12** (low-density residential zones, By-law 22-197) and
  **2024-04-10** (third low-density zone, By-law 24-051) [V], with mid-rise zones (25-189; 26-178 pending)
  next. Parcels still under former by-laws form a comparison group.
- **Study period:** 2010-2025, set by the third-party permit series and application coverage.

## Must-verify checklist
1. Open the open.hamilton.ca dataset pages (blocked here by a Cloudflare challenge) to confirm the
   licence wording and whether the portal offers more than the REST layers (e.g. a permits dataset).
2. Ask the City (Building Division) for a machine-readable permit extract; otherwise check the
   third-party permit compilation against a few monthly PDFs.
3. Check CMHC Housing Market Information Portal completions for Hamilton census tracts after 2023.
4. Confirm the meaning of `OLT_CASE_NO` with City Planning, and the site-level status of 24-000544.
5. Confirm `FRONTAGE`/`DEPTH` units and the `UNIT_OF_MEASURE` codes (inferred, not documented).

## Files
- `inventory.csv`: 26 datasets and sources with URL, publisher, licence, coverage, fields, limitations,
  join keys and provenance (same columns as Toronto's).
- `feasibility.md`: access notes, operational definitions, verification table, policy time markers,
  the five gate answers and the verdict.
- `../parcel_zoning/`: the parcel zoning table, map, scripts and validation.
- `../LOG.md`: dated research log of what was done, found and decided.
