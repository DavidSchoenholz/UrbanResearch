"""Build the data files for the parcel zoning web map (site/).

Reads output/hamilton_parcel_zoning.csv.gz (from build_parcel_zoning.py) and raw/*.geojson, and writes:
  site/data/meta.json             categories, by-laws, zone descriptions, headline numbers, data date
  site/data/zoning.json           zoning polygons dissolved by zone label, simplified (zoomed-out view)
  site/data/wards.json            ward outlines
  site/data/parcels/ward-<N>.json parcel footprints for one ward, with their zoning (zoomed-in view)
  site/data/search.json           address/roll -> ward, map position and feature roll, for the search box

Condo units and other rolls sharing an identical footprint are drawn once (geom_group); the popup
lists how many rolls share it. Run from hamilton/parcel_zoning/:  python scripts/build_map.py
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
SITE = ROOT / "site" / "data"
METRIC_CRS = "EPSG:26917"
PARCEL_SIMPLIFY_M = 0.75
ZONING_SIMPLIFY_M = 4.0
COORD_DECIMALS = 5  # about 1 m

# Order is the legend order. Colours follow planning-map conventions; see README "Map colours".
CATEGORIES = [
    "Residential", "Commercial", "Transit Oriented Corridor", "Industrial", "Institutional",
    "Open Space and Parks", "Agricultural", "Waterfront", "Utility", "Parking", "Uncategorized",
]
# Flag bits, shared with site/app.js.
FLAGS = {
    "split_zoned": 1, "has_exception": 2, "has_holding": 4, "has_temporary_use": 8,
    "under_olt_appeal_tag": 16, "pending": 32, "geometry_suspect": 64, "in_interim_control": 128,
    "in_compliance_review_area": 256, "h_converted_dwelling": 512, "former_bylaw": 1024,
}


def rounded(geoms):
    return shapely.set_precision(geoms, 10 ** -COORD_DECIMALS)


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), default=str))
    print(f"{path.relative_to(ROOT)}: {path.stat().st_size / 1e6:.2f} MB")


def text(v):
    return None if pd.isna(v) else str(v)


def main():
    tab = pd.read_csv(ROOT / "output" / "hamilton_parcel_zoning.csv.gz", dtype=str, keep_default_na=False,
                      na_values=[""])
    bools = [c for c in FLAGS if c in tab.columns]
    for c in bools:
        tab[c] = tab[c] == "True"
    tab["pending"] = tab["pending_zoning_code"].notna()
    tab["flags"] = sum(tab[c].astype(int) * bit for c, bit in FLAGS.items())

    bylaws = sorted(tab["bylaw"].dropna().unique(), key=lambda b: (b != "05-200", b))
    cat_idx = {c: i for i, c in enumerate(CATEGORIES)}
    bylaw_idx = {b: i for i, b in enumerate(bylaws)}

    # Zone lookup: code + by-law -> description, so each parcel stores a small index.
    zkeys = tab[["zoning_code", "zoning_desc", "category", "bylaw"]].dropna(subset=["zoning_code"])
    zkeys = zkeys.drop_duplicates(["zoning_code", "bylaw"]).reset_index(drop=True)
    zone_index = {(r.zoning_code, r.bylaw): i for i, r in zkeys.iterrows()}
    zones = [[r.zoning_code, text(r.zoning_desc), cat_idx.get(r.category, cat_idx["Uncategorized"]),
              bylaw_idx.get(r.bylaw)] for r in zkeys.itertuples()]

    # Parcels: one feature per distinct footprint.
    p = gpd.read_file(RAW / "parcels.geojson")[["OBJECTID", "geometry"]].rename(columns={"OBJECTID": "parcel_oid"})
    p["parcel_oid"] = p["parcel_oid"].astype(str)
    p = p.merge(tab, on="parcel_oid")
    p["ward"] = p["ward"].fillna("0")
    p = p.sort_values(["geom_group", "address"], na_position="last")

    def per_group(g):
        first = g.iloc[0]
        addrs = g["address"].dropna().unique()
        a = addrs[0] if len(addrs) else ""
        props = {
            "a": a + (f" (+{len(addrs) - 1} more)" if len(addrs) > 1 else ""),
            "r": first["property_num"],
            "n": int(len(g)),
            "z": text(first["zone_label"]),
            "k": zone_index.get((first["zoning_code"], first["bylaw"])),
            "f": int(first["flags"] | (g["flags"] & FLAGS["geometry_suspect"]).max()),
            "m": round(float(first["parcel_area_m2"])),
        }
        if first["split_zoned"]:
            props["s"] = round(float(first["primary_share"]) * 100)
            props["o"] = text(first["all_zones"])
        if pd.notna(first["olt_case_no"]):
            props["l"] = first["olt_case_no"]
        if pd.notna(first["by_law_number"]):
            props["y"] = first["by_law_number"]
        if first["pending"]:
            props["p"] = f"{first['pending_zoning_code']} (By-law {first['pending_by_law_number']}, Council {first['pending_council_app_date']})"
        if pd.notna(first["mpac_property_code"]):
            props["u"] = int(float(first["mpac_property_code"]))
        return props

    groups = p.groupby("geom_group", sort=False)
    info = pd.DataFrame({gid: per_group(g) for gid, g in groups}).T
    shapes = groups.agg(geometry=("geometry", "first"), ward=("ward", "first"))
    shapes = gpd.GeoDataFrame(shapes.join(info), geometry="geometry", crs="EPSG:4326")
    shapes = shapes[shapes["k"].notna() | shapes["z"].notna()]
    m = shapes.to_crs(METRIC_CRS)
    m["geometry"] = m.geometry.simplify(PARCEL_SIMPLIFY_M)
    shapes = m.to_crs("EPSG:4326")
    shapes["geometry"] = rounded(shapes.geometry.values)
    shapes = shapes[~shapes.geometry.is_empty]

    out_dir = SITE / "parcels"
    for old in out_dir.glob("ward-*.json") if out_dir.exists() else []:
        old.unlink()
    ward_counts = {}
    for ward, g in shapes.groupby("ward"):
        geo = json.loads(g.drop(columns="ward").to_json(drop_id=True))
        for f in geo["features"]:
            props = f["properties"]
            for key in [key for key, v in props.items() if v is None or (isinstance(v, float) and v != v)]:
                props.pop(key)
        write(out_dir / f"ward-{int(float(ward))}.json", geo)
        ward_counts[int(float(ward))] = len(g)

    # Search index: every roll, pointing at its footprint's ward and an interior point.
    pts = p.drop_duplicates("geom_group").set_index("geom_group").geometry.representative_point()
    srch = p[["address", "property_num", "ward", "geom_group"]].copy()
    srch["x"] = srch["geom_group"].map(pts.x).round(COORD_DECIMALS)
    srch["y"] = srch["geom_group"].map(pts.y).round(COORD_DECIMALS)
    # The map feature for a shared footprint carries its first roll; point every roll at that one.
    srch["feature_roll"] = srch["geom_group"].map(p.drop_duplicates("geom_group").set_index("geom_group")["property_num"])
    srch = srch.dropna(subset=["address"])
    # The sixth element is 0 when the roll is its own feature's roll (most rows), to keep the file small.
    write(SITE / "search.json", [[r.address, r.property_num, int(float(r.ward)), r.y, r.x,
                                  0 if r.feature_roll == r.property_num else r.feature_roll]
                                 for r in srch.itertuples()])

    # Zoning polygons for the zoomed-out view.
    z = gpd.read_file(RAW / "zoning.geojson").to_crs(METRIC_CRS)
    z = z[z.geometry.notna() & ~z.is_empty]
    z["geometry"] = shapely.make_valid(z.geometry.values)
    z["c"] = (z["ZONING_CATEGORY"].replace({"Low Density Residential": "Residential"})
              .map(cat_idx).fillna(cat_idx["Uncategorized"]).astype(int))
    z["b"] = z["PARENT_BY_LAW_NUMBER"].replace({"1964": "1964 Dundas (pre-3581-86)"}).map(bylaw_idx)
    z["zc"] = z["ZONING_CODE"].fillna("")
    z = z.dissolve(by=["zc", "c", "b"], as_index=False, dropna=False)
    z["geometry"] = z.geometry.simplify(ZONING_SIMPLIFY_M)
    z = z.to_crs("EPSG:4326")
    z["geometry"] = rounded(z.geometry.values)
    z = z[~z.geometry.is_empty][["zc", "c", "b", "geometry"]]
    write(SITE / "zoning.json", json.loads(z.to_json(drop_id=True)))

    w = gpd.read_file(RAW / "wards.geojson").to_crs(METRIC_CRS)
    w["geometry"] = w.geometry.simplify(15)
    w = w.to_crs("EPSG:4326")
    w["geometry"] = rounded(w.geometry.values)
    write(SITE / "wards.json", json.loads(w[["WARD", "geometry"]].to_json(drop_id=True)))

    summary = json.loads((ROOT / "output" / "summary.json").read_text())
    manifest = summary["source_manifest"]
    write(SITE / "meta.json", {
        "categories": CATEGORIES,
        "bylaws": bylaws,
        "zones": zones,
        "flags": FLAGS,
        "ward_counts": ward_counts,
        "downloaded_at": manifest["parcels"]["downloaded_at"],
        "stats": {k: summary[k] for k in [
            "n_parcel_polygons", "n_distinct_footprints", "share_parcels_with_zoning", "n_split_zoned",
            "share_split_zoned", "by_bylaw", "by_category", "n_has_exception", "n_has_holding",
            "n_olt_tag", "n_pending_council_approved", "n_geometry_suspect"]},
    })


if __name__ == "__main__":
    main()
