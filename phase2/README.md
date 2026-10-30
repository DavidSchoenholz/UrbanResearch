# Phase 2 skeleton: zoning -> application -> permit -> completion

Code scaffolding for studying how zoning relates to development applications, permits and
completed housing in Toronto. **It has only been run on synthetic data.** No real Toronto data
is loaded, and nothing here describes Toronto; the loaders are deliberately unfilled until the
field names are confirmed from verified data dictionaries (Phase 1 output).

## Quick start

```bash
pip install -r requirements.txt
python -m pytest -q                      # from this directory
python run_pilot.py --synthetic          # end-to-end run against a known truth
```

## Layout

| Module | Purpose |
|---|---|
| `pipeline/schema.py` | Canonical tables (applications, permits, zoning_versions, parcels) and validation |
| `pipeline/loaders.py` | Map raw columns onto the canonical schema; refuses to run with an unfilled mapping |
| `pipeline/linking.py` | Chain permits into projects; one-to-one link of applications to projects; match diagnostics |
| `pipeline/zoning.py` | Zoning in force **as of** a date; check whether history exists; crude zoned capacity |
| `pipeline/funnel.py` | Per-application pipeline table, cohort funnel, time-to-event inputs |
| `pipeline/survival.py` | Aalen-Johansen cumulative incidence (competing risks), Kaplan-Meier, bootstrap CI |
| `pipeline/reconcile.py` | Compare project-level completions with an aggregate series (e.g. CMHC) |
| `pipeline/spatial.py` | Optional geopandas point-in-parcel join |
| `pipeline/synthetic.py` | Synthetic data with a known ground truth, for testing |
| `run_pilot.py` | `run()` wires the steps together; CLI runs the synthetic check |

## Design decisions that matter

- **Zoning as of the application date**, never today's zoning. `history_coverage` tells you
  whether the zoning table has any history; if not, the join degenerates into a snapshot.
- **Rezoning is separated from as-of-right** via `requires_rezoning`, because applications are
  selected on zoning not permitting what the developer wants. An unlinked project is *not*
  necessarily as-of-right; it may be a failed link.
- **Permits are aggregated to projects**; a project is complete only when all observed permits
  are cleared. Unit counts use `max` by default to avoid double-counting repeated units.
- **Completion rates use cumulative incidence, not shares.** Recent cohorts have not had time to
  complete; the naive share is biased low (the synthetic run shows this), and treating refusals
  as censoring would bias the other way.

## Assumptions to replace with evidence (`pipeline/config.py`)

`permit_chain_gap_days`, `link_before_days`, `link_max_lag_days`, `unit_agg`,
`avg_unit_floor_area_m2`, `residential_efficiency`. `data_end` must be the date the sources are
*complete through*, not the download date.

## Known limitations

- Link failures look like non-completion: unlinked approved applications stay censored forever,
  biasing completion low. Watch `share_approved_apps_linked`.
- Approved projects that silently die are invisible without a cancellation record.
- Refused/withdrawn applications with no decision date are treated as censored (flagged in
  `competing_missing_date`), which biases completion high.
- Existing floor area is normally a current snapshot, so it understates unbuilt capacity for past
  applications. Zoned capacity from floor-area ratio alone is an upper bound.
- Independent censoring requires stable timelines across calendar time; compare cohorts and
  policy periods rather than only pooling. Bootstrap intervals ignore spatial clustering.
- The synthetic test shows the estimators work when the assumptions hold. It says nothing about
  how well they hold in real data.

## Next steps (need real data)

1. Fill `loaders.mapping_template` for each verified dataset; recode categorical values.
2. Run `history_coverage` on the zoning table (the Phase 1 feasibility question).
3. Choose `data_end`, the unit of analysis, and a study period; re-check the config assumptions.
4. Run `reconcile_with_aggregate` against the completions series before trusting permit clearance
   as a completion measure.
