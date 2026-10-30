"""Download the City of Hamilton layers needed for the parcel zoning map.

Pages through the City's public ArcGIS REST MapServer layers and saves each as
GeoJSON (EPSG:4326) in raw/. Also writes raw/manifest.json recording the URL,
server-side record count, downloaded count and download time of each layer, so a
later run can tell whether the source changed.

Usage (from hamilton/parcel_zoning/):
    python scripts/fetch.py            # all layers
    python scripts/fetch.py zoning     # one layer by key

No API key is needed. The server caps each request (maxRecordCount 5000-20000),
so we page with resultOffset ordered by OBJECTID.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
BASE = "https://spatialsolutions.hamilton.ca/webgis/rest/services/General"
# The server returns 403 to Python's default "Python-urllib" user agent, so send our own.
HEADERS = {"User-Agent": "UrbanResearch-hamilton-parcel-zoning/1.0 (research; github.com/DavidSchoenholz/UrbanResearch)"}

# key -> (service/layer path, page size). Layer ids checked 2026-10-30; the City can
# renumber layers when it republishes a service, so re-check names if counts look wrong.
LAYERS = {
    "zoning": ("Zoning/MapServer/9", 2000),             # Zoning Boundaries (in force)
    "zoning_council_approved": ("Zoning/MapServer/8", 2000),  # approved by Council, not yet final and binding
    "parcels": ("Zoning/MapServer/15", 5000),           # Property Parcels (for Zoning Lookup)
    "interim_control": ("Zoning/MapServer/19", 1000),   # Interim Control By-law zone
    "compliance_review": ("Zoning/MapServer/12", 1000),  # Zoning Compliance Review Required
    "h_converted_parcels": ("Zoning/MapServer/11", 1000),  # Hamilton-specific converted dwellings
    "wards": ("Political/MapServer/15", 1000),          # Post-2018 election wards
    "communities": ("Political/MapServer/7", 1000),     # former municipalities
}


def get_json(url, params, tries=5):
    q = url + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers=HEADERS), timeout=180) as r:
                d = json.load(r)
            if "error" in d:
                raise RuntimeError(d["error"])
            return d
        except Exception as exc:  # network blips and server-side timeouts both happen
            if i == tries - 1:
                raise
            wait = 2 ** (i + 1)
            print(f"  retry {i + 1} after {exc!r}; waiting {wait}s", flush=True)
            time.sleep(wait)


def fetch_layer(key):
    path, page = LAYERS[key]
    url = f"{BASE}/{path}"
    meta = get_json(url, {"f": "json"})
    n = get_json(url + "/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    print(f"{key}: {meta['name']} - {n} records", flush=True)

    feats = []
    offset = 0
    while offset < n:
        d = get_json(url + "/query", {
            "where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": 4326,
            "orderByFields": "OBJECTID", "resultOffset": offset, "resultRecordCount": page,
            "f": "geojson",
        })
        got = d.get("features", [])
        if not got:
            break
        feats.extend(got)
        offset += len(got)
        print(f"  {offset}/{n}", flush=True)

    RAW.mkdir(exist_ok=True)
    out = RAW / f"{key}.geojson"
    with open(out, "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f)

    return {
        "layer_name": meta["name"], "url": url, "server_count": n, "downloaded": len(feats),
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fields": [fl["name"] for fl in meta.get("fields") or []],
    }


def main(keys):
    RAW.mkdir(exist_ok=True)
    mpath = RAW / "manifest.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {}
    for k in keys:
        manifest[k] = fetch_layer(k)
        if manifest[k]["downloaded"] != manifest[k]["server_count"]:
            print(f"WARNING: {k} downloaded {manifest[k]['downloaded']} of {manifest[k]['server_count']}")
        mpath.write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:] or list(LAYERS))
