"""Read the raw layers written by fetch.py.

Layers are stored gzip-compressed (raw/<key>.geojson.gz) so they fit under GitHub's 100 MB file
limit (parcels: 136 MB plain, 19 MB compressed). GDAL reads them through its /vsigzip/ prefix.
"""
from pathlib import Path

import geopandas as gpd

RAW = Path(__file__).resolve().parent.parent / "raw"


def raw_path(key):
    return RAW / f"{key}.geojson.gz"


def read_raw(key):
    return gpd.read_file(f"/vsigzip/{raw_path(key)}")
