# Hamilton

Zoning and housing research for the City of Hamilton, Ontario. It follows the Toronto Phase 1
(branch `claude/determined-lovelace-oc32xm`, folder `phase1/`) and adds a zoning-per-parcel map.

| Folder | What is in it |
|---|---|
| [`phase1/`](phase1/summary.md) | Data inventory and feasibility assessment for zoning → application → permit → completion. Start with `summary.md`. |
| [`parcel_zoning/`](parcel_zoning/README.md) | The zone of every parcel (table, validation, scripts) and a static web map in `parcel_zoning/site/`. |
| [`LOG.md`](LOG.md) | Dated research log: what was done, found and decided, and where to pick up next. |

**Data date:** City layers downloaded 2026-10-30.

**Headline:** 177,751 of 177,753 parcels matched to a zone; 4.2% are split-zoned; 27% are still
governed by a former municipality's zoning by-law rather than city-wide By-law 05-200.

To view the map locally:

```bash
cd hamilton/parcel_zoning/site && python3 -m http.server 8000
```

Then open <http://localhost:8000>.
