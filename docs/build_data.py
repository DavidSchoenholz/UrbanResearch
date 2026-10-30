"""Build the overview site's data file from the research branches.

The site in docs/ shows work that lives on three unmerged branches. This script reads the source
files straight out of git at pinned commits (so every figure on the site is copied, not retyped)
and writes:

  docs/data/site-data.json   the extracted content, for inspection and for docs/checks/
  docs/data/site-data.js     the same content as `window.SITE_DATA = ...`, so the pages also work
                             when opened from disk (browsers block fetch() of local JSON files)

Run from the repository root:

    git fetch origin
    python docs/build_data.py              # pinned commits below
    python docs/build_data.py --latest     # current tips of the branches, then update SOURCES

Standard library only.
"""
import argparse
import csv
import html
import io
import json
import re
import subprocess
from pathlib import Path

DOCS = Path(__file__).resolve().parent
REPO = "DavidSchoenholz/UrbanResearch"

# Commits read for this snapshot. Update together with the "snapshot" date when re-running.
SNAPSHOT_DATE = "2026-10-30"
SOURCES = {
    "phase1": {
        "branch": "claude/determined-lovelace-oc32xm",
        "sha": "3c762341df1648a8bbe0bc43b24518b65e2e42ab",
        "title": "Phase 1: Toronto feasibility study",
    },
    "phase2": {
        "branch": "claude/optimistic-fermat-c1mogk",
        "sha": "e4c830be30388269f8be51f95af330fd7f53f0fc",
        "title": "Phase 2: analysis code skeleton and ideas list",
    },
    "hamilton": {
        "branch": "claude/nice-davinci-kpvdwk",
        "sha": "b2d1c2c0283140760eaa9634071dd104a5004233",
        "title": "Hamilton parcel-to-zoning match",
    },
}


def git_show(key, path):
    src = SOURCES[key]
    rev = src["sha"]
    return subprocess.run(["git", "show", f"{rev}:{path}"], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def gh_url(key, path):
    return f"https://github.com/{REPO}/blob/{SOURCES[key]['sha']}/{path}"


# ---------------------------------------------------------------- markdown helpers

def inline(md):
    """Inline markdown (bold, italic, code, links) to safe HTML."""
    out = html.escape(md, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                 lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', out)
    return out


def sections(md, level):
    """Split markdown into {heading: body} at the given heading level."""
    marker = "#" * level + " "
    out, cur, buf = {}, None, []
    for line in md.splitlines():
        if line.startswith(marker):
            if cur is not None:
                out[cur] = "\n".join(buf).strip()
            cur, buf = line[len(marker):].strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf).strip()
    return out


def find_section(secs, prefix):
    for k, v in secs.items():
        if k.startswith(prefix):
            return v
    raise KeyError(prefix)


def list_items(md):
    """Top-level list items (numbered or bulleted), each with its nested sub-items.

    Returns [{"html": first line, "sub": [html, ...]}]. Continuation lines are joined.
    """
    items = []
    for line in md.splitlines():
        if not line.strip():
            continue
        top = re.match(r"^(?:\d+\.|-)\s+(.*)", line)
        sub = re.match(r"^\s{2,}(?:\d+\.|-)\s+(.*)", line)
        if top:
            items.append({"md": top.group(1), "sub": []})
        elif sub and items:
            items[-1]["sub"].append(sub.group(1))
        elif items and line.startswith(" "):
            target = items[-1]["sub"]
            if target:
                target[-1] += " " + line.strip()
            else:
                items[-1]["md"] += " " + line.strip()
    return [{"html": inline(i["md"]), "sub": [inline(s) for s in i["sub"]]} for i in items]


def table_after(md, header_start):
    """Parse the markdown table whose header row starts with `header_start`."""
    lines = md.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(header_start):
            rows = []
            for row in lines[i:]:
                if not row.startswith("|"):
                    break
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-+:?", c) for c in cells):
                    continue
                rows.append(cells)
            return {"header": [inline(c) for c in rows[0]],
                    "rows": [[inline(c) for c in r] for r in rows[1:]]}
    raise KeyError(header_start)


def split_bold_lead(md_item):
    """'**Lead.** rest' -> ('Lead.', 'rest') as HTML."""
    m = re.match(r"\*\*(.+?)\*\*\s*(.*)", md_item)
    if not m:
        return None, inline(md_item)
    return inline(m.group(1)), inline(m.group(2))


# ---------------------------------------------------------------- Phase 1

def build_phase1():
    summary = git_show("phase1", "phase1/summary.md")
    feas = git_show("phase1", "phase1/feasibility.md")
    s = sections(summary, 2)

    verdict = re.search(r"\*\*Verdict: (.+?)\.\*\*\s*(.*)", summary).groups()

    # Key limitations: keep the bold lead and the full text separately.
    lim_md = s["Key limitations"]
    raw = re.split(r"\n(?=\d+\. )", "\n" + lim_md)
    limitations = []
    for block in raw:
        block = block.strip()
        if not block:
            continue
        first, *rest = block.splitlines()
        first = re.sub(r"^\d+\.\s+", "", first)
        lead, body = split_bold_lead(first)
        subs = [inline(re.sub(r"^\s*-\s+", "", r)) for r in rest if r.strip()]
        limitations.append({"lead": lead, "body": body, "sub": subs})

    # Verdict section of feasibility.md (numbered conditions + fallback).
    f2 = sections(feas, 2)
    verdict_md = find_section(f2, "4. Verdict")
    conds = []
    for m in re.finditer(r"^\d+\. \*\*(.+?)\*\* (.+)$", verdict_md, re.M):
        conds.append({"lead": inline(m.group(1)), "body": inline(m.group(2))})
    fallback = re.search(r"\*\*Fallback.+", verdict_md).group(0)

    gate = find_section(f2, "3. Feasibility gate")
    gate_q = []
    for m in re.finditer(r"^\*\*(Q\d\. .+?)\*\*\n(?:\*\*(.+?)\*\*)?", gate, re.M):
        gate_q.append({"q": inline(m.group(1)), "a": inline(m.group(2) or "")})

    return {
        "verdict": verdict[0],
        "verdict_context": inline(verdict[1]),
        "prepared_note": inline(feas.splitlines()[2]),
        "limitations": limitations,
        "verdict_conditions": conds,
        "fallback": inline(fallback),
        "frame": list_items(s["Recommended frame (Phase 2 to confirm)"]),
        "corrections": list_items(s["Corrections to the first (offline) pass"]),
        "unverified": list_items(s["Still UNVERIFIED"]),
        "files": list_items(s["Files"]),
        "gate": gate_q,
        "overlap": inline(re.search(r"\*\*The overlap of all four stages.+?\*\*", gate).group(0)),
        "link_table": table_after(feas, "| Size | MV-linked"),
        "coverage_table": table_after(feas, "| Stage | Coverage"),
        "multiplex_table": table_after(feas, "| Year | 2019"),
        "completion_table": table_after(feas, "| Measure | Field / source"),
        "links": {
            "summary": gh_url("phase1", "phase1/summary.md"),
            "feasibility": gh_url("phase1", "phase1/feasibility.md"),
            "inventory": gh_url("phase1", "phase1/inventory.csv"),
            "scripts": f"https://github.com/{REPO}/tree/{SOURCES['phase1']['sha']}/phase1/scripts",
        },
    }


def publisher_org(p):
    """Organisation part of the free-text publisher field, for the filter only.

    'City of Toronto - City Planning' -> 'City of Toronto'; the abbreviation 'CMHC' is folded into
    its full name. The full publisher text is still shown on every row.
    """
    org = re.split(r" - |\s*\(|;", p)[0].strip()
    return {"CMHC": "Canada Mortgage and Housing Corporation"}.get(org, org)


def provenance_group(p):
    return "Opened and verified" if p.startswith("opened and verified") else "Not fully verified"


def build_inventory():
    rows = list(csv.DictReader(io.StringIO(git_show("phase1", "phase1/inventory.csv"))))
    for r in rows:
        r["publisher_org"] = publisher_org(r["publisher"])
        r["provenance_group"] = provenance_group(r["provenance"])
    return rows


# ---------------------------------------------------------------- Phase 2 + ideas

def build_phase2():
    readme = git_show("phase2", "phase2/README.md")
    audit = git_show("phase2", "phase2/AUDIT_LOG.md")
    s = sections(readme, 2)
    intro = readme.split("\n## ")[0].split("\n", 1)[1].strip()
    a = sections(audit, 2)
    audit1 = a["Audit 1: code review against failure modes"]
    return {
        "intro": inline(" ".join(intro.split())),
        "modules": table_after(readme, "| Module | Purpose"),
        "design": list_items(s["Design decisions that matter"]),
        "assumptions": inline(" ".join(s["Assumptions to replace with evidence (`pipeline/config.py`)"].split())),
        "limitations": list_items(s["Known limitations"]),
        "next_steps": list_items(s["Next steps (need real data)"]),
        "audit_fixed": list_items(audit1.split("Fixed:", 1)[1]),
        "audit_checks": list_items(a["Audit 2: empirical checks"].split("\n\nNot covered:")[0]),
        "audit_not_covered": inline(" ".join(re.search(r"Not covered:.+", audit, re.S).group(0).split())),
        "links": {
            "readme": gh_url("phase2", "phase2/README.md"),
            "audit": gh_url("phase2", "phase2/AUDIT_LOG.md"),
            "config": gh_url("phase2", "phase2/pipeline/config.py"),
            "code": f"https://github.com/{REPO}/tree/{SOURCES['phase2']['sha']}/phase2/pipeline",
        },
    }


def build_ideas():
    readme = git_show("phase2", "README.md")
    s2 = sections(readme, 2)
    ideas_md = s2["Ideas to try next"]
    caveat = " ".join(ideas_md.split("\n\n")[0].split())
    s3 = sections(ideas_md, 3)
    first = table_after(s3["Good first projects (open data, quick to start)"], "| Idea")
    groups = [{"key": "first", "title": "Good first projects", "note": "Open data, quick to start",
               "items": [{"name": r[0].replace("<strong>", "").replace("</strong>", ""),
                          "question": r[1], "data": r[2]} for r in first["rows"]]}]
    for key, title in [("more", "More ideas"), ("housing", "Housing and transit follow-ups")]:
        items = []
        for it in list_items(s3[title]):
            m = re.match(r"<strong>(.+?):?</strong>:?\s*(.*)", it["html"])
            items.append({"name": m.group(1).rstrip(":"), "question": m.group(2), "data": ""})
        groups.append({"key": key, "title": title, "note": "", "items": items})
    return {"caveat": inline(caveat), "groups": groups, "link": gh_url("phase2", "README.md")}


# ---------------------------------------------------------------- Hamilton

def build_hamilton():
    base = "hamilton/parcel_zoning/"
    summary = json.loads(git_show("hamilton", base + "output/summary.json"))
    validation = json.loads(git_show("hamilton", base + "output/validation.json"))
    validation.pop("mismatches", None)
    return {
        "summary": summary,
        "validation": validation,
        "links": {
            "summary": gh_url("hamilton", base + "output/summary.json"),
            "validation": gh_url("hamilton", base + "output/validation.json"),
            "readme": gh_url("hamilton", base + "README.md"),
            "build": gh_url("hamilton", base + "scripts/build_parcel_zoning.py"),
            "validate": gh_url("hamilton", base + "scripts/validate.py"),
            "map": f"https://github.com/{REPO}/tree/{SOURCES['hamilton']['sha']}/{base}site",
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--latest", action="store_true",
                    help="read origin/<branch> tips instead of the pinned commits")
    args = ap.parse_args()
    if args.latest:
        for src in SOURCES.values():
            src["sha"] = subprocess.run(["git", "rev-parse", f"origin/{src['branch']}"], check=True,
                                        capture_output=True, text=True).stdout.strip()

    data = {
        "snapshot": {
            "date": SNAPSHOT_DATE,
            "repo": f"https://github.com/{REPO}",
            "sources": {k: {**v, "tree": f"https://github.com/{REPO}/tree/{v['sha']}",
                            "branch_url": f"https://github.com/{REPO}/tree/{v['branch']}"}
                        for k, v in SOURCES.items()},
        },
        "phase1": build_phase1(),
        "inventory": build_inventory(),
        "phase2": build_phase2(),
        "ideas": build_ideas(),
        "hamilton": build_hamilton(),
    }
    text = json.dumps(data, indent=1, ensure_ascii=False)
    (DOCS / "data").mkdir(exist_ok=True)
    (DOCS / "data" / "site-data.json").write_text(text + "\n", encoding="utf-8")
    (DOCS / "data" / "site-data.js").write_text(
        "// Generated by docs/build_data.py. Do not edit by hand.\nwindow.SITE_DATA = " + text + ";\n",
        encoding="utf-8")
    print(f"wrote docs/data/site-data.json and .js ({len(text):,} bytes); "
          f"{len(data['inventory'])} sources, {len(data['phase1']['limitations'])} limitations")


if __name__ == "__main__":
    main()
