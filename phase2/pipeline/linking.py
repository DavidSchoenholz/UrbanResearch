"""Aggregate permits to projects and link applications to projects."""
import numpy as np
import pandas as pd


def aggregate_permits_to_projects(permits, cfg):
    """Chain permits on the same parcel into projects.

    A permit starts a new project when more than cfg.permit_chain_gap_days separate its
    issue date from the previous permit's on that parcel. A project counts as cleared only
    when every one of its observed permits is cleared (cleared_date = latest clearance);
    otherwise cleared_date is NaT. Permits issued after the data cutoff are not observed,
    so a project can look complete while a later permit is still to come.
    """
    p = permits.sort_values(["parcel_id", "issued_date", "permit_id"]).copy()
    gap = p.groupby("parcel_id")["issued_date"].diff().dt.days
    p["project_id"] = (gap.isna() | (gap > cfg.permit_chain_gap_days)).cumsum()
    p["_uncleared"] = p["cleared_date"].isna()

    g = p.groupby("project_id")
    out = pd.DataFrame({
        "parcel_id": g["parcel_id"].first(),
        "issued_date": g["issued_date"].min(),
        "n_permits": g["permit_id"].count(),
        "units_created": g["units_created"].agg(cfg.unit_agg),
        "units_lost": g["units_lost"].agg(cfg.unit_agg),
        "cleared_date": g["cleared_date"].max().where(g["_uncleared"].sum() == 0),
    })
    out["net_units"] = out["units_created"] - out["units_lost"]
    return out.reset_index()


def link_applications_to_projects(apps, projects, cfg):
    """One-to-one greedy link of applications to projects on the same parcel.

    Candidate pairs satisfy -link_before_days <= (issued - submitted) <= link_max_lag_days.
    Pairs are taken in order of smallest absolute lag; each application and each project is
    used at most once. Greedy is not globally optimal, which only matters when one parcel
    has several overlapping applications.

    Returns app_id, project_id, lag_days. An unlinked project is NOT necessarily as-of-right:
    it may be a failed link (different parcel id, address change, lag outside the window).
    """
    pairs = apps[["app_id", "parcel_id", "submitted_date"]].merge(
        projects[["project_id", "parcel_id", "issued_date"]], on="parcel_id")
    pairs["lag_days"] = (pairs["issued_date"] - pairs["submitted_date"]).dt.days
    pairs = pairs[(pairs["lag_days"] >= -cfg.link_before_days)
                  & (pairs["lag_days"] <= cfg.link_max_lag_days)].copy()
    pairs["abs_lag"] = pairs["lag_days"].abs()
    pairs = pairs.sort_values(["abs_lag", "app_id", "project_id"])

    used_apps, used_projects, rows = set(), set(), []
    for app_id, project_id, lag in zip(pairs["app_id"], pairs["project_id"], pairs["lag_days"]):
        if app_id in used_apps or project_id in used_projects:
            continue
        used_apps.add(app_id)
        used_projects.add(project_id)
        rows.append((app_id, project_id, lag))
    return pd.DataFrame(rows, columns=["app_id", "project_id", "lag_days"])


def link_diagnostics(apps, projects, links):
    """Match-rate summary. Not every approved application becomes a permit, so a share of
    approved applications below 1 is expected; what matters is that it is stable and plausible."""
    approved = apps[apps["outcome"] == "approved"]
    return {
        "n_applications": len(apps),
        "n_projects": len(projects),
        "n_links": len(links),
        "share_approved_apps_linked": float(approved["app_id"].isin(links["app_id"]).mean())
        if len(approved) else np.nan,
        "share_projects_linked": float(projects["project_id"].isin(links["project_id"]).mean())
        if len(projects) else np.nan,
        "lag_days_p10_p50_p90": links["lag_days"].quantile([0.1, 0.5, 0.9]).tolist() if len(links) else [],
    }
