"""Run the Phase 2 pipeline.

    python run_pilot.py --synthetic            # end-to-end check against a known truth
    python run_pilot.py --synthetic --out out  # also write CSVs

Real data: fill the column mappings in pipeline/loaders.py from the verified Phase 1 data
dictionaries, build the four canonical tables, and call run(). Nothing is run on real data here.
"""
import argparse
from pathlib import Path

from pipeline import synthetic
from pipeline.config import PipelineConfig
from pipeline.funnel import build_pipeline_table, build_time_to_event, funnel_by_cohort
from pipeline.linking import aggregate_permits_to_projects, link_applications_to_projects, link_diagnostics
from pipeline.schema import validate
from pipeline.survival import cumulative_incidence
from pipeline.zoning import history_coverage, zoned_capacity, zoning_as_of


def run(parcels, zoning, apps, permits, cfg):
    parcels = validate(parcels, "parcels")
    zoning = validate(zoning, "zoning_versions")
    apps = validate(apps, "applications")
    permits = validate(permits, "permits")

    projects = aggregate_permits_to_projects(permits, cfg)
    links = link_applications_to_projects(apps, projects, cfg)
    table = build_pipeline_table(apps, links, projects)

    z = zoning_as_of(table[["app_id", "parcel_id", "submitted_date"]], zoning, "submitted_date")
    table = (table.merge(z[["app_id", "zone_code", "max_fsi", "max_height_m", "zoning_matched"]],
                         on="app_id", how="left")
                  .merge(parcels, on="parcel_id", how="left"))
    table = zoned_capacity(table, cfg)

    tte = build_time_to_event(table, cfg, "completed_date",
                              table["outcome"].isin(["refused", "withdrawn"]), "decided_date")
    ok = ~tte["invalid"]
    cif = cumulative_incidence(tte.loc[ok, "duration_days"], tte.loc[ok, "event"], cause=1)

    return {
        "projects": projects, "links": links, "table": table, "time_to_event": tte,
        "cohort_funnel": funnel_by_cohort(table, cfg), "cif": cif,
        "link_diagnostics": link_diagnostics(apps, projects, links),
        "zoning_history": history_coverage(zoning),
        "zoning_match_rate": float(table["zoning_matched"].mean()),
        "parcel_match_rate": float(table["lot_area_m2"].notna().mean()),
        "n_invalid_durations": int(tte["invalid"].sum()),
        "n_competing_missing_date": int(tte["competing_missing_date"].sum()),
    }


def _synthetic_report(result, data, horizons_years=(3, 5, 8)):
    from pipeline.survival import cif_at
    truth = data.truth
    table = result["table"]
    naive = float((table["stage_reached"] == "completed").mean())
    print(f"\n{'horizon':>8} {'truth':>8} {'CIF est':>8}")
    for h in horizons_years:
        days = h * 365.25
        t = float((truth["latent_complete_days"] <= days).mean())
        e = float(cif_at(result["cif"], [days])[0])
        print(f"{h:>6}y {t:>8.3f} {e:>8.3f}")
    print(f"\nnaive completed share (all apps, any follow-up): {naive:.3f}  <- biased low by censoring")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synthetic", action="store_true", help="run on synthetic data with a known truth")
    ap.add_argument("--n-parcels", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None, help="directory for CSV outputs")
    args = ap.parse_args()

    if not args.synthetic:
        raise SystemExit("Real-data loading is not implemented: fill pipeline/loaders.py mappings from the "
                         "verified Phase 1 data dictionaries, then call run(). Use --synthetic to test.")

    data = synthetic.generate(n_parcels=args.n_parcels, seed=args.seed)
    cfg = PipelineConfig(data_end=data.data_end)
    result = run(data.parcels, data.zoning_versions, data.applications, data.permits, cfg)

    print("link diagnostics:", result["link_diagnostics"])
    print("zoning history:", result["zoning_history"])
    print("zoning match rate:", round(result["zoning_match_rate"], 3))
    print("parcel match rate:", round(result["parcel_match_rate"], 3))
    print("invalid durations dropped:", result["n_invalid_durations"])
    print("refused/withdrawn with no decision date (treated as censored):", result["n_competing_missing_date"])
    _synthetic_report(result, data)

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        result["cohort_funnel"].to_csv(args.out / "cohort_funnel.csv", index=False)
        result["cif"].to_csv(args.out / "cif.csv", index=False)
        print(f"\nwrote CSVs to {args.out}/")


if __name__ == "__main__":
    main()
