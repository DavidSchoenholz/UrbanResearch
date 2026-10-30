from dataclasses import replace

import pandas as pd

from pipeline.linking import aggregate_permits_to_projects, link_applications_to_projects, link_diagnostics
from pipeline.schema import validate

COLS = ["permit_id", "parcel_id", "issued_date", "cleared_date", "units_created", "units_lost"]


def permits(rows):
    return validate(pd.DataFrame(rows, columns=COLS), "permits")


def test_chain_groups_within_gap_and_splits_beyond(cfg):
    p = permits([
        (1, 10, "2020-01-01", "2022-01-01", 10, 0),
        (2, 10, "2020-06-01", "2022-03-01", 10, 0),
        (3, 10, "2023-01-01", None, 5, 0),     # >365 days after previous -> new project
        (4, 11, "2020-01-01", None, 3, 0),
    ])
    proj = aggregate_permits_to_projects(p, cfg)
    assert len(proj) == 3
    first = proj[proj["parcel_id"] == 10].sort_values("issued_date").iloc[0]
    assert first["n_permits"] == 2
    assert first["units_created"] == 10                      # max, not double counted
    assert first["cleared_date"] == pd.Timestamp("2022-03-01")


def test_sum_aggregation_double_counts_repeated_units(cfg):
    p = permits([(1, 10, "2020-01-01", None, 10, 0), (2, 10, "2020-02-01", None, 10, 0)])
    assert aggregate_permits_to_projects(p, cfg)["units_created"].iloc[0] == 10
    assert aggregate_permits_to_projects(p, replace(cfg, unit_agg="sum"))["units_created"].iloc[0] == 20


def test_project_not_cleared_unless_every_permit_cleared(cfg):
    p = permits([(1, 10, "2020-01-01", "2022-01-01", 10, 0), (2, 10, "2020-02-01", None, 0, 0)])
    assert aggregate_permits_to_projects(p, cfg)["cleared_date"].isna().all()


def test_net_units(cfg):
    p = permits([(1, 10, "2020-01-01", None, 10, 3)])
    assert aggregate_permits_to_projects(p, cfg)["net_units"].iloc[0] == 7


def _apps(rows):
    return pd.DataFrame(rows, columns=["app_id", "parcel_id", "submitted_date", "outcome"]).assign(
        submitted_date=lambda d: pd.to_datetime(d["submitted_date"]).astype("datetime64[ns]"))


def _projects(rows):
    return pd.DataFrame(rows, columns=["project_id", "parcel_id", "issued_date"]).assign(
        issued_date=lambda d: pd.to_datetime(d["issued_date"]).astype("datetime64[ns]"))


def test_link_is_one_to_one_greedy_by_smallest_lag(cfg):
    apps = _apps([("A1", 10, "2019-01-01", "approved"), ("A2", 10, "2019-06-01", "approved")])
    projs = _projects([("P1", 10, "2019-07-01"), ("P2", 10, "2021-01-01")])
    links = link_applications_to_projects(apps, projs, cfg).set_index("app_id")
    assert links.loc["A2", "project_id"] == "P1"
    assert links.loc["A1", "project_id"] == "P2"


def test_link_window_and_negative_lag(cfg):
    apps = _apps([("A1", 10, "2019-06-01", "approved")])
    projs = _projects([("P1", 10, "2019-05-22")])                # 10 days before the application
    assert link_applications_to_projects(apps, projs, cfg).empty
    assert len(link_applications_to_projects(apps, projs, replace(cfg, link_before_days=30))) == 1
    far = _projects([("P1", 10, "2030-01-01")])
    assert link_applications_to_projects(apps, far, cfg).empty


def test_link_prefers_smallest_absolute_lag_over_most_negative(cfg):
    apps = _apps([("A1", 10, "2019-06-01", "approved")])
    projs = _projects([("P_before", 10, "2019-05-07"),            # 25 days before
                       ("P_after", 10, "2019-06-11")])            # 10 days after
    links = link_applications_to_projects(apps, projs, replace(cfg, link_before_days=30))
    assert links["project_id"].tolist() == ["P_after"] and links["lag_days"].tolist() == [10]


def test_link_requires_same_parcel(cfg):
    apps = _apps([("A1", 10, "2019-06-01", "approved")])
    projs = _projects([("P1", 11, "2019-07-01")])
    assert link_applications_to_projects(apps, projs, cfg).empty


def test_link_diagnostics(cfg):
    apps = _apps([("A1", 10, "2019-06-01", "approved"), ("A2", 11, "2019-06-01", "refused")])
    projs = _projects([("P1", 10, "2019-07-01"), ("P2", 12, "2019-07-01")])
    links = link_applications_to_projects(apps, projs, cfg)
    d = link_diagnostics(apps, projs, links)
    assert d["share_approved_apps_linked"] == 1.0
    assert d["share_projects_linked"] == 0.5
