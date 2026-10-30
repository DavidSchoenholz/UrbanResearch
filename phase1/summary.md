# Phase 1 summary: Toronto zoning and the housing pipeline

**Verdict: GO WITH LIMITS.** This is the second pass, after network access was opened. I read every Toronto open-data record through the City's open-data API and downloaded and profiled the files. I also fetched the City of Toronto, CMHC and OLT pages and pulled CMHC tables directly. StatCan (HTTP 403/503) and the Ontario legislature and e-Laws pages (403, or script-rendered) still could not be read, so claims that depend on them are marked UNVERIFIED.

## Key limitations
1. **Census-tract completions end in 2022.** CMHC returns census-tract completions for 2010–2022. Exports for 2023 onward say "This data series is now archived". Toronto-wide completions continue to 2025, and census-tract *starts* continue to 2025. The census tracts reconcile with the city total (16,292 vs. 16,296 in 2022).
2. **Zoning history is only partly recoverable.**
   - The open zoning layer is one snapshot, "updated to include amendments up to June 18th, 2023".
   - Backcasting is possible for 569-2013 lands: 27.5% of 5,247 Chapter 900 exceptions cite their amending by-law with its year. The Wayback Machine also holds copies from 2023-04 and 2024-06.
   - Lands still under former by-laws have no GIS. That covers 50.8% of 50+ unit new-building permit sites.
3. **569-2013 did not fully replace the former by-laws.** The City says it "does not fully replace all older bylaws in every area". About 1,500 low-rise parcels were excluded, and 2026 by-laws are still bringing lands in. Some 2013 provisions remain under OLT appeal (PL130592 / OLT-22-002465).
4. **Cleared permits are not completions.** Units on cleared permits equal 22–62% of CMHC completions each year 2002–2024 (correlation 0.23). The data has no 2007 clearances and a 2025 batch-closure spike.
5. **Appeal history is overwritten.** Development Applications show current status only: 20–29% of 2020–2025 rezoning files show an appeal state, but only 0–5% of 2008–2015 files. There is no open OLT dataset; Case Status keeps cases two years after closure. Committee of Adjustment appeals are open (Toronto Local Appeal Body (TLAB) data, from 2017).
6. **Application → permit links exist only for large Planning-Act projects.** The Development Pipeline links them for projects at or above the Site Plan threshold ("fewer than 10 units" are excluded). Its `Application Number` matches 96.9% of application records, and 98% of "Built" projects match a permit address. It has no permit IDs and no built dates. Everything else links by address.
7. **Selection is severe.** Among 2018–2025 new-residential permits, 87% of 50+ unit projects are rezoning-linked, and 72–79% of 1–4 unit projects are linked to a minor variance (upper bounds).
8. **Net units are weak.** `DWELLING_UNITS_LOST` is filled on about 35% of permits, and the fill rate rises over time.

## Recommended frame (Phase 2 to confirm)
- **Period:**
  - cohorts 2013-05-09 to 2017, with outcomes to 2022 (census-tract completions);
  - an extension to 2025 using permits and census-tract starts;
  - a multiplex marker window around 2023-05-10. New 2–6 unit permits went from 47 in 2022 to 243 in 2025.
- **Unit of analysis:** address/parcel for timing and attrition; 2021 census tract for completions.

## Corrections to the first (offline) pass
- 3D Massing heights are `AVG_HEIGHT`/`MAX_HEIGHT`, not `elez`. Annual vintages exist for 2016–2023 and 2025.
- Open GIS layers exist for Secondary Plans (2015 vintage) and SASPs (Dec 2025).
- The Development Pipeline is an open dataset; `Active` merges three stages.
- The holding and exception field names are `ZN_HOLDING`/`HOLDING_ID`/`ZN_EXCPTN`/`EXCPTN_NO` (now verified).
- The Height Overlay field is `HT_LABEL`, not `HT_HEIGHT` as the readme says.

## Still UNVERIFIED
- Bill 23 and Bill 185 royal assent dates (2022-11-28; 2024-06-06).
- The in-force dates of the multiplex (2023-05-12) and garden-suite (2022-07-04) by-laws.
- StatCan Census fields and release dates.
- The geography of CMHC's conversions and demolitions tables.
- Whether files from before 2023 can be retrieved from the Wayback Machine.

## Files
- `inventory.csv`: 30 sources, with fields, coverage, limitations, join keys and provenance.
- `feasibility.md`: definitions, verification, gate answers and verdict.
- `scripts/`: profiling and linkage code. Data is not committed.
