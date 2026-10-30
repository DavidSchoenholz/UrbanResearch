"""Spot-check the parcel zoning table against the City's live zoning service.

For a random sample of parcels, sends the parcel's interior point to the City's Zoning Boundaries
layer (a server-side point-in-polygon query, independent of our local overlay) and compares the
zoning code it returns with our primary zone. Split-zoned parcels are sampled separately, because
there an interior point can legitimately land in the secondary zone.

Writes output/validation.json. Run from hamilton/parcel_zoning/:
    python scripts/validate.py [n_per_stratum]
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from rawio import read_raw

ROOT = Path(__file__).resolve().parent.parent
URL = "https://spatialsolutions.hamilton.ca/webgis/rest/services/General/Zoning/MapServer/9/query"
HEADERS = {"User-Agent": "UrbanResearch-hamilton-parcel-zoning/1.0 (research; github.com/DavidSchoenholz/UrbanResearch)"}
SEED = 20261030


def city_zone_at(x, y):
    q = URL + "?" + urllib.parse.urlencode({
        "geometry": f"{x},{y}", "geometryType": "esriGeometryPoint", "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "outFields": "ZONING_CODE", "returnGeometry": "false",
        "f": "json",
    })
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers=HEADERS), timeout=60) as r:
                feats = json.load(r).get("features", [])
            return sorted({(f["attributes"]["ZONING_CODE"] or "").strip() for f in feats})
        except Exception:
            time.sleep(2 ** (i + 1))
    return None


def main(n):
    tab = pd.read_csv(ROOT / "output" / "hamilton_parcel_zoning.csv.gz", dtype=str)
    tab = tab[(tab["has_zoning"] == "True") & (tab["geometry_suspect"] == "False")]
    strata = {"single_zone": tab[tab["split_zoned"] == "False"], "split_zoned": tab[tab["split_zoned"] == "True"]}
    parcels = read_raw("parcels").set_index("OBJECTID")

    result = {"checked_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "seed": SEED}
    mismatches = []
    for name, df in strata.items():
        s = df.sample(min(n, len(df)), random_state=SEED)
        agree = checked = 0
        for _, r in s.iterrows():
            pt = parcels.loc[int(r["parcel_oid"]), "geometry"].representative_point()
            codes = city_zone_at(pt.x, pt.y)
            if codes is None:
                continue
            checked += 1
            if r["zoning_code"] in codes:
                agree += 1
            else:
                mismatches.append({"stratum": name, "parcel_oid": r["parcel_oid"], "address": r["address"],
                                   "ours": r["zoning_code"], "all_ours": r["all_zones"], "city_at_point": codes})
        result[name] = {"checked": checked, "agree": agree, "agree_share": round(agree / checked, 4) if checked else None}
        print(name, result[name], flush=True)
    result["mismatches"] = mismatches
    (ROOT / "output" / "validation.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
