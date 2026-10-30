"""Parse TRREB Market Watch PDFs into monthly Toronto district rows.

Covers the layout used from the July 2011 report onward. The first complete set of Toronto
district rows in a report is the monthly, all-home-types table. Every file is validated: each
row's sales x average price must match its dollar volume (confirming the columns lined up), and
the districts must sum to the City of Toronto row. Files that fail are reported, never guessed.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from pdftext import pdf_text

TOKEN = r"(?:\$?-?[\d,]+(?:\.\d+)?%?|-{1,2}|n/a|N/A)"
ROW = re.compile(rf"^\s*(?P<label>[A-Za-z][A-Za-z0-9 .\-'/&()]*?)\s{{2,}}(?P<rest>(?:{TOKEN}\s+)*{TOKEN})\s*$")
DISTRICT = re.compile(r"^Toronto ([CWE]\d{2})$")
CITY = re.compile(r"^City of Toronto( Total)?$")
COLS = ["sales", "dollar_volume", "avg_price", "median_price", "new_listings", "snlr_pct",
        "active_listings", "months_inventory", "avg_sp_lp_pct", "avg_ldom", "avg_pdom"]
PRICE_COLS = ["dollar_volume", "avg_price", "median_price", "avg_sp_lp_pct", "avg_ldom", "avg_pdom"]


def num(tok):
    if tok in ("-", "--", "n/a", "N/A"):
        return np.nan
    return float(tok.replace("$", "").replace(",", "").replace("%", ""))


def period_of(name):
    """'mw2609' -> '2026-09'; two-digit years of 90 or more are 1990s ('mw9802' -> '1998-02')."""
    yy = int(name[2:4])
    return f"{(1900 if yy >= 90 else 2000) + yy}-{name[4:6]}"


def parse_text(text, period):
    """Return (DataFrame, problems). District 'CITY' is the City of Toronto total row."""
    seen, recs, city = set(), [], None
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        toks = m["rest"].split()
        if len(toks) < 8:
            continue
        label = re.sub(r"\s+", " ", m["label"]).strip()
        vals = [num(t) for t in toks]
        if CITY.match(label) and not recs:
            city = vals
        d = DISTRICT.match(label)
        if not d:
            continue
        if d[1] in seen:  # the next table (year-to-date) starts
            break
        seen.add(d[1])
        recs.append({**dict(zip(COLS, vals)), "period": period, "district": d[1]})
    if not recs:
        return pd.DataFrame(), ["no Toronto district rows"]

    df = pd.DataFrame(recs)
    problems = []
    df.loc[df["sales"] == 0, PRICE_COLS] = np.nan  # no sales: a price of 0 is "not reported", not $0
    has_sales = df["sales"] > 0
    err = (df.loc[has_sales, "sales"] * df.loc[has_sales, "avg_price"]
           / df.loc[has_sales, "dollar_volume"] - 1).abs()
    if (err > 0.02).any():
        problems.append(f"checksum failed on {int((err > 0.02).sum())} rows")
    if city is None:
        problems.append("no City of Toronto row to validate against")
    else:
        if df["sales"].sum() != city[0]:
            problems.append(f"district sales {df['sales'].sum():.0f} != City of Toronto {city[0]:.0f}")
        df = pd.concat([df, pd.DataFrame([{**dict(zip(COLS, city)), "period": period, "district": "CITY"}])],
                       ignore_index=True)
    return df, problems


def parse_pdf(pdf):
    name = Path(pdf).stem
    try:
        return parse_text(pdf_text(pdf), period_of(name))
    except Exception as exc:  # corrupt PDF or pdftotext failure
        return pd.DataFrame(), [f"extract failed: {exc}"]
