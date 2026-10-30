import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pdftext import lines_from_words  # noqa: E402


def w(x0, y, text, width=30):
    return (x0, y, x0 + width, text)


def test_words_on_one_row_are_ordered_and_column_gaps_become_two_spaces():
    out = lines_from_words([w(100, 10, "68"), w(12, 10, "Toronto", 24), w(40, 10, "W02", 20)])
    assert out == ["Toronto W02  68"]


def test_rows_split_by_vertical_position():
    out = lines_from_words([w(10, 10, "a"), w(10, 25, "b")])
    assert out == ["a", "b"]


def test_stale_overlay_of_previous_row_is_dropped():
    # row 2 also carries row 1's values (same positions); only the new values must survive
    row1 = [w(12, 10, "Toronto", 24), w(40, 10, "W02", 20), w(100, 10, "68")]
    row2 = [w(40, 22, "W02", 20), w(100, 22, "68"), w(12, 22, "Toronto", 24),
            w(40, 22, "W03", 20), w(100, 22, "45")]
    assert lines_from_words(row1 + row2) == ["Toronto W02  68", "Toronto W03  45"]


def test_legitimately_repeated_values_are_kept():
    # two rows with identical values and no overlay conflict: nothing may be dropped
    rows = [w(100, 10, "100%"), w(10, 10, "x"), w(100, 22, "100%"), w(10, 22, "y")]
    assert lines_from_words(rows) == ["x  100%", "y  100%"]


def test_placeholder_ghost_words_are_ignored():
    out = lines_from_words([w(12, 10, "Toronto", 24), w(40, 10, "C02", 20), w(100, 10, "39"),
                            w(140, 10, "Abc"), w(180, 10, "312")])
    assert out == ["Toronto C02  39  312"]


def test_row_value_equal_to_its_stale_copy_is_kept_once():
    # the new row's sales equals the previous row's sales: both words overlap and are identical
    row1 = [w(12, 10, "Toronto", 24), w(40, 10, "E08", 20), w(100, 10, "75")]
    row2 = [w(12, 22, "Toronto", 24), w(40, 22, "E08", 20), w(40, 22, "E09", 20),
            w(100, 22, "75"), w(100, 22, "75")]
    assert lines_from_words(row1 + row2) == ["Toronto E08  75", "Toronto E09  75"]
