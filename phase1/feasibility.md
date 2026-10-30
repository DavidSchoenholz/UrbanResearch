# Phase 1 feasibility: Toronto zoning → application → approval → permit → completion

Prepared 2026-10-30. Descriptive and associational only; no causal claims.

## 0. Access limitations (read first)

- **Web search worked; opening pages mostly did not.** The session's network policy blocked every primary host I tried: `ckan0.cf.opendata.inter.prod-toronto.ca`, `open.toronto.ca`, `www.toronto.ca`, `www150.statcan.gc.ca`, `www.ontario.ca`, `www03.cmhc-schl.gc.ca`, `geohub.lio.gov.on.ca` and `olt.gov.on.ca`. Only `github.com` and `raw.githubusercontent.com` opened.
- **So no primary source was "opened and verified".** Each claim below carries one of three labels:
  - **[S]**: seen in a search-engine excerpt of the cited primary URL. The page was not opened, so the claim is not fully verified.
  - **[G]**: read in a third-party GitHub file that was opened. That is a secondary source.
  - **[R]**: recalled from background knowledge and not opened. Treat [R] as **UNVERIFIED**.
- **Code was runnable but no data was downloaded**, so no counts, match rates or coverage years come from my own computation.
- **Re-running.** Phase 1 should be re-run with these hosts allowed (environment Network access → Allowed domains; see https://code.claude.com/docs/en/cloud-environments#network-access): `ckan0.cf.opendata.inter.prod-toronto.ca`, `open.toronto.ca`, `www.toronto.ca`, `www03.cmhc-schl.gc.ca`, `www.cmhc-schl.gc.ca`, `www12.statcan.gc.ca`, `www150.statcan.gc.ca`, `www.ontario.ca`, `ero.ontario.ca`, `olt.gov.on.ca`.

---

## 1. Operational definitions

### 1.1 Zoned capacity
**Definition.** Zoned capacity is the maximum residential gross floor area (GFA) permitted on a lot by the zoning in force on a reference date, converted to units. Unused capacity is that capacity minus the existing built GFA.

**Formulas.**
- `cap_GFA_far = FSI_TOTAL × lot_area`.
  - `FSI_TOTAL` is the Zoning Area layer's numeric field. [S: the ZN_ZONE/FSI_TOTAL schema was seen in a third-party ArcGIS copy, https://services7.arcgis.com/AHJOWTX3sFcnmA9U/ArcGIS/rest/services/MidtermAssignment_WFL1/FeatureServer/3]
  - `lot_area` comes from the Property Boundaries polygon (D13).
- `cap_GFA_env = lot_area × lot_coverage × floors`.
  - `floors = floor(HT / 3.0 m)`, where HT comes from the Height Overlay (or the zone label). The by-law says the permitted height is "the numerical value following the letters 'HT' on the Height Overlay Map" [S: https://www.toronto.ca/zoning/bylaw%5Famendments/ZBL_NewProvision_Chapter900_31.htm].
  - `lot_coverage` comes from the Lot Coverage Overlay where one applies.
  - The 3.0 m storey height is an assumption.
- `cap_GFA = min(cap_GFA_far, cap_GFA_env)`, using whichever constraints exist.
- `cap_units = cap_GFA / g`, where `g` is an assumed gross area per unit (for example 85 m² for apartments). Test sensitivity to `g`.
- **Count rule for low-rise residential zones.** Here the binding constraint is the permitted unit count, not FSI. After the multiplex amendment (in effect 2023-05-12) up to 4 units are permitted in Neighbourhoods [S: https://www.toronto.ca/multiplex], so `cap_units = max(count rule, GFA rule)`.

**Existing built measure.** `built_GFA ≈ footprint_area × floor(elez / 3.0 m)`, using 3D Massing footprints, whose `elez` height attribute is in metres [S: https://library.torontomu.ca/gmdc/2015/01/20/toronto3dmassing/]. Existing units would come from 2021 Census dwellings at DA level (D22).

**Building data needed.**
- **Needed:** footprint, height or storeys, GFA and existing unit count per building.
- **Openly available:** footprint + height only (3D Massing, LIDAR-derived, "illustrative only" disclaimer [S]).
- **Missing:** GFA and unit counts per building are not in any open dataset I found. MPAC assessment data is not open [R]. Built GFA is therefore an estimate, and parcel-level unused capacity carries measurement error.

**Not captured by the layers.**
- Chapter 900 site-specific exceptions can override FSI and height. Only the exception reference is in the layer [S: https://www.toronto.ca/legdocs/bylaws/2013/law0569-schedule-a-vol1-ch1-800.pdf]; the text is in PDFs.
- Holding symbols "(H)" restrict use until conditions are met [S, same source].
- Secondary Plans and Site and Area Specific Policies (SASPs) are not zoning and have no confirmed open GIS layer (D12).
- Minister's Zoning Orders are not in City layers (D25).

**Recommendation.** Flag lots with an exception, holding symbol or MZO, and either exclude them from capacity estimates or hand-code them.

### 1.2 As-of-right vs. rezoning vs. minor variance
For each permit-project (§1.3), search for planning applications on the same parcel, either within 10 years before the project's first `APPLICATION_DATE` or ending in that window.

| Class | Rule (data fields) |
|---|---|
| **Rezoning** | Linked to a Development Applications record of type OZ (Official Plan / Zoning By-law Amendment) [S: type codes per https://github.com/Planning-Toronto/alternative-application-information-centre, [G]] |
| **Minor variance** | No OZ, but linked to a Committee of Adjustment MV record (D05) |
| **As-of-right** | No OZ or MV link. Site Plan (SA), subdivision (SB), part-lot (PL) or condo (CD) links do not change zoning, so the project stays as-of-right but is flagged as "site-plan controlled". |

- **Selection bias.** Rezoning applications are selected on zoning being non-binding in the developer's favour. Each class must therefore be reported separately and never pooled when relating zoning to activity.
- **Cross-check for rezonings.** For rezoning projects, the relevant "zoning" is (a) the pre-application zoning and (b) the approved site-specific by-law. Source (b) from the by-law archive (D09) or the Chapter 900 exception number.
- **Linkage is spatial.** A planning-application number field in the permit data was not found [G: 32-column dictionary, https://raw.githubusercontent.com/Mahmoud-O/toronto-building-permits/main/docs/data_dictionary.md], so the link must be made spatially. The match rate is unknown until it is measured.

### 1.3 Project (aggregating permits)
1. Union Cleared (D01, D02) and Active (D03) permits.
   - Deduplicate on `PERMIT_NUM` + `REVISION_NUM` + `PERMIT_TYPE`. A third party found the first two alone left 5,065 duplicates, and adding the third cut that to 24 [G: https://github.com/paramsngh/toronto-building-permits].
   - Keep the latest revision.
2. Build a permit-stream key from `PERMIT_NUM` minus its trailing sub-type code. The year + application-number stem is a third-party inference [G].
3. Drop trade and secondary permits (plumbing, HVAC, drain, fire) when a main building permit exists on the stream. Drop partial and conditional permits as duplicates. A third party removed 270,998 secondary duplicates this way [G].
4. Merge streams into a project when they share `GEO_ID` (or a normalized address) and their activity windows overlap within 24 months. This catches separate shoring, foundation and above-grade permits.
5. Set project attributes:
   - units = max `DWELLING_UNITS_CREATED` across the New Building / main permits (max, not sum);
   - first application = min `APPLICATION_DATE`;
   - first issue = min `ISSUED_DATE`;
   - project clearance = max `COMPLETED_DATE` among the main permits.
6. For Planning-Act projects, overwrite the project ID with the Development Pipeline `Application Number` where a spatial match exists [G: https://raw.githubusercontent.com/Nshipyard/toronto-development-pipeline/main/scripts/build_pipeline.py].

Validation: hand-check a stratified sample of 100 projects against AIC and permit descriptions.

### 1.4 Completion
| Measure | Source and field | What it is | Geography |
|---|---|---|---|
| **CMHC completion** | Starts & Completions Survey (D20, D21) | Site-visit confirmed. A unit "may be counted as completed" with up to 10% of work remaining [S: CMHC methodology URL in D21]. Gross new units only. | CSD/CMA; census tracts listed as a portal geography [S], post-2023 availability UNVERIFIED |
| **City "Built"** | Development Pipeline `'Pipeline Status' = 'Built'` (D06) | "Ready for occupancy and/or completed" [S: 2020 pipeline PDF] | Project point |
| **Permit cleared** | `COMPLETED_DATE` / `STATUS` in Cleared Permits (D01) | Administrative closure of the permit file. It can lag occupancy by years and can occur without construction [R]. **Not a completion measure.** | Address |
| **Net stock change** | Census `Total private dwellings` (D22) | Net of demolitions and conversions | DA/CT, every 5 years |

**Reconciliation plan.**
- Compare annual totals of each measure for 2017–2025 at city level, and by CT where CMHC allows.
- City dashboards already report completions as "reported by CMHC" [S: https://www.toronto.ca/wp-content/uploads/2025/06/904a-city-planning-municipal-housing-target-dashboard.pdf]. The City itself treats CMHC as the authoritative completions count.
- Primary measure: CMHC completions. Secondary measure: City "Built" for project-level timing.

---

## 2. Verification items

| Item | Finding | Status |
|---|---|---|
| Zoning in force at application date | The open Zoning By-law layer is a current snapshot. A catalogue copy says amendments run "up to June 18th, 2023" [S: https://data.urbandatacentre.ca/catalogue/city-toronto-zoning-by-law]. A 2014 vintage exists ("current as of September 15, 2014") [S: https://library.torontomu.ca/gmdc/2014/10/02/toronto-zoning-shapefiles-available/]. No version history was found. Amending by-laws with numbers and dates are in the by-law archive (D09) and the per-chapter amendment pages (D08). | Partially reconstructable (see §3 Q1) |
| Did 569-2013 fully replace pre-amalgamation by-laws? | **No.** It was enacted 2013-05-09 and appealed under s.34(19) [S: https://www.toronto.ca/city-government/planning-development/zoning-by-law-preliminary-zoning-reviews/zoning-by-law-569-2013/]. "Nothing in this By-law repeals the provisions of the Former General Zoning By-laws"; it supersedes them only where it applies. Lands hatched on the Section 990.10 map stay under former by-laws [S: https://www.toronto.ca/legdocs/bylaws/2013/law0569-schedule-a-vol1-ch1-800.pdf]. "Some regulations … remain under appeal with the Ontario Land Tribunal" under PL130592 / OLT-22-002465 [S: https://www.toronto.ca/city-government/planning-development/zoning-by-law-preliminary-zoning-reviews/zoning-by-law-569-2013-2/omb-decisions/]. | [S] |
| Exceptions, holding, Secondary Plans, MZOs in open data | Exceptions: Chapter 900, referenced by "x" numbers on the map; text only in PDFs. Holding: "(H)" before the zone symbol [S, same PDF]. The exception and holding attribute names in the GIS layer are **UNVERIFIED**. Secondary Plans/SASPs: no open GIS layer found, only Official Plan PDFs [S: D12]. MZOs: published as O. Regs / ERO notices, for example O. Reg. 561/24 (65 Rexdale Blvd) and Zoning Order 005-2026 (1875 Steeles Ave W) [S: D25]. Not found in City layers. | [S]; attribute names UNVERIFIED |
| OLT role and appeal data | OLT Case Status shows active cases plus cases closed within the last 2 years. Decisions are online for 10 years and also on CanLII [S: https://olt.gov.on.ca/case-status]. **No open bulk appeal dataset was found.** Bill 23 and Bill 185 (royal assent 2024-06-06 [S: Aird & Berlis summary]) narrowed third-party appeals [S, secondary]. CoA appeals in Toronto go to TLAB [S, secondary; start date UNVERIFIED]. | Appeal data not open as a dataset |
| Gross vs. net; units vs. buildings | `DWELLING_UNITS_LOST` "rarely filled in" [G]. CMHC counts gross new units on new foundations [S: D21]. The Census measures net stock. Permits record units per permit, not per building, so the project roll-up in §1.3 is needed. | [G]/[S] |
| Boundary and definition changes | Ward boundaries changed to 25 wards in 2018 [R]. Neighbourhoods moved from 140 to 158 [R]. CMHC geographies are redefined every 5 years, and completions have been collected only in CMAs since 2023-01-01 [S: D21]. The pipeline uses a rolling 5-year window, and edition totals are not comparable: 854,898 units in 2024 vs. ~791,000 in 2025, despite a stated "+7%" [S: 2024/2025 bulletins]. | Mixed |

**Policy time markers.**

| Date | Event | Source / status |
|---|---|---|
| 1998-01-01 | Amalgamation | [R] UNVERIFIED |
| 2013-05-09 | 569-2013 enacted | [S] toronto.ca 569-2013 page |
| 2014-09-15 | Earliest open 569-2013 GIS snapshot | [S] TMU GMDC |
| 2018 / 2019-07-16 | Laneway suites (sources conflict) | UNVERIFIED |
| 2022-02-02; 2022-07-04 | Garden suites adopted; OLT dismissed appeal, so the by-law is in force | [S] https://www.toronto.ca/news/garden-suites-permitted-in-toronto-after-ontario-land-tribunal-dismisses-appeal/ |
| 2022-11-28 | Bill 23 royal assent | [S] legislature record via myparliament.ca and law-firm notes; one source says Nov 29; ontario.ca not opened |
| 2023-05-10 / **2023-05-12** / 2023-06-14 | Multiplex (≤4 units): Council adoption / zoning in effect / OPA in effect | [S] https://www.toronto.ca/multiplex |
| 2024-06-06 | Bill 185 royal assent | [S] law-firm note |
| 2024-11-13 | As-of-right mid-rise on Avenues adopted | [S] toronto.ca Avenues study page |
| 2025-08-15 | Province approves PMTSAs, so inclusionary zoning (By-law 941-2021) can take effect | [S] secondary |

**Recommended marker.** Use the **multiplex zoning in effect on 2023-05-12** as the cleanest marker.
- It is a single citywide as-of-right change, and it affects low-rise permits directly, with no rezoning needed.
- Garden suites (in force 2022-07-04) are a close preceding marker and must be modelled jointly.
- Bill 23 is a poor marker, because its provisions phased in at different dates [S: Aird & Berlis "what's in force"].

---

## 3. Feasibility gate

**Q1. Can zoning be obtained as of each application date?**
**Partially; not directly.** The open layer is a current snapshot with no version history. Three methods could recover past zoning:
- (a) a 2014-09-15 baseline (D11);
- (b) backcasting, by removing site-specific amending by-laws (D09) enacted after the application date;
- (c) for OZ applications, the "existing zoning" stated in staff reports.

Method (b) is feasible for the 569-2013 general provisions plus Chapter 900 exceptions, but it means manual or NLP extraction from PDFs. Lands under former by-laws and provisions under appeal cannot be backcast reliably.

*Mitigation:* restrict zoned-capacity analyses to lots whose exception and zone label did not change between the application date and today. Identify those lots by the absence of any post-date amending by-law on the parcel, and report the excluded share.

**Q2. Is there a project-level link between applications and permits?**
**Partially.**
- The City's Development Pipeline is explicitly project-level: it "brings together Planning application and building permit data" [S: D06]. It carries `'Application Number'`, which joins to Development Applications `APPLICATION#` [G].
- It covers only larger Planning-Act projects in a rolling 5-year window. Whether it exposes permit numbers is UNVERIFIED.
- Permit records have no application-number field [G], so as-of-right and minor-variance projects can be linked only by address, `GEO_ID` or space. The match rate is to be measured.

**Q3. Is there a completions measure finer than the whole city?**
**Yes, with caveats.**
- City "Built" status per Pipeline project (point level; Planning-Act projects only) [S].
- CMHC completions by census tract: the portal lists CT as a geography [S]. Post-2023 CT availability and suppression are UNVERIFIED.
- Census DA/CT net dwelling change every 5 years.
- Permit clearance is not a completion measure.

**Q4. How many years have consistent coverage across all four stages?**
Best estimate from unverified coverage:

| Stage | Coverage |
|---|---|
| Permits | 2001–present [G: mirrored metadata "from 2001 onwards"] |
| Zoning (569-2013, GIS) | Snapshot from 2014-09-15 [S] |
| Development applications | ~10 years for OZ/SA, ~5 years for MV/CO in third-party tools [G]; true start UNVERIFIED |
| Pipeline | Rolling 5 years (2021–2025 in the current edition); earlier editions as PDFs [S] |
| CMHC completions | Long series [S] |

The binding constraints are zoning (2014+), application coverage (about 2016+ if 10 years) and completions lag. High-rise projects take several years from application to completion [R].

**Recommended study period:**
- **Application cohorts 2016–2020**, with outcomes observed through **2025-12-31**. This allows at least 5 years of follow-up for completion and attrition.
- **Low-rise / as-of-right permits 2019-05 to 2026-09**, for the pre/post multiplex descriptive comparison: 4 years before and about 3.4 years after 2023-05-12.

*Justification:* this is the latest window where zoning (2014 baseline + amendments), applications and permits are all in open data, and where most cohorts have had time to complete. Confirm the start year once D04 is downloaded.

**Q5. What is the finest reliable unit of analysis?**
**Census tract (2021 boundaries)** for analyses covering all four stages including completions. **Parcel / project** for application → approval → permit timing and attrition, and for the Pipeline subset's completions. Wards are too coarse and changed in 2018 [R].

---

## 4. Verdict: **GO WITH LIMITS (provisional)**

The verdict is provisional: no primary source was opened. It becomes final only after the checklist in summary.md passes with network access.

Limits:
1. **No true as-of-date zoning.** Use the backcast or "stable-zoning lots" restriction and report the excluded share. Results on lots with exceptions, holding symbols, MZOs or former by-laws are excluded or hand-coded.
2. **Application → permit linkage is spatial**, except for Pipeline projects. Report match rates, and treat unmatched permits as "as-of-right (presumed)".
3. **Completions.**
   - CMHC completions at CT are the primary measure.
   - Project-level "Built" applies only to Planning-Act projects.
   - Permit clearance must not be used as completion.
4. **Net units.**
   - Permit `DWELLING_UNITS_LOST` is unreliable.
   - Net change comes from linked demolition permits plus the Census (2021→2026; 2026 counts due 2027-02-10 [S: https://www.statcan.gc.ca/sites/default/files/documents/2026-09/census-2026-key-content-release-schedule.pdf]).
5. **Appeals (OLT) have no open dataset.** Appeal status and timing can only be observed for a hand-coded sample from OLT decisions, collected by manual lookup rather than scraping until terms are checked.
6. **Built-form data has no GFA or unit counts.** Unused capacity is approximated from 3D Massing heights.

**Fallback if the checks fail** (for example, the development applications history is short or the CT completions are suppressed):

> Use a citywide plus CT-level descriptive time series around the 2023-05-12 multiplex marker, limited to as-of-right low-rise permits (permits → CMHC completions). Add a parcel-level Pipeline cohort study (application → Built) without zoning-capacity terms.
