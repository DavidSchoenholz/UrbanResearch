"""Polite, resumable download of publicly linked TRREB reports and City of Toronto boundaries.

TRREB's site states that its content is copyright TRREB. These files are for private analysis:
do not commit or republish them. robots.txt is honoured and requests are rate-limited.

    python fetch.py marketwatch --data-dir data     # monthly Market Watch PDFs (default: 2011-07 onward)
    python fetch.py community --data-dir data       # Toronto West/Central/East quarterly community reports
    python fetch.py boundaries --data-dir data      # City of Toronto neighbourhood polygons (open licence)
"""
import argparse
import json
import re
import time
import urllib.request
import urllib.robotparser
from pathlib import Path

BASE = "https://trreb.ca"
UA = "Mozilla/5.0 (personal urban-data research; low-rate)"
CKAN = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=neighbourhoods"

MW_RE = re.compile(r"/wp-content/files/market-stats/market-watch/(mw\d{4})\.pdf")
COMM_RE = re.compile(r"/wp-content/files/market-stats/community-reports/\d{4}/Q[1-4]/"
                     r"Toronto(?:West|Central|East)Q[1-4]\d{4}\.pdf")


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def robots():
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{BASE}/robots.txt")
    rp.parse(get(f"{BASE}/robots.txt").decode("utf8", "replace").splitlines())
    return rp


def _year_month(code):
    """'1107' -> (2011, 7); two-digit years of 90 or more are 1990s ('9802' -> (1998, 2))."""
    yy = int(code[:2])
    return (1900 if yy >= 90 else 2000) + yy, int(code[2:4])


def marketwatch_paths(html, since="1107"):
    """Archive-page paths for reports at or after `since` (YYMM). The pre-2011-07 layout is not parsed."""
    floor = _year_month(since)
    return sorted({m.group(0) for m in MW_RE.finditer(html) if _year_month(m.group(1)[2:]) >= floor})


def community_paths(html):
    return sorted(set(COMM_RE.findall(html)))


def download(paths, dest, delay=1.5):
    dest.mkdir(parents=True, exist_ok=True)
    rp = robots()
    done = failed = 0
    for p in paths:
        out = dest / Path(p).name
        if out.exists() and out.read_bytes()[:4] == b"%PDF":
            continue
        if not rp.can_fetch(UA, BASE + p):
            print("disallowed by robots.txt:", p)
            continue
        try:
            data = get(BASE + p, timeout=90)
        except Exception as exc:  # network / HTTP error: report and carry on
            print("failed:", p, exc)
            failed += 1
        else:
            if data[:4] == b"%PDF":
                out.write_bytes(data)
                done += 1
            else:
                print("not a PDF:", p)
                failed += 1
        time.sleep(delay)
    print(f"downloaded {done}, failed {failed}, into {dest}")


def fetch_boundaries(data_dir):
    """Current (158) and historical (140) neighbourhood polygons, GeoJSON, EPSG:4326."""
    pkg = json.loads(get(CKAN))["result"]
    out = data_dir / "boundaries"
    out.mkdir(parents=True, exist_ok=True)
    for name, fname in [("Neighbourhoods - 4326.geojson", "nbhd158.geojson"),
                        ("Neighbourhoods - historical 140 - 4326.geojson", "nbhd140.geojson")]:
        url = next(r["url"] for r in pkg["resources"] if r["name"] == name)
        (out / fname).write_bytes(get(url, timeout=120))
        print("wrote", out / fname)
    print("licence:", pkg.get("license_title"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["marketwatch", "community", "boundaries"])
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between requests (keep >= 1)")
    ap.add_argument("--since", default="1107", help="YYMM; earliest Market Watch report to fetch")
    a = ap.parse_args()
    if a.what == "boundaries":
        fetch_boundaries(a.data_dir)
    elif a.what == "marketwatch":
        html = get(f"{BASE}/market-watch-archive/").decode("utf8", "replace")
        download(marketwatch_paths(html, a.since), a.data_dir / "marketwatch", a.delay)
    else:
        html = get(f"{BASE}/market-data/community-reports/").decode("utf8", "replace")
        download(community_paths(html), a.data_dir / "community", a.delay)


if __name__ == "__main__":
    main()
