# Phase 1 summary: Toronto zoning and the housing pipeline

**Verdict: GO WITH LIMITS (provisional).** The verdict is provisional because no primary source page could be opened in this session. The environment's network policy blocked the City of Toronto, CMHC, StatCan, Ontario and OLT hosts. Every claim comes from search-engine excerpts of primary URLs [S], third-party GitHub files that were opened [G], or recall [R, UNVERIFIED]. Nothing is "opened and verified." The full evidence is in `feasibility.md` and the dataset details are in `inventory.csv`.

## Key limitations
1. **Zoning cannot be pulled as of the application date.**
   - The open Zoning By-law layer is a current snapshot. A catalogue copy says it includes amendments "up to June 18th, 2023" [S].
   - The only historical vintage found is from 2014-09-15 [S].
   - Past zoning has to be rebuilt by backcasting with amending by-laws from the PDF archive, or the analysis restricted to lots whose zoning has not changed.
2. **Zoning By-law 569-2013 did not fully replace the former by-laws.**
   - It was enacted 2013-05-09.
   - The former by-laws are "not repealed" and still govern the lands hatched on the Section 990.10 map.
   - Some 569-2013 provisions remain under OLT appeal (PL130592 / OLT-22-002465) [S].
3. **Applications and permits link at project level only for larger Planning-Act projects.** The Development Pipeline links them through `'Application Number'` = `APPLICATION#` [G]. Permit records have no application-number field [G], so as-of-right and minor-variance projects must be matched by address, `GEO_ID` or location.
4. **A cleared permit is not a completion.** The candidate measures are:
   - CMHC completions (site-visit based; a unit counts as complete with ≤10% of work left), at CMA, CSD and possibly census tract [S];
   - the City's "Built" status, for Pipeline projects only [S];
   - Census net dwelling change every 5 years.
5. **Net units are weak.** `DWELLING_UNITS_LOST` is "rarely filled in" [G], and CMHC counts gross units only.
6. **There is no open OLT appeal dataset.** The Case Status tool keeps closed cases for only 2 years, and decisions are online for 10 years [S]. Appeals can only be studied in a hand-coded sample.
7. **Definitions drift.**
   - The Pipeline uses a rolling 5-year window, and its 2024 and 2025 unit totals are not comparable [S].
   - Wards were redrawn in 2018 [R].
   - CMHC collects completions only in CMAs since 2023 [S].
8. **Built-form data has no GFA or unit counts.** 3D Massing provides footprints and heights (`elez`, in metres) [S], so existing GFA has to be estimated.

## Recommended frame (to confirm in Phase 2)
- **Study period:**
  - application cohorts 2016–2020 with outcomes observed to 2025-12-31;
  - an as-of-right low-rise permit window from 2019-05 to 2026-09 around the **multiplex zoning in effect 2023-05-12** [S].
- **Unit of analysis:** the 2021 census tract for analyses spanning all four stages; the parcel or project for stage-to-stage timing and attrition.
- **Classes:** rezoning (OZ), minor variance (CoA MV) and as-of-right, always reported separately because of selection bias.

## Must-verify checklist once the hosts are allowed
1. The CKAN `datastore_search` schema for the cleared permits, active permits, development applications, Committee of Adjustment and zoning datasets. Confirm field names, the earliest `DATE_SUBMITTED` / `APPLICATION_DATE`, and the licence.
2. Whether the Development Pipeline is an open download, and whether it contains permit numbers.
3. Census-tract completions in CMHC's Housing Market Information Portal after 2023, and the suppression rate.
4. The exception and holding attribute names in the Zoning Area layer, and whether the City archives past vintages.
5. The terms of use for the OLT Case Status tool and the Application Information Centre before any automated access. Neither was scraped.

Hosts to allow: `ckan0.cf.opendata.inter.prod-toronto.ca`, `open.toronto.ca`, `www.toronto.ca`, `www03.cmhc-schl.gc.ca`, `www.cmhc-schl.gc.ca`, `www12.statcan.gc.ca`, `www150.statcan.gc.ca`, `www.ontario.ca`, `ero.ontario.ca`, `olt.gov.on.ca` (environment settings → Network access; https://code.claude.com/docs/en/cloud-environments#network-access).

## Files
- `inventory.csv`: 28 datasets and sources, each with URL, publisher, licence, coverage, fields, limitations, join keys and provenance.
- `feasibility.md`: operational definitions, verification table, policy time markers, the five gate answers and the verdict.
