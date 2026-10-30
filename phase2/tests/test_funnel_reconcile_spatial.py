import numpy as np
import pandas as pd
import pytest

from pipeline.funnel import build_pipeline_table, build_time_to_event, funnel_by_cohort
from pipeline.reconcile import reconcile_with_aggregate


def ts(s):
    return pd.Timestamp(s) if s else pd.NaT


def make_apps(rows):
    df = pd.DataFrame(rows, columns=["app_id", "parcel_id", "submitted_date", "decided_date", "outcome",
                                     "requires_rezoning", "units_proposed"])
    for c in ("submitted_date", "decided_date"):
        df[c] = pd.to_datetime(df[c]).astype("datetime64[ns]")
    return df


def make_projects(rows):
    df = pd.DataFrame(rows, columns=["project_id", "issued_date", "cleared_date", "net_units"])
    for c in ("issued_date", "cleared_date"):
        df[c] = pd.to_datetime(df[c]).astype("datetime64[ns]")
    return df


@pytest.fixture
def table():
    apps = make_apps([
        ("A1", 1, "2018-01-01", "2018-06-01", "approved", True, 10),    # completed
        ("A2", 2, "2018-02-01", "2018-07-01", "approved", False, 20),   # permitted only
        ("A3", 3, "2019-01-01", "2019-03-01", "refused", True, 5),      # refused
        ("A4", 4, "2019-05-01", None, "pending", None, 8),              # pending, route unknown
    ])
    projects = make_projects([("P1", "2018-09-01", "2021-09-01", 9), ("P2", "2019-01-01", None, 18)])
    links = pd.DataFrame({"app_id": ["A1", "A2"], "project_id": ["P1", "P2"], "lag_days": [243, 334]})
    return build_pipeline_table(apps, links, projects)


def test_stage_and_route(table):
    t = table.set_index("app_id")
    assert t["stage_reached"].to_dict() == {"A1": "completed", "A2": "permitted", "A3": "submitted", "A4": "submitted"}
    assert t["route"].to_dict() == {"A1": "rezoning_or_variance", "A2": "no_rezoning_recorded",
                                    "A3": "rezoning_or_variance", "A4": "unknown"}
    assert not t["permit_without_approval"].any()


def test_cohort_funnel_counts_and_follow_up(table, cfg):
    f = funnel_by_cohort(table, cfg, by=())
    row18 = f[f["cohort_year"] == 2018].iloc[0]
    assert (row18["n_apps"], row18["n_approved"], row18["n_permitted"], row18["n_completed"]) == (2, 2, 2, 1)
    assert row18["units_completed"] == 9
    assert row18["completed_share_naive"] == 0.5
    assert np.isclose(row18["min_follow_up_years"], 7.0, atol=0.01)


def test_time_to_event_rules(table, cfg):
    tte = build_time_to_event(table, cfg, "completed_date",
                              table["outcome"].isin(["refused", "withdrawn"]), "decided_date").set_index("app_id")
    assert tte.loc["A1", "event"] == 1 and tte.loc["A1", "duration_days"] == (ts("2021-09-01") - ts("2018-01-01")).days
    assert tte.loc["A2", "event"] == 0 and tte.loc["A2", "duration_days"] == (cfg.data_end - ts("2018-02-01")).days
    assert tte.loc["A3", "event"] == 2 and tte.loc["A3", "duration_days"] == (ts("2019-03-01") - ts("2019-01-01")).days
    assert tte.loc["A4", "event"] == 0
    assert not tte["invalid"].any()


def test_completion_takes_precedence_over_refusal(cfg):
    apps = make_apps([("A1", 1, "2018-01-01", "2018-06-01", "refused", True, 10)])
    projects = make_projects([("P1", "2018-09-01", "2021-09-01", 9)])
    links = pd.DataFrame({"app_id": ["A1"], "project_id": ["P1"], "lag_days": [243]})
    t = build_pipeline_table(apps, links, projects)
    assert t["permit_without_approval"].iloc[0]
    tte = build_time_to_event(t, cfg, "completed_date", t["outcome"].eq("refused"), "decided_date")
    assert tte["event"].iloc[0] == 1


def test_competing_outcome_without_date_is_flagged_not_hidden(cfg):
    apps = make_apps([("A1", 1, "2018-01-01", None, "withdrawn", True, 10)])
    t = build_pipeline_table(apps, pd.DataFrame({"app_id": [], "project_id": [], "lag_days": []}),
                             make_projects([]))
    tte = build_time_to_event(t, cfg, "completed_date", t["outcome"].isin(["refused", "withdrawn"]),
                              "decided_date")
    assert tte["event"].iloc[0] == 0 and tte["competing_missing_date"].iloc[0]


def test_route_handles_nullable_boolean_and_unknown(cfg):
    apps = make_apps([("A1", 1, "2018-01-01", None, "pending", True, 1),
                      ("A2", 2, "2018-01-01", None, "pending", None, 1)])
    apps["requires_rezoning"] = apps["requires_rezoning"].astype("boolean")
    t = build_pipeline_table(apps, pd.DataFrame({"app_id": [], "project_id": [], "lag_days": []}),
                             make_projects([]))
    assert t["route"].tolist() == ["rezoning_or_variance", "unknown"]


def test_completed_refusal_without_decision_date_is_not_flagged_missing(cfg):
    apps = make_apps([("A1", 1, "2018-01-01", None, "refused", True, 10)])
    projects = make_projects([("P1", "2018-09-01", "2021-09-01", 9)])
    links = pd.DataFrame({"app_id": ["A1"], "project_id": ["P1"], "lag_days": [243]})
    t = build_pipeline_table(apps, links, projects)
    tte = build_time_to_event(t, cfg, "completed_date", t["outcome"].eq("refused"), "decided_date")
    assert tte["event"].iloc[0] == 1 and not tte["competing_missing_date"].iloc[0]


def test_invalid_durations_flagged(cfg):
    apps = make_apps([("A1", 1, "2020-01-01", None, "pending", True, 1),
                      ("A2", 2, "2026-06-01", None, "pending", True, 1)])      # submitted after data_end
    projects = make_projects([("P1", "2019-01-01", "2019-06-01", 1)])           # cleared before submission
    links = pd.DataFrame({"app_id": ["A1"], "project_id": ["P1"], "lag_days": [-365]})
    t = build_pipeline_table(apps, links, projects)
    tte = build_time_to_event(t, cfg, "completed_date", t["outcome"].eq("refused"), "decided_date")
    assert tte["invalid"].all()


def test_reconcile_with_aggregate():
    projects = pd.DataFrame({
        "project_id": [1, 2, 3], "net_units": [10, 20, 5],
        "cleared_date": pd.to_datetime(["2020-03-01", "2020-09-01", None])})
    agg = pd.DataFrame({"year": [2020, 2021], "completions": [40, 50]})
    out = reconcile_with_aggregate(projects, agg).set_index("year")
    assert out.loc[2020, "units_cleared"] == 30
    assert np.isclose(out.loc[2020, "ratio_units_to_aggregate"], 0.75)
    assert out.loc[2021, "units_cleared"] != out.loc[2021, "units_cleared"]   # NaN: aggregate-only year


def test_attach_parcel_id():
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import Point, box
    from pipeline.spatial import attach_parcel_id

    parcels = gpd.GeoDataFrame({"parcel_id": [1, 2]}, geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs="EPSG:2952")
    pts = gpd.GeoDataFrame({"k": ["in1", "boundary", "outside"]},
                           geometry=[Point(0.5, 0.5), Point(1, 0.5), Point(5, 5)], crs="EPSG:2952")
    out, stats = attach_parcel_id(pts, parcels)
    assert len(out) == 3
    assert stats == {"n_points": 3, "n_unmatched": 1, "n_multi_match": 1}
    assert out.loc[out["k"] == "in1", "parcel_id"].iloc[0] == 1
