import pandas as pd
import pytest

from pipeline.loaders import mapping_template, to_canonical
from pipeline.schema import validate

PERMIT_COLS = ["permit_id", "parcel_id", "issued_date", "cleared_date", "units_created", "units_lost"]


def permits(rows):
    return pd.DataFrame(rows, columns=PERMIT_COLS)


def test_missing_columns_raise():
    with pytest.raises(ValueError, match="missing columns"):
        validate(pd.DataFrame({"permit_id": [1]}), "permits")


def test_null_key_raises_because_nan_keys_would_merge():
    df = permits([(1, None, "2020-01-01", None, 1, 0)])
    with pytest.raises(ValueError, match="null values"):
        validate(df, "permits")


def test_duplicate_key_and_negative_units_raise():
    with pytest.raises(ValueError, match="duplicate"):
        validate(permits([(1, 1, "2020-01-01", None, 1, 0), (1, 2, "2020-01-01", None, 1, 0)]), "permits")
    with pytest.raises(ValueError, match="negative"):
        validate(permits([(1, 1, "2020-01-01", None, -1, 0)]), "permits")


def test_dates_are_coerced_to_ns():
    out = validate(permits([(1, 1, "2020-01-01", None, 1, 0)]), "permits")
    assert str(out["issued_date"].dtype) == "datetime64[ns]"
    assert str(out["cleared_date"].dtype) == "datetime64[ns]"


def test_bad_outcome_raises():
    df = pd.DataFrame({"app_id": [1], "parcel_id": [1], "submitted_date": ["2020-01-01"],
                       "decided_date": [None], "outcome": ["maybe"], "requires_rezoning": [True],
                       "units_proposed": [5]})
    with pytest.raises(ValueError, match="outcome"):
        validate(df, "applications")


def test_requires_rezoning_is_normalized_and_strings_are_rejected():
    base = {"app_id": [1, 2], "parcel_id": [1, 2], "submitted_date": ["2020-01-01"] * 2,
            "decided_date": [None, None], "outcome": ["pending", "pending"], "units_proposed": [1, 1]}
    ok = validate(pd.DataFrame({**base, "requires_rezoning": [True, None]}), "applications")
    assert str(ok["requires_rezoning"].dtype) == "boolean"
    with pytest.raises(ValueError, match="requires_rezoning"):
        validate(pd.DataFrame({**base, "requires_rezoning": ["Y", "N"]}), "applications")


def test_overlapping_zoning_versions_raise():
    df = pd.DataFrame({
        "parcel_id": [1, 1], "zone_code": ["a", "b"], "max_fsi": [1.0, 2.0], "max_height_m": [10, 20],
        "effective_from": ["1900-01-01", "2018-01-01"], "effective_to": [None, None]})
    with pytest.raises(ValueError, match="overlapping"):
        validate(df, "zoning_versions")


def test_loader_refuses_unfilled_mapping():
    with pytest.raises(NotImplementedError):
        to_canonical(pd.DataFrame(), mapping_template("permits"), "permits")


def test_loader_maps_and_validates():
    raw = pd.DataFrame({"PID": [1], "PARCEL": [9], "ISSUED": ["2020-01-01"], "CLEARED": [None],
                        "UP": [5], "LOST": [0]})
    mapping = {"permit_id": "PID", "parcel_id": "PARCEL", "issued_date": "ISSUED",
               "cleared_date": "CLEARED", "units_created": "UP", "units_lost": "LOST"}
    out = to_canonical(raw, mapping, "permits")
    assert list(out["parcel_id"]) == [9]


def test_loader_rejects_wrong_keys_missing_columns_and_shared_columns():
    raw = pd.DataFrame({"A": [1]})
    with pytest.raises(ValueError, match="mapping keys"):
        to_canonical(raw, {"permit_id": "A"}, "permits")
    full = {k: "A" for k in mapping_template("permits")}
    with pytest.raises(ValueError, match="same raw column"):
        to_canonical(raw, full, "permits")
    full = {k: f"X{i}" for i, k in enumerate(mapping_template("permits"))}
    with pytest.raises(KeyError):
        to_canonical(raw, full, "permits")
