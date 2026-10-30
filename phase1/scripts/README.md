# Phase 1 scripts

These scripts produced the coverage and linkage figures in `../feasibility.md`. Data files are not committed. Download them into a scratch directory (`RAW`) first, using the resource URLs listed in `../inventory.csv`, and pass the paths as arguments.

```bash
python3 -I pkgsum.py META_DIR                       # CKAN package metadata summary (package_show JSON files)
python3 -I build_permits.py RAW DATA/permits_all.parquet
python3 -I profile2.py DATA/permits_all.parquet DATA/bld_stems.parquet
python3 -I link.py RAW DATA                          # application <-> pipeline <-> permit address linkage
python3 -I spatial.py RAW DATA                       # GEO_ID -> address points -> zoning polygons
python3 -I reconcile.py DATA                         # permits vs CMHC starts/completions (needs DATA/cmhc/ts_csd_*.csv)
python3 -I h2t.py page.html > page.txt               # HTML-to-text helper for primary web pages
```

CMHC series were pulled from `https://www03.cmhc-schl.gc.ca/hmip-pimh/en/TableMapChart/ExportTable` using HTTP POST with these table IDs:
- `1.1.2.11`: completions by census tract;
- `1.1.1.11`: starts by census tract;
- `1.2.2`: historical completions;
- `1.2.1`: historical starts.

Geographies used: `GeographyId=2270` with `GeographyTypeId=3` for the Toronto CMA, and `GeographyId=3520005` with `GeographyTypeId=4` for the Toronto CSD. The table IDs come from the open-source `cmhc` R package (github.com/mountainmath/cmhc, `R/cmhc_tables.R`).

Requires pandas, pyarrow, geopandas, pyogrio, shapely.
