"""Zoning lookups as of a date, and a crude zoned-capacity measure."""
import numpy as np
import pandas as pd

ZONE_COLS = ("zone_code", "max_fsi", "max_height_m")


def zoning_as_of(records, zoning_versions, date_col, cols=ZONE_COLS):
    """Attach the zoning in force on records[date_col] for records[parcel_id].

    Returns records (original index and order preserved) plus `cols`, effective_from,
    effective_to and zoning_matched. Unmatched rows (no version covering the date: before the
    first version, in a gap, or after an expired version) get NaN and zoning_matched=False;
    they are never silently filled with a later or current regime.
    """
    clash = [c for c in (*cols, "effective_from", "effective_to", "zoning_matched") if c in records.columns]
    if clash:
        raise ValueError(f"records already has columns {clash}")
    if records[date_col].isna().any():
        raise ValueError(f"{date_col} has nulls")

    r = records.copy()
    r["_row"] = np.arange(len(r))
    r = r.sort_values(date_col)
    v = zoning_versions[["parcel_id", "effective_from", "effective_to", *cols]].sort_values("effective_from")
    m = pd.merge_asof(r, v, left_on=date_col, right_on="effective_from", by="parcel_id",
                      direction="backward")

    expired = m["effective_to"].notna() & (m[date_col] >= m["effective_to"])
    blank = ["effective_from", "effective_to", *cols]
    for c in blank:
        m[c] = m[c].mask(expired)
    m["zoning_matched"] = m["effective_from"].notna()

    m = m.sort_values("_row").drop(columns="_row")
    m.index = records.index
    return m


def history_coverage(zoning_versions):
    """Does the zoning table contain history, or only a snapshot?

    If no parcel has more than one version, zoning_as_of is equivalent to joining today's
    zoning to past events, which is the bias this module exists to avoid. Treat
    `looks_like_single_snapshot` as the answer to the Phase 1 feasibility question on
    reconstructing historical zoning.
    """
    per_parcel = zoning_versions.groupby("parcel_id").size()
    share_multi = float((per_parcel > 1).mean()) if len(per_parcel) else 0.0
    return {
        "n_parcels": int(len(per_parcel)),
        "share_with_multiple_versions": share_multi,
        "earliest_effective_from": zoning_versions["effective_from"].min(),
        "looks_like_single_snapshot": share_multi == 0.0,
    }


def zoned_capacity(df, cfg, fsi_col="max_fsi", lot_col="lot_area_m2", built_col="existing_floor_area_m2"):
    """Add crude zoned-capacity columns: permitted floor area, unbuilt floor area, unbuilt units.

    Limitations: (1) existing floor area is usually a *current* snapshot, so for past
    applications it already includes the building the application produced and understates
    unbuilt capacity; use floor area as of the application date if the data allow.
    (2) Floor-area-ratio caps ignore height, setback, heritage and other limits, so this is an
    upper bound. (3) The unit conversion uses cfg assumptions.
    """
    out = df.copy()
    out["zoned_floor_area_m2"] = out[fsi_col] * out[lot_col]
    out["unbuilt_floor_area_m2"] = (out["zoned_floor_area_m2"] - out[built_col]).clip(lower=0)
    out["unbuilt_units_est"] = (out["unbuilt_floor_area_m2"] * cfg.residential_efficiency
                                / cfg.avg_unit_floor_area_m2)
    return out
