"""Regenerate docs/data/data.js from the work branches, so figures are copied, not retyped.

Run from the repo root after `git fetch origin`:  python3 docs/build_data.py
"""
import csv, io, json, subprocess

BRANCHES = {
    "toronto": "origin/claude/determined-lovelace-oc32xm",
    "phase2": "origin/claude/optimistic-fermat-c1mogk",
    "hamilton": "origin/claude/nice-davinci-kpvdwk",
}


def show(branch, path):
    return subprocess.check_output(["git", "show", f"{branch}:{path}"], text=True)


def sha(branch):
    return subprocess.check_output(["git", "rev-parse", "--short", branch], text=True).strip()


inventory = list(csv.DictReader(io.StringIO(show(BRANCHES["toronto"], "phase1/inventory.csv"))))
summary = json.loads(show(BRANCHES["hamilton"], "hamilton/parcel_zoning/output/summary.json"))
validation = json.loads(show(BRANCHES["hamilton"], "hamilton/parcel_zoning/output/validation.json"))

keep = ["n_parcel_polygons", "n_unique_property_num", "n_duplicate_property_num_rows",
        "parcel_area_sum_km2", "parcel_union_km2", "n_zoning_polygons", "n_pieces",
        "n_parcels_without_zoning", "n_split_zoned", "share_split_zoned", "by_bylaw",
        "by_category", "top_zone_codes", "n_has_exception", "n_has_holding",
        "n_pending_council_approved", "n_olt_tag", "n_geometry_suspect"]
data = {
    "snapshot": {k: sha(v) for k, v in BRANCHES.items()},
    "inventory": inventory,
    "hamilton": {k: summary[k] for k in keep},
    "hamilton_validation": {k: validation[k] for k in ("single_zone", "split_zoned")},
}
with open("docs/data/data.js", "w") as f:
    f.write("window.DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
print("wrote docs/data/data.js", {k: len(v) if hasattr(v, "__len__") else v for k, v in data.items()})
