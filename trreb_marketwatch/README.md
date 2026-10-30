# TRREB Market Watch: Toronto price log and map

Pulls the **free, publicly linked** TRREB reports, parses them into tidy tables, and builds a
self-contained HTML page: a neighbourhood price map plus a district price log.

> **Copyright.** TRREB's site states that its content is copyright TRREB. The downloader honours
> `robots.txt` and rate-limits itself, and this is meant for private analysis. **Downloaded PDFs and
> the derived CSV/HTML contain TRREB's figures: they are git-ignored here, so do not commit or
> republish them** without checking TRREB's terms. Only code is in this repository.
> This does not touch TRREB's licensed MLS data (individual sales), which is not public.

## Run it

```bash
pip install -r requirements.txt          # also needs poppler's pdftotext on the PATH
python fetch.py boundaries  --data-dir data
python fetch.py marketwatch --data-dir data     # ~180 monthly PDFs, 1.5 s apart (about 15 min)
python fetch.py community   --data-dir data     # 45 Toronto quarterly PDFs
python build.py --data-dir data --out out       # about 1.5 min; writes out/toronto_prices.html
python -m pytest -q
```

## What it produces (`out/`)

| File | Contents |
|---|---|
| `district_monthly.csv` | Monthly, all home types, per TRREB district (C01...E11) and `CITY`: sales, dollar volume, average and median price, new and active listings, days on market |
| `community_quarterly.csv` | Quarterly, per TRREB community in Toronto |
| `community_match.csv` | Which TRREB community matched which City neighbourhood, and which did not |
| `parse_report.csv` | Per-file parse status and the reason for any failure |
| `toronto_prices.html` | Interactive page: choropleth by neighbourhood (quarter and measure selectable), price log per neighbourhood, district chart (up to four at once), table views, light/dark mode |

## How the data is checked

Every parsed row is validated, and a file that fails is dropped and reported, never patched:

- **Checksum:** `sales x average price` must match `dollar volume` (within 2%), which confirms the
  columns lined up. This caught every parsing bug below.
- **Totals:** the Toronto districts must sum exactly to the City of Toronto row.
- Spot checks against figures read by eye from the PDFs matched exactly.

Results on the real archive: **182 of 183** monthly reports (July 2011 to September 2026) and **45 of 45**
community reports validate.

### Quirks found in the PDFs (all handled, with tests)
- Some reports print a stale copy of the previous row's values over each row, so rows are rebuilt from
  word coordinates (`pdftext.py`) and stale words are dropped only when they conflict with a different word.
- A placeholder word (`Abc`) is embedded mid-row in some reports.
- Communities with two or fewer sales are printed as short rows containing listing counts, not prices; only the
  sales count is kept (reading them by position would have invented prices).
- A zero price with zero sales means "not reported", not $0.
- Two-digit years of 90 or more are 1990s (the archive reaches back to 1998).

## Limitations

- **`mw2205` (May 2022) fails validation** (every cell is printed twice) and is excluded; the chart shows a gap.
- **Reports before July 2011 are not parsed.** They use a different layout (supporting them needs a second parser).
- **Districts have no published boundaries**, so they appear as a chart and not on the map.
- **Community data starts in 2022 Q4** (the earliest Toronto community report available), so the map has 15 quarters.
- **Only 116 of 158 neighbourhoods are mapped.** Communities are matched to City neighbourhoods by *exact*
  normalized name only; the rest are listed on the page, not fuzzy-matched. Some TRREB communities cover several
  neighbourhoods (for example the waterfront communities) or use different names.
- Averages are not quality-adjusted (a month with more expensive sales lifts the average). TRREB suppresses small
  communities, and says its quarterly community figures may not match sums of its monthly reports.
- Parsing depends on TRREB's PDF layout; a redesign will surface as validation failures in `parse_report.csv`.

Neighbourhood boundaries are City of Toronto Open Data (Open Government Licence - Toronto).
