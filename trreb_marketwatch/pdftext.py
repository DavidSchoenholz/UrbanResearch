"""PDF text with rows rebuilt from word coordinates.

`pdftotext -layout` interleaves neighbouring rows in some TRREB reports (overlapping text boxes),
which scrambles table rows. Words from `pdftotext -bbox` carry exact positions, so rows are rebuilt
by grouping words that share a vertical position and ordering them left to right.
"""
import html
import re
import subprocess

WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="[\d.]+">(.*?)</word>')
LINE_TOL = 3.0   # points: words within this vertical distance belong to one row
COL_GAP = 6.0    # points: a horizontal gap wider than this becomes a column break (two spaces)
PLACEHOLDERS = {"Abc"}  # ghost text that some reports embed mid-row; never data
MIN_DATA_WORDS = 3  # a row with fewer words is treated as a ghost/label row, not a reference row


def _overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 1.0


def _dedupe(row):
    """Collapse identical overlapping words (a value and its stale copy) to a single word."""
    keep = []
    for w in sorted(row, key=lambda w: w[0]):
        if not any(k[3] == w[3] and _overlap(w, k) for k in keep):
            keep.append(w)
    return keep


def _drop_stale(row, prev):
    """Remove stale overlay words: in some reports each row also carries a copy of the previous data
    row's values printed at the same positions. A word is dropped only if it overlaps another word on
    its row AND exactly duplicates a word of the previous data row at that position, so legitimately
    repeated values (two rows both at '100%') survive. Only the immediately preceding data row is a
    reference: an older row that happens to hold the same number must not erase a real value."""
    row = _dedupe(row)
    if not prev:
        return row
    keep = []
    for w in row:
        conflict = any(o is not w and _overlap(w, o) for o in row)
        stale = any(p[3] == w[3] and _overlap(w, p) for p in prev)
        if not (conflict and stale):
            keep.append(w)
    return keep


def lines_from_words(words):
    """words: iterable of (x0, y, x1, text) on one page -> list of row strings."""
    ws = sorted((w for w in words if w[3] not in PLACEHOLDERS), key=lambda w: (w[1], w[0]))
    rows, cur, y0 = [], [], None
    for w in ws:
        if y0 is None or w[1] - y0 > LINE_TOL:
            if cur:
                rows.append(cur)
            cur, y0 = [], w[1]
        cur.append(w)
    if cur:
        rows.append(cur)
    out, prev_data = [], []
    for r in rows:
        r = sorted(_drop_stale(r, prev_data), key=lambda w: w[0])
        if len(r) >= MIN_DATA_WORDS:
            prev_data = r
        s = r[0][3]
        for a, w in zip(r, r[1:]):
            s += ("  " if w[0] - a[2] > COL_GAP else " ") + w[3]
        out.append(s)
    return out


def pdf_text(pdf):
    raw = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], capture_output=True, text=True,
                         check=True).stdout
    pages = []
    for chunk in raw.split("<page ")[1:]:
        words = [(float(x0), float(y), float(x1), html.unescape(t)) for x0, y, x1, t in WORD.findall(chunk)]
        pages.append("\n".join(lines_from_words(words)))
    return "\n\n".join(pages)
