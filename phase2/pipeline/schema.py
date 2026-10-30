"""Canonical table schemas and validation.

Raw sources are mapped onto these in loaders.py; downstream code only sees these names.
"""
import pandas as pd

OUTCOMES = {"approved", "refused", "withdrawn", "pending"}

TABLES = {
    "applications": {
        "required": ["app_id", "parcel_id", "submitted_date", "decided_date", "outcome",
                     "requires_rezoning", "units_proposed"],
        "dates": ["submitted_date", "decided_date"],
        "key": ["app_id"],
        "non_null": ["app_id", "parcel_id", "submitted_date", "outcome"],
        "non_negative": ["units_proposed"],
    },
    "permits": {
        "required": ["permit_id", "parcel_id", "issued_date", "cleared_date",
                     "units_created", "units_lost"],
        "dates": ["issued_date", "cleared_date"],
        "key": ["permit_id"],
        "non_null": ["permit_id", "parcel_id", "issued_date"],
        "non_negative": ["units_created", "units_lost"],
    },
    # One row per parcel per period during which a zoning regime was in force. Use a
    # sentinel early date (for example 1900-01-01) as effective_from for a baseline whose
    # true start is unknown; leave effective_to null while the regime is still in force.
    "zoning_versions": {
        "required": ["parcel_id", "zone_code", "max_fsi", "max_height_m",
                     "effective_from", "effective_to"],
        "dates": ["effective_from", "effective_to"],
        "key": ["parcel_id", "effective_from"],
        "non_null": ["parcel_id", "effective_from"],
        "non_negative": ["max_fsi", "max_height_m"],
    },
    "parcels": {
        "required": ["parcel_id", "lot_area_m2", "existing_floor_area_m2"],
        "dates": [],
        "key": ["parcel_id"],
        "non_null": ["parcel_id"],
        "non_negative": ["lot_area_m2", "existing_floor_area_m2"],
    },
}


def validate(df, table):
    """Return a validated copy of df with dates coerced to datetime64[ns]; raise ValueError on problems.

    Key columns must be non-null because pandas merges treat NaN keys as equal to each other,
    which would silently link unrelated records.
    """
    spec = TABLES[table]
    missing = [c for c in spec["required"] if c not in df.columns]
    if missing:
        raise ValueError(f"{table}: missing columns {missing}")

    out = df.copy()
    for c in spec["dates"]:
        out[c] = pd.to_datetime(out[c]).astype("datetime64[ns]")
    for c in spec["non_null"]:
        n_null = int(out[c].isna().sum())
        if n_null:
            raise ValueError(f"{table}: {n_null} null values in required column '{c}'")
    if out.duplicated(spec["key"]).any():
        raise ValueError(f"{table}: duplicate rows for key {spec['key']}")
    for c in spec["non_negative"]:
        if (out[c] < 0).any():
            raise ValueError(f"{table}: negative values in '{c}'")

    if table == "applications":
        bad = set(out["outcome"].unique()) - OUTCOMES
        if bad:
            raise ValueError(f"applications: outcome values {sorted(bad)} not in {sorted(OUTCOMES)}")
        try:
            out["requires_rezoning"] = out["requires_rezoning"].astype("boolean")
        except (TypeError, ValueError) as exc:
            raise ValueError("applications: requires_rezoning must be True/False/null; recode "
                             "source values (for example 'Y'/'N') before validating") from exc
    if table == "zoning_versions":
        z = out.sort_values(["parcel_id", "effective_from"])
        if (z["effective_to"] <= z["effective_from"]).any():
            raise ValueError("zoning_versions: effective_to must be after effective_from")
        nxt = z.groupby("parcel_id")["effective_from"].shift(-1)
        overlap = nxt.notna() & (z["effective_to"].isna() | (z["effective_to"] > nxt))
        if overlap.any():
            raise ValueError(f"zoning_versions: {int(overlap.sum())} overlapping versions on the same parcel")
    return out
