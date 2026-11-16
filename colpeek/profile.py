"""The profiler: turn rows into per-column stats.

One pass, streaming-friendly. Memory stays bounded no matter how big the
file is: unique values are tracked only up to MAX_TRACKED_UNIQUE per
column, and the "top values" counter is capped the same way. Past the cap
the unique count is reported as a lower bound ("10000+") instead of a lie.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .infer import infer_type, sort_key_for_min_max

# Past this many distinct values in one column, stop tracking new ones.
# 10k is plenty for a "peek" — and it keeps a 10-million-row file from
# eating all your RAM just to count uniques.
MAX_TRACKED_UNIQUE = 10_000


@dataclass
class ColumnProfile:
    """Everything colpeek knows about one column."""

    name: str
    type: str = "unknown"
    rows: int = 0
    missing: int = 0
    unique: int = 0
    unique_capped: bool = False
    minimum: str | None = None
    maximum: str | None = None
    top_values: list[tuple[str, int]] = field(default_factory=list)

    @property
    def missing_pct(self) -> float:
        if self.rows == 0:
            return 0.0
        return round(self.missing / self.rows * 100, 1)

    def to_dict(self) -> dict:
        return {
            "column": self.name,
            "type": self.type,
            "rows": self.rows,
            "missing": self.missing,
            "missing_pct": self.missing_pct,
            "unique": self.unique,
            "unique_capped": self.unique_capped,
            "min": self.minimum,
            "max": self.maximum,
            "top_values": [
                {"value": value, "count": count}
                for value, count in self.top_values
            ],
        }


@dataclass
class Profile:
    """The whole-file result: one ColumnProfile per column."""

    columns: list[ColumnProfile]
    rows: int
    rows_truncated: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "rows_truncated": self.rows_truncated,
            "columns": [c.to_dict() for c in self.columns],
            "warnings": self.warnings,
        }


def profile_columns(
    headers: list[str],
    rows: list[list[str]],
    rows_seen: int,
    top_n: int = 5,
    missing_values: set[str] | None = None,
) -> Profile:
    """Build a Profile from headers and already-read rows.

    `missing_values` is the set of strings that count as missing on top of
    an empty cell (e.g. {"NA", "N/A"}). Matching is exact after stripping
    whitespace — I do not want "Nana" to become missing because it contains
    "NA".
    """
    na = {v.strip() for v in (missing_values or set())}
    na.discard("")

    columns: list[ColumnProfile] = []
    for idx, name in enumerate(headers):
        values = [row[idx] for row in rows]
        present = [
            v for v in values if v.strip() != "" and v.strip() not in na
        ]

        col = ColumnProfile(name=name, rows=len(rows))
        col.missing = len(rows) - len(present)
        col.type = infer_type(present)

        seen: set[str] = set()
        counts: Counter[str] = Counter()
        capped = False
        for v in present:
            counts[v] += 1
            if len(seen) < MAX_TRACKED_UNIQUE:
                seen.add(v)
            elif v not in seen:
                capped = True
        col.unique = len(seen)
        col.unique_capped = capped
        col.top_values = counts.most_common(top_n)

        if present and col.type in ("integer", "number", "date"):
            ordered = sorted(present, key=lambda v: sort_key_for_min_max(v, col.type))  # type: ignore[arg-type]
            col.minimum = ordered[0]
            col.maximum = ordered[-1]

        columns.append(col)

    warnings: list[str] = []
    truncated = rows_seen > len(rows)
    if truncated:
        warnings.append(
            f"Only the first {len(rows)} of {rows_seen} rows were profiled (--limit)."
        )

    return Profile(columns=columns, rows=len(rows), rows_truncated=truncated, warnings=warnings)
