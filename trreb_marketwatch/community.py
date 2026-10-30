"""Parse TRREB Toronto Community Reports (West / Central / East) into quarterly community rows."""
import re

import numpy as np
import pandas as pd

from pdftext import pdf_text

TOKEN = r"(?:\$?-?[\d,]+(?:\.\d+)?%?|-{1,2}|n/a|N/A)"
ROW = re.compile(rf"^\s*(?P<label>[A-Za-z][A-Za-z0-9 .,\-'/&()]*?)\s{{2,}}(?P<rest>(?:{TOKEN}\s+)*{TOKEN})\s*$")
HEAD = re.compile(r"Toronto ([CWE]\d{2}) Community Breakdown")
PERIOD = re.compile(r"All Home Types\s+(\d{4}) Q([1-4])")
COLS = ["sales", "dollar_volume", "avg_price", "median_price", "new_listings", "active_listings",
        "avg_sp_lp_pct", "avg_dom"]
PRICE_COLS = ["dollar_volume", "avg_price", "median_price", "avg_sp_lp_pct", "avg_dom"]


def num(tok):
    if tok in ("-", "--", "n/a", "N/A"):
        return np.nan
    return float(tok.replace("$", "").replace(",", "").replace("%", ""))


def parse_text(text):
    """Return (DataFrame, problems). Rows under each 'Toronto XNN Community Breakdown' heading.

    TRREB suppresses statistics for communities with two or fewer sales, so those rows are
    short; only their sales count is kept and everything else stays NaN. Rows with at least 3 sales are checksum-validated
    (sales x average price ~ dollar volume).
    """
    recs, district, period = [], None, None
    for line in text.splitlines():
        h = HEAD.search(line)
        if h:
            district = h[1]
            continue
        p = PERIOD.search(line)
        if p and district:
            period = f"{p[1]}Q{p[2]}"
            continue
        if "The source of all slides" in line:
            district = None
            continue
        if not district or not period:
            continue
        m = ROW.match(line)
        if not m or m["label"].strip() == "Community":
            continue
        vals = [num(t) for t in m["rest"].split()]
        if len(vals) < len(COLS):
            # suppressed row (two or fewer sales): the printed numbers are not the full column set,
            # so only the sales count is trusted; mapping them by position would invent prices
            vals = vals[:1]
        recs.append({**dict(zip(COLS, vals)), "period": period, "district": district,
                     "community": re.sub(r"\s+", " ", m["label"]).strip()})
    df = pd.DataFrame(recs)
    if df.empty:
        return df, ["no community rows"]
    df.loc[df["sales"] == 0, PRICE_COLS] = np.nan  # no sales: a price of 0 is "not reported", not $0
    chk = df[df["sales"] >= 3]
    err = (chk["sales"] * chk["avg_price"] / chk["dollar_volume"] - 1).abs()
    problems = [f"checksum failed on {int((err > 0.02).sum())} rows"] if (err > 0.02).any() else []
    return df, problems


def parse_pdf(pdf):
    try:
        text = pdf_text(pdf)
    except Exception as exc:
        return pd.DataFrame(), [f"extract failed: {exc}"]
    return parse_text(text)
