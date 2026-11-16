"""Output: a plain ASCII table for humans, JSON for scripts.

No dependencies, no colour codes — the table has to survive being piped
into a file or pasted into a chat. Long values are truncated with an
ellipsis rather than blowing the table out.
"""

from __future__ import annotations

import json

from .profile import Profile

# Longest a single cell value may be in the table before it gets cut.
MAX_CELL_LEN = 40


def _truncate(value: str) -> str:
    if len(value) > MAX_CELL_LEN:
        return value[: MAX_CELL_LEN - 1] + "…"
    return value


def render_table(profile: Profile) -> str:
    """Render the profile as a plain-text table."""
    headers = ["column", "type", "missing", "unique", "min", "max", "top values"]
    rows: list[list[str]] = []
    for col in profile.columns:
        unique = f"{col.unique}+" if col.unique_capped else str(col.unique)
        top = ", ".join(
            f"{_truncate(v)} ({c})" for v, c in col.top_values
        )
        rows.append(
            [
                col.name,
                col.type,
                f"{col.missing} ({col.missing_pct}%)",
                unique,
                _truncate(col.minimum) if col.minimum is not None else "—",
                _truncate(col.maximum) if col.maximum is not None else "—",
                top or "—",
            ]
        )

    widths = [
        max(len(h), max((len(r[i]) for r in rows), default=0))
        for i, h in enumerate(headers)
    ]

    def fmt(cells: list[str]) -> str:
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    lines = [
        f"{profile.rows} rows",
        "",
        fmt(headers),
        fmt(["-" * w for w in widths]),
    ]
    lines.extend(fmt(r) for r in rows)
    if profile.warnings:
        lines.append("")
        lines.extend(f"note: {w}" for w in profile.warnings)
    return "\n".join(lines) + "\n"


def render_json(profile: Profile) -> str:
    """Render the profile as indented JSON."""
    return json.dumps(profile.to_dict(), indent=2) + "\n"
