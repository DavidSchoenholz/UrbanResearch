"""Parse downloaded TRREB PDFs into CSVs and build a self-contained HTML map + price log.

    python build.py --data-dir data --out out

Reads  data/marketwatch/*.pdf, data/community/*.pdf, data/boundaries/nbhd158.geojson
Writes out/district_monthly.csv, out/community_quarterly.csv, out/community_match.csv,
       out/parse_report.csv and out/toronto_prices.html

TRREB communities are matched to City neighbourhoods by exact normalized name only. Anything
else is listed as unmapped on the page; nothing is fuzzy-matched or guessed.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

import community
import fetch
import marketwatch

HERE = Path(__file__).parent
SIMPLIFY_M = 20      # polygon simplification tolerance, metres (EPSG:2952)
SVG_WIDTH = 900


def norm(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def parse_all(pdf_dir, parse_pdf, kind, keep=lambda path: True):
    frames, report = [], []
    for pdf in sorted(Path(pdf_dir).glob("*.pdf")):
        if not keep(pdf):
            continue
        df, problems = parse_pdf(pdf)
        report.append({"kind": kind, "file": pdf.name, "rows": len(df),
                       "status": "ok" if len(df) and not problems else "FAILED",
                       "problems": "; ".join(problems)})
        if len(df) and not problems:
            frames.append(df)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return out, pd.DataFrame(report)


def match_communities(comm, nbhd):
    """Exact normalized-name match of TRREB communities to City neighbourhood names."""
    by_name = {}
    for code, name in zip(nbhd["AREA_SHORT_CODE"], nbhd["AREA_NAME"]):
        by_name.setdefault(norm(name), []).append((code, name))
    rows = []
    for (district, name), _ in comm.groupby(["district", "community"]):
        hits = by_name.get(norm(name), [])
        status = "matched" if len(hits) == 1 else ("ambiguous" if hits else "unmapped")
        rows.append({"district": district, "community": name,
                     "area_code": hits[0][0] if len(hits) == 1 else None,
                     "area_name": hits[0][1] if len(hits) == 1 else None, "status": status})
    match = pd.DataFrame(rows)
    # a neighbourhood claimed by two communities is ambiguous: use neither
    dup = match["area_code"].notna() & match["area_code"].duplicated(keep=False)
    match.loc[dup, ["area_code", "area_name"]] = None
    match.loc[dup, "status"] = "ambiguous"
    return match


def svg_geometry(gdf):
    """Project to EPSG:2952, simplify, and return (path strings, width, height) for an SVG viewBox."""
    g = gdf.to_crs(2952)
    g["geometry"] = g.geometry.simplify(SIMPLIFY_M)
    minx, miny, maxx, maxy = g.total_bounds
    scale = SVG_WIDTH / (maxx - minx)

    def ring(coords):
        pts = [f"{(x - minx) * scale:.1f} {(maxy - y) * scale:.1f}" for x, y in coords]
        return "M" + "L".join(pts) + "Z"

    paths = []
    for geom in g.geometry:
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        paths.append("".join(ring(p.exterior.coords) + "".join(ring(i.coords) for i in p.interiors)
                             for p in polys))
    return paths, SVG_WIDTH, round((maxy - miny) * scale)


def clean(v):
    return None if pd.isna(v) else float(v)


def build_payload(districts, comm, match, nbhd):
    paths, w, h = svg_geometry(nbhd)
    code_to_comm = {r.area_code: r for r in match.itertuples() if r.status == "matched"}
    quarters = sorted(comm["period"].unique())

    vals = {}
    keyed = comm.merge(match[match["status"] == "matched"][["district", "community", "area_code"]],
                       on=["district", "community"])
    for r in keyed.itertuples():
        vals.setdefault(r.area_code, {})[r.period] = [clean(r.sales), clean(r.avg_price), clean(r.median_price)]

    areas = []
    for code, name, d in zip(nbhd["AREA_SHORT_CODE"], nbhd["AREA_NAME"], paths):
        c = code_to_comm.get(code)
        areas.append({"id": code, "name": name, "d": d,
                      "community": c.community if c else None, "district": c.district if c else None})

    # full monthly range: a month that failed validation is a gap in the chart, not a closed-up axis
    periods = [str(p) for p in pd.period_range(districts["period"].min(), districts["period"].max(), freq="M")]
    codes = sorted(districts["district"].unique(), key=lambda c: (c != "CITY", c))
    series = {m: {c: [] for c in codes} for m in ("avg_price", "median_price", "sales")}
    wide = {m: districts.pivot(index="period", columns="district", values=m).reindex(periods)
            for m in series}
    for m in series:
        for c in codes:
            series[m][c] = [clean(v) for v in wide[m][c]] if c in wide[m] else [None] * len(periods)

    unmapped = match[match["status"] != "matched"][["district", "community"]].sort_values(
        ["district", "community"]).to_dict("records")
    return {"width": w, "height": h, "areas": areas, "quarters": quarters, "values": vals,
            "periods": periods, "codes": codes, "series": series, "unmapped": unmapped}


def render(payload, out_path):
    template = (HERE / "map_template.html").read_text(encoding="utf8")
    blob = json.dumps(payload, allow_nan=False, separators=(",", ":")).replace("</", "<\\/")
    out_path.write_text(template.replace("__DATA__", blob), encoding="utf8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--since", default="1107", help="YYMM; earliest Market Watch report to parse")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    floor = fetch._year_month(a.since)
    districts, rep1 = parse_all(a.data_dir / "marketwatch", marketwatch.parse_pdf, "marketwatch",
                                keep=lambda f: fetch._year_month(f.stem[2:]) >= floor)
    comm, rep2 = parse_all(a.data_dir / "community", community.parse_pdf, "community")
    report = pd.concat([rep1, rep2], ignore_index=True)
    report.to_csv(a.out / "parse_report.csv", index=False)
    print(report.groupby(["kind", "status"]).size().to_string())
    if districts.empty or comm.empty:
        raise SystemExit("nothing parsed; run fetch.py first")

    n_dup = int(comm.duplicated(["period", "district", "community"]).sum())
    comm = comm.drop_duplicates(["period", "district", "community"])
    districts.sort_values(["period", "district"]).to_csv(a.out / "district_monthly.csv", index=False)
    comm.sort_values(["period", "district", "community"]).to_csv(a.out / "community_quarterly.csv", index=False)

    import geopandas as gpd
    nbhd = gpd.read_file(a.data_dir / "boundaries" / "nbhd158.geojson")
    match = match_communities(comm, nbhd)
    match.to_csv(a.out / "community_match.csv", index=False)
    print(match["status"].value_counts().to_string(), f"\n(duplicate community rows dropped: {n_dup})")

    render(build_payload(districts, comm, match, nbhd), a.out / "toronto_prices.html")
    print("wrote", a.out / "toronto_prices.html")


if __name__ == "__main__":
    main()
