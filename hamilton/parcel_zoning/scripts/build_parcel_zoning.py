"""Assign zoning to every Hamilton parcel by area overlay.

Reads raw/*.geojson (from scripts/fetch.py) and writes:
  output/hamilton_parcel_zoning.csv.gz    one row per parcel polygon, its primary zone and flags
  output/hamilton_parcel_zone_pieces.csv.gz  one row per (parcel, zoning polygon) overlap, with area share
  output/summary.json                     counts used in README / QA_REPORT

Method (see ../README.md, "Method"):
  1. Project both layers to UTM 17N (EPSG:26917) so areas are in square metres.
  2. Intersect each parcel with the zoning polygons it touches; compute each piece's share of the
     parcel's area.
  3. Drop slivers: pieces under SLIVER_SHARE of the parcel or under SLIVER_M2. These come from the
     parcel and zoning layers being digitized separately, not from real split zoning.
  4. The primary zone is the piece with the largest share. A parcel is "split-zoned" when more than
     one distinct zone label survives step 3.

Run from hamilton/parcel_zoning/:  python scripts/build_parcel_zoning.py
"""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "output"

METRIC_CRS = "EPSG:26917"
# A zoning piece must cover at least this share of the parcel AND this many m2 to count.
SLIVER_SHARE = 0.05
SLIVER_M2 = 10.0
# Square metres per unit of the parcel layer's SITE_AREA. Codes inferred by comparing SITE_AREA with
# polygon area (median ratios 0.000246 A, 10.77 F, 1.0006 M, 0.0001 H; checked 2026-10-30).
SITE_AREA_TO_M2 = {"A": 4046.8564224, "F": 0.09290304, "M": 1.0, "H": 10000.0}

ZONE_FIELDS = [
    "ZONING_CODE", "ZONING_DESC", "ZONING_CATEGORY", "PARENT_BY_LAW_NUMBER", "BY_LAW_NUMBER",
    "EXCEPTION1", "EXCEPTION2", "EXCEPTION3", "HOLDING1", "HOLDING2", "HOLDING3",
    "TEMPORARY_USE_1", "TEMPORARY_USE_2", "OLT_CASE_NO", "OLT_LEAD_CASE_NO",
    "COUNCIL_APP_DATE", "FINALBINDING_DATE", "URBAN_RURAL_SETTLE", "ZONING_MAP",
]


def clean_str(s):
    s = s.astype("string").str.strip()
    return s.mask(s == "")


def zone_label(z):
    """Label in the style of the City's map: code, then exceptions, holdings and temporary uses."""
    parts = [z["ZONING_CODE"]]
    for c in ["EXCEPTION1", "EXCEPTION2", "EXCEPTION3"]:
        parts.append(z[c])
    for c in ["HOLDING1", "HOLDING2", "HOLDING3", "TEMPORARY_USE_1", "TEMPORARY_USE_2"]:
        parts.append(z[c])
    df = pd.concat(parts, axis=1).astype("string")
    return df.apply(lambda r: ", ".join(v for v in r if pd.notna(v)), axis=1)


def governing_bylaw(parent):
    """05-200 or the former-municipality by-law that still governs the polygon."""
    p = parent.fillna("Unknown")
    return p.replace({"1964": "1964 Dundas (pre-3581-86)"})


def load_zoning():
    z = gpd.read_file(RAW / "zoning.geojson").to_crs(METRIC_CRS)
    for c in ZONE_FIELDS:
        if c not in ("COUNCIL_APP_DATE", "FINALBINDING_DATE"):
            z[c] = clean_str(z[c])
    z = z[z.geometry.notna() & ~z.is_empty].copy()
    z["geometry"] = shapely.make_valid(z.geometry.values)
    z["zone_label"] = zone_label(z)
    z["category"] = z["ZONING_CATEGORY"].replace({"Low Density Residential": "Residential"}).fillna("Uncategorized")
    z["bylaw"] = governing_bylaw(z["PARENT_BY_LAW_NUMBER"])
    z["zid"] = np.arange(len(z))
    return z


def load_parcels():
    p = gpd.read_file(RAW / "parcels.geojson").to_crs(METRIC_CRS)
    p = p.rename(columns={"OBJECTID": "parcel_oid"})
    p["geometry"] = shapely.make_valid(p.geometry.values)
    p["parcel_area_m2"] = p.area
    p["site_area_m2"] = p["SITE_AREA"] * p["UNIT_OF_MEASURE"].map(SITE_AREA_TO_M2)
    # Condo units (MPAC code 370) and some multi-roll properties share one identical footprint.
    # geom_group numbers each distinct footprint so the map can draw it once.
    key = pd.Series([shapely.to_wkb(g) for g in shapely.normalize(p.geometry.values)], index=p.index)
    p["geom_group"] = pd.factorize(key)[0]
    p["n_same_geometry"] = p.groupby("geom_group")["geom_group"].transform("size")
    # Polygon area far from the assessed site area means the drawn shape is not the lot (e.g. 12
    # rolls share a 19.5 km2 harbour polygon). Only judged where SITE_AREA is filled in.
    ratio = p["site_area_m2"] / p["parcel_area_m2"]
    p["geometry_suspect"] = (p["site_area_m2"] > 0) & ((ratio < 0.1) | (ratio > 10)) & (p["n_same_geometry"] == 1)
    p.loc[p["parcel_area_m2"] > 1e7, "geometry_suspect"] = True
    return p


def overlay(p, z):
    """Long table of parcel x zoning-polygon intersections with area and share."""
    pairs = gpd.sjoin(p[["parcel_oid", "geometry"]], z[["zid", "geometry"]], predicate="intersects")
    pg = p.set_index("parcel_oid").geometry.loc[pairs["parcel_oid"]].values
    zg = z.set_index("zid").geometry.loc[pairs["zid"]].values
    inter = shapely.intersection(pg, zg)
    pieces = pd.DataFrame({
        "parcel_oid": pairs["parcel_oid"].values,
        "zid": pairs["zid"].values,
        "piece_m2": shapely.area(inter),
    })
    pieces = pieces.merge(p[["parcel_oid", "parcel_area_m2"]], on="parcel_oid")
    pieces["share"] = pieces["piece_m2"] / pieces["parcel_area_m2"]
    pieces = pieces[pieces["piece_m2"] > 0]
    keep = z[["zid", "zone_label", "ZONING_CODE", "category", "bylaw"]]
    return pieces.merge(keep, on="zid")


def per_parcel(pieces):
    # Collapse pieces with the same zone label (one zone split across several City polygons).
    by_label = (pieces.groupby(["parcel_oid", "zone_label"], as_index=False)
                .agg(share=("share", "sum"), piece_m2=("piece_m2", "sum"), zid=("zid", "first")))
    by_label["significant"] = (by_label["share"] >= SLIVER_SHARE) & (by_label["piece_m2"] >= SLIVER_M2)
    by_label = by_label.sort_values(["parcel_oid", "share"], ascending=[True, False])
    top = by_label.groupby("parcel_oid").head(1).set_index("parcel_oid")
    sig = by_label[by_label["significant"]]
    agg = sig.groupby("parcel_oid").agg(
        n_zones=("zone_label", "size"),
        all_zones=("zone_label", lambda s: " | ".join(s)),
    )
    second = sig.groupby("parcel_oid")["share"].apply(lambda s: s.iloc[1] if len(s) > 1 else 0.0)
    out = top[["zid", "zone_label", "share"]].rename(columns={"share": "primary_share"})
    out = out.join(agg).join(second.rename("second_share"))
    out["n_zones"] = out["n_zones"].fillna(1).astype(int)  # top piece may itself be a sliver
    out["second_share"] = out["second_share"].fillna(0.0)
    out["covered_share"] = pieces.groupby("parcel_oid")["share"].sum().clip(upper=1.0)
    return out


def flag_overlap(p, layer, name, min_share=0.5):
    """Boolean: at least min_share of the parcel lies inside the given polygon layer."""
    g = gpd.read_file(RAW / f"{layer}.geojson").to_crs(METRIC_CRS)
    g["geometry"] = shapely.make_valid(g.geometry.values)
    g = g[["geometry"]].dissolve()
    inter = shapely.area(shapely.intersection(p.geometry.values, g.geometry.iloc[0]))
    return pd.Series(inter / p["parcel_area_m2"].values >= min_share, index=p.index, name=name)


def largest_overlap(p, layer, cols, prefix):
    """For each parcel, attributes of the polygon in `layer` covering most of it (>= 50%)."""
    g = gpd.read_file(RAW / f"{layer}.geojson").to_crs(METRIC_CRS)
    g["geometry"] = shapely.make_valid(g.geometry.values)
    g = g[cols + ["geometry"]].reset_index(names="gid")
    pairs = gpd.sjoin(p[["parcel_oid", "geometry"]], g, predicate="intersects")
    pg = p.set_index("parcel_oid").geometry.loc[pairs["parcel_oid"]].values
    gg = g.set_index("gid").geometry.loc[pairs["gid"]].values
    pairs["a"] = shapely.area(shapely.intersection(pg, gg))
    pairs = pairs.merge(p[["parcel_oid", "parcel_area_m2"]], on="parcel_oid")
    pairs = pairs[pairs["a"] / pairs["parcel_area_m2"] >= 0.5]
    pairs = pairs.sort_values("a", ascending=False).drop_duplicates("parcel_oid")
    return pairs.set_index("parcel_oid")[cols].add_prefix(prefix)


def main():
    OUT.mkdir(exist_ok=True)
    z = load_zoning()
    p = load_parcels()
    print(f"zoning polygons {len(z)}, parcels {len(p)}", flush=True)

    pieces = overlay(p, z)
    print(f"pieces {len(pieces)}", flush=True)
    pp = per_parcel(pieces)

    zattrs = z.set_index("zid")[["ZONING_CODE", "ZONING_DESC", "category", "bylaw", "BY_LAW_NUMBER",
                                 "EXCEPTION1", "EXCEPTION2", "EXCEPTION3", "HOLDING1", "HOLDING2",
                                 "HOLDING3", "TEMPORARY_USE_1", "TEMPORARY_USE_2", "OLT_CASE_NO",
                                 "URBAN_RURAL_SETTLE", "ZONING_MAP"]]
    pp = pp.join(zattrs, on="zid")

    out = p[["parcel_oid", "PROPERTY_NUM", "LOCATOR", "PROP_CODE", "FRONTAGE", "DEPTH",
             "SITE_AREA", "UNIT_OF_MEASURE", "site_area_m2", "parcel_area_m2", "geom_group",
             "n_same_geometry", "geometry_suspect"]].set_index("parcel_oid")
    out = out.join(pp.drop(columns="zid"))
    out["has_zoning"] = out["zone_label"].notna()
    out["split_zoned"] = out["n_zones"].fillna(0) > 1
    out["has_exception"] = out["EXCEPTION1"].notna()
    out["has_holding"] = out[["HOLDING1", "HOLDING2", "HOLDING3"]].notna().any(axis=1)
    out["has_temporary_use"] = out[["TEMPORARY_USE_1", "TEMPORARY_USE_2"]].notna().any(axis=1)
    out["under_olt_appeal_tag"] = out["OLT_CASE_NO"].notna()
    out["former_bylaw"] = out["bylaw"].notna() & (out["bylaw"] != "05-200")

    # Context layers. flag_overlap returns values in p order, which is also out order.
    for layer, name in [("interim_control", "in_interim_control"),
                        ("compliance_review", "in_compliance_review_area"),
                        ("h_converted_parcels", "h_converted_dwelling")]:
        out[name] = flag_overlap(p, layer, name).values
    pending = largest_overlap(p, "zoning_council_approved", ["ZONING_CODE", "BY_LAW_NUMBER", "COUNCIL_APP_DATE"], "pending_")
    out = out.join(pending)
    out["pending_COUNCIL_APP_DATE"] = pd.to_datetime(out["pending_COUNCIL_APP_DATE"], unit="ms").dt.date
    ward = largest_overlap(p, "wards", ["WARD"], "")
    comm = largest_overlap(p, "communities", ["COMMUNITY_NAME"], "")
    out = out.join(ward).join(comm.rename(columns={"COMMUNITY_NAME": "community"}))
    out = out.rename(columns={"WARD": "ward"})

    out = out.reset_index()
    out.columns = [c.lower() for c in out.columns]
    out = out.rename(columns={"locator": "address", "prop_code": "mpac_property_code"})
    for c in ["primary_share", "second_share", "covered_share"]:
        out[c] = out[c].round(4)
    for c in ["site_area_m2", "parcel_area_m2"]:
        out[c] = out[c].round(1)
    out.to_csv(OUT / "hamilton_parcel_zoning.csv.gz", index=False)

    long = pieces.merge(z[["zid", "PARENT_BY_LAW_NUMBER"]], on="zid")
    long = long.merge(p[["parcel_oid", "PROPERTY_NUM"]], on="parcel_oid")
    long = long[["parcel_oid", "PROPERTY_NUM", "zone_label", "ZONING_CODE", "category", "bylaw", "piece_m2", "share"]]
    long.columns = [c.lower() for c in long.columns]
    long["piece_m2"] = long["piece_m2"].round(1)
    long["share"] = long["share"].round(4)
    long.sort_values(["parcel_oid", "share"], ascending=[True, False]).to_csv(
        OUT / "hamilton_parcel_zone_pieces.csv.gz", index=False)

    # Parcel layer self-overlap (stacked condo or duplicate polygons would show up here).
    union_area = shapely.union_all(p.geometry.values).area
    summary = {
        "n_parcel_polygons": int(len(out)),
        "n_unique_property_num": int(out["property_num"].nunique()),
        "n_duplicate_property_num_rows": int(out["property_num"].duplicated().sum()),
        "parcel_area_sum_km2": round(float(p["parcel_area_m2"].sum()) / 1e6, 3),
        "parcel_union_km2": round(union_area / 1e6, 3),
        "n_distinct_footprints": int(out["geom_group"].nunique()),
        "n_rows_sharing_footprint": int((out["n_same_geometry"] > 1).sum()),
        "n_geometry_suspect": int(out["geometry_suspect"].sum()),
        "n_zoning_polygons": int(len(z)),
        "n_pieces": int(len(pieces)),
        "share_parcels_with_zoning": round(float(out["has_zoning"].mean()), 5),
        "n_parcels_without_zoning": int((~out["has_zoning"]).sum()),
        "n_split_zoned": int(out["split_zoned"].sum()),
        "share_split_zoned": round(float(out["split_zoned"].mean()), 5),
        "primary_share_quantiles": {str(q): round(float(out["primary_share"].quantile(q)), 4)
                                    for q in [0.01, 0.05, 0.1, 0.5]},
        "covered_share_lt_0.95": int((out["covered_share"] < 0.95).sum()),
        "by_bylaw": out["bylaw"].fillna("none").value_counts().to_dict(),
        "by_category": out["category"].fillna("none").value_counts().to_dict(),
        "top_zone_codes": out["zoning_code"].value_counts().head(30).to_dict(),
        "n_has_exception": int(out["has_exception"].sum()),
        "n_has_holding": int(out["has_holding"].sum()),
        "n_has_temporary_use": int(out["has_temporary_use"].sum()),
        "n_olt_tag": int(out["under_olt_appeal_tag"].sum()),
        "olt_cases": out["olt_case_no"].value_counts().head(15).to_dict(),
        "n_pending_council_approved": int(out["pending_zoning_code"].notna().sum()),
        "pending_bylaws": out["pending_by_law_number"].value_counts().to_dict(),
        "n_interim_control": int(out["in_interim_control"].sum()),
        "n_compliance_review_area": int(out["in_compliance_review_area"].sum()),
        "n_h_converted": int(out["h_converted_dwelling"].sum()),
        "n_no_ward": int(out["ward"].isna().sum()),
        "site_area_vs_polygon_median_ratio": round(float((out["site_area_m2"] / out["parcel_area_m2"]).median()), 4),
        "settings": {"SLIVER_SHARE": SLIVER_SHARE, "SLIVER_M2": SLIVER_M2, "METRIC_CRS": METRIC_CRS},
        "source_manifest": json.loads((RAW / "manifest.json").read_text()),
    }
    for k in summary["source_manifest"].values():
        k.pop("fields", None)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({k: v for k, v in summary.items() if k != "source_manifest"}, indent=2, default=str))


if __name__ == "__main__":
    main()
