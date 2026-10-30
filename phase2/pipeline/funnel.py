"""Pipeline table, cohort funnel, and time-to-event inputs."""
import numpy as np
import pandas as pd

STAGES = ["submitted", "approved", "permitted", "completed"]


def build_pipeline_table(apps, links, projects):
    """One row per application with its linked project's dates and units.

    route: 'rezoning_or_variance' / 'no_rezoning_recorded' / 'unknown' from requires_rezoning.
    A link to a project does not by itself prove the project was as-of-right or not; the route
    comes only from the application record. permit_without_approval flags data inconsistencies.
    """
    proj = projects[["project_id", "issued_date", "cleared_date", "net_units"]].rename(
        columns={"issued_date": "permit_issued_date", "cleared_date": "completed_date"})
    t = (apps.merge(links[["app_id", "project_id", "lag_days"]], on="app_id", how="left")
             .merge(proj, on="project_id", how="left"))

    rz = t["requires_rezoning"]
    is_true = rz.eq(True).fillna(False).astype(bool)
    is_false = rz.eq(False).fillna(False).astype(bool)
    t["route"] = np.select([is_true, is_false],
                           ["rezoning_or_variance", "no_rezoning_recorded"], default="unknown")
    t["stage_reached"] = np.select(
        [t["completed_date"].notna(), t["permit_issued_date"].notna(), t["outcome"].eq("approved")],
        ["completed", "permitted", "approved"], default="submitted")
    t["permit_without_approval"] = t["permit_issued_date"].notna() & ~t["outcome"].eq("approved")
    return t


def funnel_by_cohort(table, cfg, by=("route",)):
    """Counts reaching each stage by submission-year cohort (and `by` columns).

    completed_share_naive divides by all applications regardless of follow-up, so it is biased
    downward for recent cohorts; use survival.cumulative_incidence for rates. min_follow_up_years
    is the shortest follow-up of any application in the cohort.
    """
    t = table.copy()
    t["cohort_year"] = t["submitted_date"].dt.year
    reached = t["stage_reached"]
    t["_approved"] = reached.isin(["approved", "permitted", "completed"])
    t["_permitted"] = reached.isin(["permitted", "completed"])
    t["_completed"] = reached.eq("completed")
    t["_units_completed"] = t["net_units"].where(t["_completed"], 0)

    keys = ["cohort_year", *by]
    out = t.groupby(keys).agg(
        n_apps=("app_id", "count"),
        n_approved=("_approved", "sum"),
        n_permitted=("_permitted", "sum"),
        n_completed=("_completed", "sum"),
        units_proposed=("units_proposed", "sum"),
        units_completed=("_units_completed", "sum"),
    ).reset_index()
    out["completed_share_naive"] = out["n_completed"] / out["n_apps"]
    year_end = pd.to_datetime(out["cohort_year"].astype(str) + "-12-31")
    out["min_follow_up_years"] = ((cfg.data_end - year_end).dt.days / 365.25).clip(lower=0)
    return out


def build_time_to_event(table, cfg, event_date_col, competing_mask, competing_date_col,
                        start_col="submitted_date"):
    """Durations (days) and event codes for survival.cumulative_incidence.

    event 1: event_date_col is recorded. event 2: competing outcome (competing_mask) with a
    competing_date_col date and no event date. event 0: censored at cfg.data_end. The event of
    interest wins if both are recorded (a refused application that still produced a completed
    project is counted as completed).

    Censored rows include approved projects that silently died: that attrition cannot be seen
    without an explicit cancellation record. A competing outcome with no date cannot be placed
    in time, so it is censored; `competing_missing_date` flags those rows because treating dead
    applications as still at risk overstates the completion rate. `invalid` flags negative
    durations and dates after cfg.data_end (usually a wrong data_end or a data error); drop them
    and report how many.
    """
    start = table[start_col]
    ev = table[event_date_col]
    comp_date = table[competing_date_col]
    has_event = ev.notna()
    comp_flag = pd.Series(np.asarray(competing_mask, dtype=bool), index=table.index) & ~has_event
    has_comp = comp_flag & comp_date.notna()

    end = ev.where(has_event, comp_date.where(has_comp)).fillna(cfg.data_end)
    duration = (end - start).dt.days
    code = np.select([has_event.to_numpy(), has_comp.to_numpy()], [1, 2], default=0)
    invalid = (duration < 0) | (end > cfg.data_end) | duration.isna()
    return pd.DataFrame({
        "app_id": table["app_id"],
        "duration_days": duration,
        "event": code,
        "invalid": invalid,
        "competing_missing_date": comp_flag & comp_date.isna(),
    })
