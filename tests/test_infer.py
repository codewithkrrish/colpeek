"""Tests for type inference — the part most likely to guess wrong."""

from colpeek.infer import infer_type


def test_integers():
    assert infer_type(["1", "42", "-7", "0"]) == "integer"


def test_floats_are_number_not_integer():
    assert infer_type(["1.5", "2", "3.25"]) == "number"


def test_booleans_need_a_word():
    # true/false/yes/no spell it out; bare 0/1 are integers, not booleans.
    assert infer_type(["true", "false", "TRUE"]) == "boolean"
    assert infer_type(["yes", "no", "true"]) == "boolean"
    assert infer_type(["0", "1", "1"]) == "integer"


def test_dates_iso_and_day_first():
    assert infer_type(["2023-01-15", "2022-06-01"]) == "date"
    assert infer_type(["15-01-2023", "01-06-2022"]) == "date"


def test_text_and_mixed():
    assert infer_type(["Mumbai", "Delhi", "Pune"]) == "text"
    # One value refuses to fit: the whole column is mixed, not a number
    # with an asterisk.
    assert infer_type(["42", "N/A", "7"]) == "mixed"


def test_empty_values_are_ignored_not_typed():
    assert infer_type(["", "  ", ""]) == "unknown"
    assert infer_type(["5", "", "9"]) == "integer"


def test_single_value_text():
    assert infer_type(["hello"]) == "text"
