"""Optional spatial helpers. geopandas is imported lazily so the rest of the package runs without it."""


def _geopandas():
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise ImportError("spatial helpers need geopandas: pip install geopandas") from exc
    return gpd


def attach_parcel_id(points, parcels, parcel_id_col="parcel_id"):
    """Assign each point (GeoDataFrame) the id of the parcel polygon that contains it.

    A point on a shared boundary matches several parcels; the first is kept and counted in
    n_multi_match. Returns (points_with_parcel_id, stats). Unmatched points keep a null id.
    Geocoding quality, not this join, usually limits the match rate, so report n_unmatched.
    """
    gpd = _geopandas()
    if parcel_id_col in points.columns:
        raise ValueError(f"points already has '{parcel_id_col}'")
    if points.crs != parcels.crs:
        points = points.to_crs(parcels.crs)
    joined = gpd.sjoin(points, parcels[[parcel_id_col, "geometry"]], how="left", predicate="intersects")
    dup = joined.index.duplicated(keep="first")
    joined = joined[~dup].drop(columns="index_right")
    stats = {
        "n_points": int(len(points)),
        "n_unmatched": int(joined[parcel_id_col].isna().sum()),
        "n_multi_match": int(dup.sum()),
    }
    return joined, stats
