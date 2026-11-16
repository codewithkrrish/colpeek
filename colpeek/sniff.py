"""Reading the file: delimiter sniffing, headers, ragged rows.

Kept separate from profiling because "what does this file look like" and
"what do the columns contain" are different questions, and mixing them
makes both harder to test.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .errors import ColpeekError

# How much of the file to read when guessing the delimiter.
SNIFF_BYTES = 8192

# Delimiters csv.Sniffer is allowed to guess. Tabs and semicolons cover
# most exports; pipes show up in logs. I do not let it guess spaces —
# it gets that wrong constantly.
SNIFF_DELIMITERS = ",\t;|"


def detect_delimiter(sample: str, hint: str | None) -> str:
    """Pick a delimiter: explicit hint wins, else sniff, else comma."""
    if hint:
        return hint
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=SNIFF_DELIMITERS)
        return dialect.delimiter
    except csv.Error:
        return ","


def open_text(path: Path):
    """Open a CSV-ish file as text, tolerating a BOM and odd encodings.

    Tries UTF-8 (with BOM stripped) first; if the file is not valid UTF-8,
    falls back to latin-1 rather than dying — latin-1 never fails to decode,
    and a peek at the data beats no data. The fallback is reported to the
    caller through the returned flag.
    """
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
        # Actually decode a chunk now so a bad encoding fails here, where
        # we can fall back cleanly, instead of mid-read in the caller.
        handle.read(SNIFF_BYTES)
        handle.seek(0)
        return handle, "utf-8"
    except UnicodeDecodeError:
        handle.close()
        return path.open("r", encoding="latin-1", newline=""), "latin-1"


def read_rows(
    path: Path,
    delimiter: str | None = None,
    has_header: bool = True,
    limit: int | None = None,
) -> tuple[list[str], list[list[str]], list[str], int]:
    """Read a delimited file into rows.

    Returns (headers, rows, warnings, rows_seen). Rows are lists of raw
    strings; short rows are padded with "" and long rows are truncated,
    with a warning either way instead of a crash. `rows_seen` counts every
    data row in the file even when `limit` stops the read early.
    """
    if not path.exists():
        raise ColpeekError(f"No such file: {path}")
    if path.is_dir():
        raise ColpeekError(f"Expected a file, got a directory: {path}")

    handle, encoding = open_text(path)
    warnings: list[str] = []
    if encoding == "latin-1":
        warnings.append("File is not valid UTF-8; read as latin-1 instead.")

    with handle:
        sample = handle.read(SNIFF_BYTES)
        if not sample.strip():
            raise ColpeekError(f"File is empty: {path}")
        handle.seek(0)
        delim = detect_delimiter(sample, delimiter)
        reader = csv.reader(handle, delimiter=delim)

        try:
            first = next(reader)
        except StopIteration:
            raise ColpeekError(f"File is empty: {path}")

        if has_header:
            headers = [h.strip() or f"col_{i + 1}" for i, h in enumerate(first)]
            if len(set(headers)) != len(headers):
                warnings.append("Duplicate column names found in the header.")
        else:
            headers = [f"col_{i + 1}" for i in range(len(first))]
            rows = [first]
            rows_seen = 1
            return _finish(headers, rows, rows_seen, reader, limit, warnings)

        return _finish(headers, [], 0, reader, limit, warnings)


def _finish(
    headers: list[str],
    rows: list[list[str]],
    rows_seen: int,
    reader,
    limit: int | None,
    warnings: list[str],
) -> tuple[list[str], list[list[str]], list[str], int]:
    width = len(headers)
    short_rows = 0
    long_rows = 0
    for raw in reader:
        rows_seen += 1
        if limit is not None and len(rows) >= limit:
            continue
        if len(raw) < width:
            short_rows += 1
            raw = raw + [""] * (width - len(raw))
        elif len(raw) > width:
            long_rows += 1
            raw = raw[:width]
        rows.append(raw)

    if short_rows:
        warnings.append(
            f"{short_rows} row(s) were shorter than the header and were padded with empty values."
        )
    if long_rows:
        warnings.append(
            f"{long_rows} row(s) had extra fields that were ignored."
        )
    return headers, rows, warnings, rows_seen
