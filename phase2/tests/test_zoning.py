import numpy as np
import pandas as pd

from pipeline.schema import validate
from pipeline.zoning import history_coverage, zoned_capacity, zoning_as_of


def versions(rows):
    df = pd.DataFrame(rows, columns=["parcel_id", "zone_code", "max_fsi", "max_height_m",
                                     "effective_from", "effective_to"])
    return validate(df, "zoning_versions")


def records(rows):
    return pd.DataFrame(rows, columns=["rec", "parcel_id", "d"]).assign(
        d=lambda x: pd.to_datetime(x["d"]).astype("datetime64[ns]"))


def test_as_of_picks_regime_in_force_and_preserves_order():
    v = versions([
        (1, "old", 1.0, 10, "1900-01-01", "2018-01-01"),
        (1, "new", 2.0, 20, "2018-01-01", None),
    ])
    r = records([("c", 1, "2020-05-05"), ("a", 1, "2017-12-31"), ("b", 1, "2018-01-01")])
    out = zoning_as_of(r, v, "d")
    assert list(out["rec"]) == ["c", "a", "b"]
    assert list(out["zone_code"]) == ["new", "old", "new"]
    assert out["zoning_matched"].all()


def test_unmatched_cases_are_blank_not_backfilled():
    v = versions([
        (3, "late", 1.0, 10, "2020-01-01", None),            # starts after the record
        (4, "expired", 1.0, 10, "1900-01-01", "2010-01-01"),  # ends before the record, no successor
    ])
    r = records([("no_parcel", 2, "2015-01-01"), ("too_early", 3, "2019-01-01"), ("gap", 4, "2015-01-01")])
    out = zoning_as_of(r, v, "d")
    assert not out["zoning_matched"].any()
    assert out["zone_code"].isna().all()
    assert out["max_fsi"].isna().all()


def test_index_alignment_is_kept():
    v = versions([(1, "z", 1.5, 10, "1900-01-01", None)])
    r = records([("a", 1, "2020-01-01"), ("b", 1, "2010-01-01")])
    r.index = [10, 20]
    out = zoning_as_of(r, v, "d")
    assert list(out.index) == [10, 20]
    assert list(out["max_fsi"]) == [1.5, 1.5]


def test_history_coverage_detects_snapshot():
    snap = versions([(1, "z", 1.0, 10, "1900-01-01", None), (2, "z", 1.0, 10, "1900-01-01", None)])
    assert history_coverage(snap)["looks_like_single_snapshot"]
    hist = versions([(1, "a", 1.0, 10, "1900-01-01", "2018-01-01"), (1, "b", 2.0, 10, "2018-01-01", None)])
    cov = history_coverage(hist)
    assert not cov["looks_like_single_snapshot"] and cov["share_with_multiple_versions"] == 1.0


def test_zoned_capacity(cfg):
    df = pd.DataFrame({"max_fsi": [2.0, 1.0], "lot_area_m2": [1000.0, 1000.0],
                       "existing_floor_area_m2": [500.0, 1500.0]})
    out = zoned_capacity(df, cfg)
    assert list(out["zoned_floor_area_m2"]) == [2000.0, 1000.0]
    assert list(out["unbuilt_floor_area_m2"]) == [1500.0, 0.0]            # clipped at zero
    assert np.isclose(out["unbuilt_units_est"].iloc[0], 1500 * 0.8 / 75)
