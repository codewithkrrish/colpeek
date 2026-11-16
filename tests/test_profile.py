"""Tests for the profiler: counts, uniques, min/max, top values."""

from colpeek.profile import profile_columns


def _profile(headers, rows, **kwargs):
    return profile_columns(headers, rows, rows_seen=len(rows), **kwargs)


def test_happy_path_counts():
    profile = _profile(
        ["name", "age", "city"],
        [
            ["Asha", "28", "Mumbai"],
            ["Rohan", "34", "Delhi"],
            ["Meera", "", "Mumbai"],
        ],
    )
    by_name = {c.name: c for c in profile.columns}
    assert by_name["age"].type == "integer"
    assert by_name["age"].missing == 1
    assert by_name["age"].missing_pct == 33.3
    assert by_name["age"].minimum == "28"
    assert by_name["age"].maximum == "34"
    assert by_name["city"].type == "text"
    assert by_name["city"].unique == 2
    assert by_name["city"].top_values[0] == ("Mumbai", 2)


def test_empty_column_is_unknown():
    profile = _profile(["a", "b"], [["", "x"], ["", "y"]])
    col = profile.columns[0]
    assert col.type == "unknown"
    assert col.missing == 2
    assert col.unique == 0
    assert col.minimum is None


def test_custom_missing_values():
    profile = _profile(
        ["score"],
        [["42"], ["NA"], ["N/A"], ["7"]],
        missing_values={"NA", "N/A"},
    )
    col = profile.columns[0]
    assert col.type == "integer"
    assert col.missing == 2
    assert col.unique == 2


def test_na_matching_is_exact():
    # "Nana" contains "NA" but is a real value, not a missing marker.
    profile = _profile(
        ["name"], [["Nana"], ["NA"]], missing_values={"NA"}
    )
    col = profile.columns[0]
    assert col.missing == 1
    assert col.unique == 1


def test_top_values_respects_top_n():
    profile = _profile(
        ["city"],
        [["A"], ["B"], ["A"], ["C"], ["A"], ["B"]],
        top_n=2,
    )
    assert profile.columns[0].top_values == [("A", 3), ("B", 2)]


def test_float_min_max_is_numeric_not_lexical():
    # Lexically "9" > "10"; numerically it is not. This is the bug a
    # naive string sort would ship.
    profile = _profile(["v"], [["9"], ["10"], ["100"]])
    col = profile.columns[0]
    assert col.type == "integer"
    assert col.minimum == "9"
    assert col.maximum == "100"


def test_unique_cap_reports_lower_bound():
    rows = [[str(i)] for i in range(10_005)]
    profile = _profile(["id"], rows)
    col = profile.columns[0]
    assert col.unique_capped is True
    assert col.unique == 10_000


def test_to_dict_shape():
    profile = _profile(["a"], [["1"], ["2"]])
    data = profile.to_dict()
    assert data["rows"] == 2
    assert data["columns"][0]["column"] == "a"
    assert data["columns"][0]["top_values"][0]["value"] == "1"
