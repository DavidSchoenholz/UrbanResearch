"""Parser tests on invented fixture text (layout mimics pdftotext -layout; numbers are made up)."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build  # noqa: E402
import community  # noqa: E402
import fetch  # noqa: E402
import marketwatch  # noqa: E402

MW = """
 All TRREB Areas           1,000      $1,000,000,000    $1,000,000       $900,000        3,000        40.0%          5,000              4.0             99%          30           45
 City of Toronto             100        $100,000,000    $1,000,000       $900,000          300        40.0%            500              4.0             99%          30           45
 Toronto West                 40         $30,000,000      $750,000       $700,000          100        40.0%            200              4.0             99%          30           45
 Toronto W01                  10         $10,000,000    $1,000,000       $900,000           30        40.0%             60              4.0             99%          30           45
 Toronto W02                  30         $20,000,000      $666,667       $650,000           70        40.0%            140              4.0             99%          30           45
 Toronto Central              60         $70,000,000    $1,166,667     $1,000,000          200        40.0%            300              4.0             99%          30           45
 Toronto C01                  60         $70,000,000    $1,166,667     $1,000,000          200        40.0%            300              4.0             99%          30           45
 All TRREB Areas          11,000     $11,000,000,000    $1,000,000       $900,000       33,000        40.0%         55,000              4.0             99%          30           45
 Toronto W01                 100        $100,000,000    $1,000,000       $900,000          300        40.0%            600              4.0             99%          30           45
"""

COMM = """
Toronto Regional Real Estate Board          Toronto C02 Community Breakdown
SUMMARY OF EXISTING HOME TRANSACTIONS       All Home Types 2026 Q2
Community          Sales   Dollar Volume   Average Price   Median Price   New Listings   Active Listings   Avg. SP/LP   Avg. DOM
Annex                100   $100,000,000    $1,000,000      $900,000       200            100               98%          30
Casa Loma             50    $50,000,000    $1,000,000      $950,000       100             50               99%          20
The Islands            0             0              0
Rustic                 2             5              3
The source of all slides is the Toronto Regional Real Estate Board.
Toronto Regional Real Estate Board          Toronto C03 Community Breakdown
SUMMARY OF EXISTING HOME TRANSACTIONS       All Home Types 2026 Q2
Community          Sales   Dollar Volume   Average Price   Median Price   New Listings   Active Listings   Avg. SP/LP   Avg. DOM
Lawrence Park South   20    $20,000,000    $1,000,000      $900,000       40              20               98%          30
"""


def test_marketwatch_takes_first_district_set_and_adds_city():
    df, problems = marketwatch.parse_text(MW, "2026-09")
    assert problems == []
    assert sorted(df["district"]) == ["C01", "CITY", "W01", "W02"]      # stops at the repeated W01
    assert df.loc[df["district"] == "W01", "sales"].iloc[0] == 10
    assert df.loc[df["district"] == "CITY", "sales"].iloc[0] == 100


def test_marketwatch_flags_district_sum_mismatch_and_bad_columns():
    bad_sum = MW.replace("Toronto C01                  60", "Toronto C01                  61")
    assert any("City of Toronto" in p for p in marketwatch.parse_text(bad_sum, "x")[1])
    bad_cols = MW.replace(" Toronto C01                  60         $70,000,000    $1,166,667",
                          " Toronto C01                  60         $70,000,000    $9,999,999")
    assert bad_cols != MW
    assert any("checksum" in p for p in marketwatch.parse_text(bad_cols, "x")[1])
    assert marketwatch.parse_text("nothing here", "x")[1] == ["no Toronto district rows"]


def test_marketwatch_zero_sales_means_no_price_not_zero_dollars():
    text = MW.replace("Toronto W02                  30         $20,000,000      $666,667       $650,000",
                      "Toronto W02                   0                  $0              $0             $0")
    text = text.replace("Toronto W01                  10", "Toronto W01                  10").replace(
        "Toronto West                 40         $30,000,000", "Toronto West                 10         $10,000,000").replace(
        "City of Toronto             100        $100,000,000", "City of Toronto              70         $80,000,000")
    df, _ = marketwatch.parse_text(text, "x")
    w02 = df[df["district"] == "W02"].iloc[0]
    assert w02["sales"] == 0 and w02[["avg_price", "median_price", "dollar_volume"]].isna().all()


def test_period_of():
    assert marketwatch.period_of("mw2609") == "2026-09"
    assert marketwatch.period_of("mw1107") == "2011-07"
    assert marketwatch.period_of("mw9802") == "1998-02"      # 1990s, not 2098


def test_community_rows_districts_and_suppressed_values():
    df, problems = community.parse_text(COMM)
    assert problems == []
    assert set(df["district"]) == {"C02", "C03"}
    assert set(df["period"]) == {"2026Q2"}
    islands = df[df["community"] == "The Islands"].iloc[0]
    assert islands["sales"] == 0
    assert islands[["dollar_volume", "avg_price", "median_price"]].isna().all()   # not $0
    assert df.loc[df["community"] == "Annex", "avg_price"].iloc[0] == 1_000_000


def test_community_checksum_catches_misaligned_columns():
    bad = COMM.replace("$100,000,000    $1,000,000", "$100,000,000    $5,000,000")
    assert any("checksum" in p for p in community.parse_text(bad)[1])


def test_name_normalisation_matches_punctuation_variants():
    assert build.norm("Yonge-St. Clair") == build.norm("Yonge-St.Clair")
    assert build.norm("Cabbagetown-South St. James Town") == "cabbagetown south st james town"


def test_matching_is_exact_only_and_flags_ambiguity():
    import pandas as pd
    nbhd = pd.DataFrame({"AREA_SHORT_CODE": ["001", "002", "003"],
                         "AREA_NAME": ["Annex", "Casa Loma", "Casa-Loma"]})
    comm = pd.DataFrame({"district": ["C02"] * 3, "community": ["Annex", "Casa Loma", "Waterfront Communities C1"]})
    m = build.match_communities(comm, nbhd).set_index("community")
    assert m.loc["Annex", "status"] == "matched" and m.loc["Annex", "area_code"] == "001"
    assert m.loc["Casa Loma", "status"] == "ambiguous"           # two neighbourhoods normalise the same
    assert m.loc["Waterfront Communities C1", "status"] == "unmapped"

    # two communities claiming one neighbourhood: use neither
    comm2 = pd.DataFrame({"district": ["C02", "C03"], "community": ["Annex", "ANNEX"]})
    assert set(build.match_communities(comm2, nbhd)["status"]) == {"ambiguous"}


def test_archive_and_community_path_filters():
    html = ('<a href="/wp-content/files/market-stats/market-watch/mw9802.pdf">'
            '<a href="/wp-content/files/market-stats/market-watch/mw0001.pdf">'
            '<a href="/wp-content/files/market-stats/market-watch/mw1107.pdf">'
            '<a href="/wp-content/files/market-stats/market-watch/mw2609.pdf">'
            '<a href="/wp-content/files/market-stats/community-reports/2026/Q2/TorontoCentralQ22026.pdf">'
            '<a href="/wp-content/files/market-stats/community-reports/2026/Q2/AjaxQ22026.pdf">')
    assert [p[-10:-4] for p in fetch.marketwatch_paths(html)] == ["mw1107", "mw2609"]
    assert [p[-10:-4] for p in fetch.marketwatch_paths(html, since="0001")] == ["mw0001", "mw1107", "mw2609"]
    assert any("mw9802" in p for p in fetch.marketwatch_paths(html, since="9801"))   # 1990s kept when asked for
    assert len(fetch.community_paths(html)) == 1


def test_render_escapes_script_close(tmp_path):
    payload = {"x": "</script><b>"}
    build.render(payload, tmp_path / "o.html")
    out = (tmp_path / "o.html").read_text()
    assert "</script><b>" not in out and "<\\/script>" in out


def test_suppressed_rows_keep_only_sales_never_listing_counts_as_prices():
    df, problems = community.parse_text(COMM)
    assert problems == []
    rustic = df[df["community"] == "Rustic"].iloc[0]
    assert rustic["sales"] == 2
    assert rustic[["dollar_volume", "avg_price", "median_price", "new_listings"]].isna().all()
