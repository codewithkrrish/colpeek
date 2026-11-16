"""Type inference for one column at a time.

The idea is simple: look at the values, try the strictest type first, and
only loosen when a value refuses to fit. A column is an integer column only
if every non-empty value parses as an int — one stray "N/A" and it is text,
not a number with an asterisk.

Dates are the one place I guess a little: I try a short list of formats
people actually write (ISO first, then the common day-first and US ones).
Anything else is text, and that is fine — a wrong guess here is worse than
no guess.
"""

from __future__ import annotations

from datetime import datetime

# Formats I will accept as a date. Deliberately short: if your dates look
# like "March 4th, 2024" this will call the column text, and that is honest.
DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
)

# A boolean column of 0/1 clashes with integer, so integers win: if every
# value is 0 or 1, that is an integer column, not a boolean one. Bool is
# only reported when at least one value spells it out (true/false/yes/no).
BOOLEAN_WORDS = {"true", "false", "yes", "no", "y", "n"}


def _looks_like_int(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


def _looks_like_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _parse_date(value: str) -> datetime | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _specific_type(value: str) -> str | None:
    """The strictest non-text type one value fits, or None for plain text."""
    if _looks_like_int(value):
        return "integer"
    if _looks_like_float(value):
        return "number"
    if value.lower() in BOOLEAN_WORDS:
        return "boolean"
    if _parse_date(value) is not None:
        return "date"
    return None


def infer_type(values: list[str]) -> str:
    """Infer the type of a column from its non-empty values.

    Returns one of: "integer", "number", "boolean", "date", "text",
    "mixed" (values fit different types), or "unknown" (no values at all).
    """
    seen = [v.strip() for v in values if v.strip() != ""]
    if not seen:
        return "unknown"

    specific = [_specific_type(v) for v in seen]
    fitted = {t for t in specific if t is not None}
    if not fitted:
        # Nothing fits any specific type: plain text.
        return "text"
    if any(t is None for t in specific):
        # Some values fit a type and others are plain text: mixed.
        return "mixed"
    if fitted <= {"integer", "number"}:
        # A mix of ints and floats is still just a number column.
        return "integer" if fitted == {"integer"} else "number"
    if len(fitted) == 1:
        return fitted.pop()
    # Values fit different specific types: mixed, and saying so beats guessing.
    return "mixed"


def sort_key_for_min_max(value: str, col_type: str) -> object:
    """A key that lets min/max work per inferred type."""
    if col_type == "integer":
        return int(value)
    if col_type == "number":
        return float(value)
    if col_type == "date":
        parsed = _parse_date(value)
        return parsed if parsed is not None else value
    return value
