# Phase 1 feasibility: Toronto zoning → application → approval → permit → completion

Prepared 2026-10-30. The study is descriptive and associational; nothing here supports causal claims.

## 0. Access and evidence

**How the evidence was gathered.**
- **Toronto open data:** every catalogue record was read through the City's open-data (CKAN) API, with metadata and field schemas taken from it. The data files were downloaded and profiled, with outputs held in a scratch directory and not committed.
- **City pages:** City of Toronto, CMHC and OLT pages were fetched with `curl` and converted to text.
- **CMHC tables:** pulled as CSV from the Housing Market Information Portal (HMIP) export endpoint.
- **Scripts:** all are in `scripts/`.

**Hosts I could not read:**
- `www12.statcan.gc.ca` returned HTTP 403.
- `www.statcan.gc.ca` (census release schedule) returned 503.
- `www.ola.org` (bill status) returned 403.
- `www.ontario.ca/laws` loads its content by script, so no statute text came back.

Claims that rest on those sources are labelled **UNVERIFIED** or "[secondary]".

**Labels used below:**
- **[V]**: verified from the primary source or data in this session.
- **[C]**: computed by me from downloaded primary data; the script is named.
- **[secondary]** or **UNVERIFIED**: not confirmed from a primary source.

---

## 1. Operational definitions

### 1.1 Zoned capacity
**Definition.** Zoned capacity is the maximum residential gross floor area (GFA) the zoning in force on date *t* permits on a lot, converted to units. It is compared with existing built floor area.

**Fields that implement it:** Zoning Area layer (`zoning-by-law`). The readme [V] defines:
- `FSI_TOTAL`: "permitted maximum FSI … Total in the zone";
- `PRCNT_RES`: the residential FSI share in mixed-use zones (the "r" value);
- `DENSITY`: the "d" value in residential zones;
- `UNITS`: the "u" value, a maximum unit count;
- `AREA_UNITS`: minimum lot area per unit;
- `COVERAGE`: lot coverage.

Overlays add `HT_LABEL` (metres) and `HT_STORIES` from the Height Overlay, and `PRCNT_CVER` from the Lot Coverage Overlay. The readme calls the height field `HT_HEIGHT`, but the published file has `HT_LABEL` [V].

**Formulas:**
- `cap_GFA = lot_area × FSI`. Use `PRCNT_RES` in mixed-use zones, else `FSI_TOTAL`, else `DENSITY`.
- Where no FSI applies, use the envelope: `lot_area × coverage × floor(HT_LABEL / 3.0 m)` (or `HT_STORIES`).
  - `lot_area` = polygon area from Property Boundaries (`PARCELID`, `STATEDAREA` [V]).
- `cap_units = max(unit-count rule, cap_GFA / g)`.
  - `g` is an assumed gross m² per unit; report results across a sensitivity range.
  - The unit-count rule is `UNITS`, or `lot_area / AREA_UNITS`. From May 2023 it is also 4 units in Neighbourhoods: Council adopted by-laws 473-2023 and 474-2023 on May 10, 2023 [V: toronto.ca Multiplex 2–4 study page].
  - From June 25–26, 2025 it is 6 units in Toronto & East York District and Ward 23 (by-laws 653-2025 and 654-2025) [V: toronto.ca/multiplex].

**What the numeric fields actually cover** [C: `spatial.py`]:
- `FSI_TOTAL>0` in only 24.1% of zoning polygons;
- `DENSITY>0` in 18.7%;
- `UNITS>0` in 5.6%;
- `COVERAGE>0` in 0%.

Most low-rise residential zones have no numeric FSI. For them, capacity has to come from the envelope (height and coverage overlays plus the setbacks in the by-law text), or from the unit-count rule.

**Existing built measure.**
- 3D Massing footprints with `AVG_HEIGHT`/`MAX_HEIGHT` [V, 2025 file], giving `built_GFA ≈ footprint × floor(AVG_HEIGHT / 3.0 m)`.
- The Building Outlines layer adds `DERIVED_HEIGHT` [V].
- There are annual 3D Massing vintages for 2016–2023 and 2025 (no 2024) [V]. Change in built form can therefore be measured over time.
- Existing units are not in any open building layer. Use 2021 Census dwellings at dissemination-area level, which I could not open here (UNVERIFIED). MPAC holds copyright on assessment data [V: 3D Massing record].

**Exceptions break the simple calculation.**
- 75.5% of Zoning Area polygons carry a Chapter 900 exception (`ZN_EXCPTN=Y`). So do 73% of single-unit and 49% of 50+ unit new-building permit sites [C].
- Exceptions can override FSI and height, so capacity read from the layer attributes is an upper or lower bound only.
- In Phase 2, parse each exception's numeric overrides (GFA, height, units) from the Chapter 900 text. I parsed 5,247 exceptions programmatically [C], so this is possible.

### 1.2 As-of-right vs. rezoning vs. minor variance
Classify each permit-project (§1.3) by the planning files at the same address within a lookback window (10 years before first `APPLICATION_DATE`, ending before `ISSUED_DATE`).

| Class | Rule |
|---|---|
| Rezoning | Development Applications `APPLICATION_TYPE='OZ'` at the same normalized address (`STREET_NUM`/`STREET_NAME`/`STREET_TYPE`/`STREET_DIRECTION`) or spatial match |
| Minor variance | No OZ; Committee of Adjustment `APPLICATION_TYPE='MV'` with `C_OF_A_DESCISION` approved |
| As-of-right | Neither. SA (site plan), SB, PL or CD links do not change zoning. |

**Feasibility evidence** (new-residential permit projects, applications 2018–2025, address match without a date window) [C: `link.py`]:

| Size | MV-linked | OZ-linked | No link |
|---|---|---|---|
| 1 unit | 79% | 4% | 17% |
| 2–4 units | 72% | 4% | 24% |
| 5–49 units | 17% | 64% | 20% |
| 50+ units | 9% | 87% | 5% |

These shares are upper bounds, because there is no date window and an address can have unrelated past files.

Three things follow:
- Truly as-of-right new construction is a minority in every size class.
- Large projects are almost all rezonings. The selection bias in the brief is severe: applications are concentrated where zoning does not permit the project.
- Analyses must be split by class and size.

### 1.3 Project (aggregating permits)
The permit number is the key [V field note: "Last two digits of calendar year, plus IBMS-generated sequence"].

1. **Use the folder stem.** The first two tokens of `PERMIT_NUM` (e.g. `05 196217`) form a permit folder. Every component shares it [C: `profile2.py`]:
   - building: `BLD`, or `B01…Bnn` for subdivision houses;
   - partial permits: `FND` (foundation), `SHO` (shoring), `STR` (structure);
   - trade permits: `PLB`, `HVA`, `DRN`;
   - demolition: `DEM`.
2. **Deduplicate on `PERMIT_NUM`+`REVISION_NUM`+`PERMIT_TYPE`.** These three are unique for 1,096,036 of 1,096,236 rows [C]. Revisions keep the same `PERMIT_NUM`.
3. **Units per building permit** = max `DWELLING_UNITS_CREATED` across revisions.
   - Units per folder = the sum over building permits (`BLD` and each `Bnn`).
   - Drop trade, partial and conditional permits from unit counts.
   - Drop obvious errors: one record has 100,000 units; 11 values are negative [C].
4. **Merge folders into a project** when they share `GEO_ID` (or a normalized address) and their activity overlaps within 36 months. This catches separate shoring and above-grade folders and phased towers.
5. **Planning-Act projects:** attach the Development Pipeline `Application Number`. It matches Development Applications `APPLICATION#` for 96.9% of Pipeline projects. 98% of "Built" projects have an exact address match to some permit [C].

Validate against a hand-checked sample before Phase 2 analysis.

### 1.4 Completion

| Measure | Field / source | Definition | Geography and years | Use |
|---|---|---|---|---|
| **CMHC completion** | HMIP 1.1.2.11 (CT), 1.2.2 (CSD) | "all the proposed construction work … has been performed … up to 10% … may remain" [V: CMHC methodology] | **CT 2010–2022 only.** 2023+ exports say "This data series is now archived" [V]. City of Toronto total 1998–2025 [V] | Primary |
| **City Pipeline "Built"** | `Pipeline Status='Built'` | "Projects that became ready for occupancy and/or were completed" [V: 2025 bulletin] | Project/address; **no built date**; rolling 5-year window | Project-level outcome, Planning-Act projects ≥ Site Plan threshold only |
| **Permit cleared** | `COMPLETED_DATE` ("Date work is complete and permit is cleared"), `STATUS='Closed'` | Administrative closure | Address; 2001–2026, **no 2007 clearances** [C] | **Not a completion measure** |
| **Net stock** | Census dwellings | Net of demolitions and conversions | DA/CT, 5-yearly | Net-unit check (UNVERIFIED, StatCan blocked) |

**Reconciliation** [C: `reconcile.py`]:
- **Census tracts vs. city total.** Tracts 0001–0399 sum to 16,292 completions in 2022, vs. 16,296 for the Toronto CSD. The tract file reproduces the city total.
- **Cleared permits vs. CMHC.** Units on cleared New Building permits equal only **22–62% of CMHC completions** in each year 2002–2024 (correlation 0.23). In 2025 they jump to 22,359 against CMHC's 14,753, which suggests a batch closure. Only 48% of 50+ unit permits issued 2010–2018 have cleared.
- **Permits issued vs. CMHC starts.** Units on issued permits run 0.5–1.5× CMHC starts each year (correlation 0.40). They track starts better than clearance tracks completions.
- **Pipeline "Built" vs. CMHC.** "Built" sums to 124,326 units, against 95,701 CMHC completions in the City over 2021–2025. Pipeline "Built" is *higher*, even though it excludes small projects. The definitions differ: "ready for occupancy and/or completed", and proposed rather than as-built unit counts. The two cannot be used interchangeably.

---

## 2. Verification results

### Zoning in force at application date
**Finding:** partially reconstructable.
- The open GIS layer is a single snapshot: "updated to include amendments up to June 18th, 2023" [V CKAN].
- The legal office consolidation is newer: "Version Date: July 31, 2024, including City-wide Amendments up to April 30, 2026" [V].
- Past versions:
  - Wayback Machine captures of the CKAN files on 2023-04-04 and 2024-06-05 [V, CDX index];
  - a 2014 vintage is reported in a library notice (UNVERIFIED).
- Chapter 900 exceptions cite their amending by-laws: 1,443 of 5,247 (27.5%) cite a "By-law: NNNN-YYYY", with latest-cited years 2014–2026 [C]. Site-specific changes after 2013 can therefore be dated, to the year from the citation and to the day from the by-law archive.

### Did 569-2013 fully replace the pre-amalgamation by-laws?
**No** [V].
- City: "569-2013 does not fully replace all older bylaws in every area".
- About "1500 low-rise residential parcels … were excluded … as part of the transition protocol".
- By-laws 206-2026 and 650-2026 are only now bringing Etobicoke-York and Scarborough low-rise lands into 569-2013, so the coverage boundary moves over time.
- "Some regulations … remain under appeal … Case Number PL130592 / OLT-22-002465".
- Former by-laws are hard copy or counter-only; there is no GIS.
- In the data, 50.8% of 50+ unit and 12.7% of 1-unit new-building permit sites fall outside every 569-2013 polygon [C].

### Exceptions, holding provisions, Secondary Plans, MZOs in open data
- **Exceptions:** `ZN_EXCPTN`/`EXCPTN_NO` and holding symbols `ZN_HOLDING`/`HOLDING_ID` are attributes [V readme]. There are 48 holding polygons. Exception text is only in the HTML consolidation.
- **Secondary Plans:** a layer exists, "current as of the 2015 Plan Consolidation", with 55 polygons [V].
- **Site and Area Specific Policies:** 868 polygons, December 2025 consolidation [V].
- **MZOs:** listed on a City web page, about 30 orders from O. Reg. 170/20 to 2026 [V]. They are **not** in the zoning layer. "If there is a conflict … the MZO prevails" [V].

### OLT appeals: role and data
- No open bulk dataset exists.
- Case Status keeps cases "two years after a case is closed". Decisions are online for up to 10 years and also on CanLII [V].
- Development Applications `STATUS` shows appeal states (`OMB Appeal`, `OMB Approved`, `Appeal Received`), but **current status only**:
  - 20–29% of 2020–2025 rezoning (OZ) files show an appeal state;
  - only 0–5% of 2008–2015 files do, because closure overwrites it [C].
- Appeal incidence for older cohorts therefore needs hand-coding from OLT decisions.
- Committee of Adjustment appeals: open TLAB dataset, 2,146 appeals since 2017-05 [V]. Committee of Adjustment records have `OMB_DESCISION` for 512 rows [C].
- No OLT terms-of-use page was found (404). `robots.txt` disallows only `/wp-admin/`. Manual lookup is assumed; nothing was scraped.

### Policy time markers (exact dates)
- **Multiplex ≤4 units:** Council adoption 2023-05-10 [V]. The in-force date (2023-05-12) is [secondary].
- **Garden suites:** Council 2022-02-02 [V]. In force after the OLT dismissed the appeal on 2022-07-04 [secondary]. O. Reg. 462/24 in force 2024-11-20 [V].
- **Sixplex (TEY + Ward 23):** Council 2025-06-25/26, "now in force" [V]; in-force date UNVERIFIED.
- **Bill 23** royal assent 2022-11-28 and **Bill 185** royal assent 2024-06-06: [secondary], UNVERIFIED from primary sources.

**Signal in the data** [C]. New Building permits for 2–6 units issued per year:

| Year | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 YTD |
|---|---|---|---|---|---|---|---|---|
| Permits | 16 | 22 | 28 | 47 | 65 | 153 | 243 | 292 |

Second-suite and laneway/garden-suite permit units rose from 238 (2019) to 858 (2025). **The multiplex marker of 2023-05 is usable** for permits. It cannot be studied for completions below city level, because census-tract completions end in 2022.

### Gross vs. net; units vs. buildings; definitional drift
- **Lost units:** `DWELLING_UNITS_LOST` is filled on about 35% of rows. Among "Demolition Folder" permits, the share with lost units > 0 rose from 33% (2004) to 87% (2025) [C]. Net-unit series are biased toward recent years.
- **Rental demolitions:** a separate dataset covers 6+ unit rental demolitions approved since 2017 (165 records) [V].
- **CMHC counts gross new units only.** Its "Residential Conversions and Demolitions" tables exist; geography UNVERIFIED.
- **Units vs. buildings:** permits record units per building permit, so subdivisions appear as `B01…Bnn`. Aggregate per §1.3.
- **Drift:**
  - wards went from 44 to 25 in Dec 2018, and neighbourhoods from 140 to 158 [V resources];
  - the Pipeline's rolling window changes each edition. Open-data units total 927,532 vs. the bulletin's "over 791,000" [C/V];
  - the 2000–2016 permits file uses a different date format and header case [C].

---

## 3. Feasibility gate

**Q1. Can zoning be obtained as of each application date?**
**Partially.**
- **569-2013 lands, 2013-05-09 onward:** yes, approximately. Take the current layer (June 2023) and the consolidation (to 2024/2026), then backcast by removing exceptions whose citing by-law post-dates *t*. Check against the 2023 and 2024 Wayback copies. City-wide changes have known dates (e.g. 474-2023).
  - Base-zone map changes that do not create an exception cannot be dated from Chapter 900 and need the by-law archive.
- **Lands under former by-laws:** no. That is about half of large-project sites [C]. There is no GIS, and the hard copies are not open.
- **Before 2013:** no harmonized zoning exists.
- **Rezoning and minor-variance files:** zoning-as-of-application is partly observed directly. Committee of Adjustment `ZONING_DESIGNATION` records it [V]. For rezonings, the staff reports linked via `APPLICATION_URL` state the existing zoning (manual).

**Q2. Is there a project-level link between applications and permits?**
**Yes for Planning-Act projects; by address for the rest.**
- The Development Pipeline groups applications and "downstream Building Permits" into projects [V].
- Its `Application Number` matches Development Applications `APPLICATION#` for 96.9% of projects [C].
- It has no permit IDs, but 98% of Built projects match a permit address [C].
- Permits carry no application number [V schema], so other projects link by address or `GEO_ID`.
- `GEO_ID` matches current Address Points for 88.6% of permits overall but only 69.8% of new-residential permits [C]. Supplement with address strings.

**Q3. Is there a completions measure finer than the whole city?**
**Yes, but only to 2022.**
- CMHC completions by census tract cover **2010–2022**, are archived after that, and reconcile with the city total [C/V].
- Starts by census tract continue through 2025 [V].
- Pipeline "Built" is project-level but undated, and limited to Planning-Act projects.

**Q4. Years with consistent coverage across all four stages; recommended period.**

| Stage | Coverage |
|---|---|
| Applications | Rezoning/site plan 2008-01 → [V]; Committee of Adjustment 2001 → [V]; TLAB 2017-05 → [V] |
| Approval / appeal | Current status only; no dates |
| Zoning | 569-2013 from 2013-05-09 (layer as of 2023-06) |
| Permits | Reliable from ~2002. Units on issued permits are <10% of CMHC starts before 2002 [C]; no 2007 clearances |
| Completions by tract | 2010–2022 |

**The overlap of all four stages at sub-city level is 2013-05 to 2022-12, about 9.5 years.**

Recommended design:
1. **Primary period:** application/permit cohorts **2013-05-09 to 2017-12-31**, with outcomes (permit issuance, CMHC starts and completions by tract) observed through **2022-12-31**. That gives at least 5 years for completion; the median time from application to issue for 50+ unit permits is 2.1 years, then 2.9 years to clearance [C].
2. **Extension:** for 2018–2025 cohorts, stop the outcome at *permit issued* and *CMHC start by tract*, which runs through 2025.
3. **Marker study:** an as-of-right low-rise window **2019-05 to 2026-09** around 2023-05-10, using permits and starts only.

**Q5. Finest reliable unit of analysis.**
- **Address/parcel** for application → approval → permit timing and attrition.
- **2021 census tract** for anything involving completions (2010–2022) or starts (to 2025).
- Wards are too coarse and were redrawn in 2018.

---

## 4. Verdict: **GO WITH LIMITS**

1. **Zoning history.** Zoning-as-of-date is reconstructable only for 569-2013 lands from 2013 onward, by backcasting. Former-by-law lands are excluded or hand-coded; they hold about half of large-project sites. Report the excluded share in every table.
2. **Completions below city level end in 2022.** Post-2022 analysis uses starts by tract or project-level Pipeline "Built" (undated). Permit clearance is never used as completion.
3. **Appeals cannot be measured from open data for older cohorts.** The appeal analysis is a hand-coded sample of OLT decisions, done by manual lookup.
4. **Selection.** Rezoning, minor variance and as-of-right are reported separately. As-of-right new construction is a minority in every size class.
5. **Net units.** Demolition-unit capture improves over time, so net series must be flagged or restricted to recent years. The 2026 Census will provide a net check (counts due 2027, UNVERIFIED).
6. **Built form.** Built GFA and existing units are estimated from massing heights and the Census.

**Fallback if Phase 2 finds the backcast unreliable:** drop as-of-date capacity. Run (a) a Pipeline cohort study of attrition and stage reached, by Official Plan designation, Secondary Plan or SASP, and (b) a census-tract panel (2010–2022 completions; 2010–2025 starts) on current zoning, with exposure measured only for tracts whose exceptions have no post-2013 amendments.
