"""Command-line entry point. Thin on purpose: parse flags, call the real
work in sniff/profile/render, and turn ColpeekError into a clean message.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import __version__
from .errors import ColpeekError
from .profile import profile_columns
from .render import render_json, render_table
from .sniff import read_rows

EXIT_OK = 0
EXIT_FILE_ERROR = 1
# argparse already exits 2 on bad flags; I keep that convention.


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="colpeek",
        description="Peek inside a CSV or TSV: one line of stats per column.",
    )
    parser.add_argument("file", help="CSV or TSV file to profile")
    parser.add_argument(
        "--columns",
        metavar="NAMES",
        help="only profile these columns (comma-separated names)",
    )
    parser.add_argument(
        "--delimiter",
        metavar="CHAR",
        help="field delimiter (default: auto-detected)",
    )
    parser.add_argument(
        "--tsv", action="store_true", help="shorthand for --delimiter $'\\t'"
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="treat the first row as data, name columns col_1, col_2, ...",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        default=None,
        help="profile only the first N data rows",
    )
    parser.add_argument(
        "--top",
        type=int,
        metavar="N",
        default=5,
        help="how many top values to show per column (default: 5)",
    )
    parser.add_argument(
        "--na-values",
        metavar="VALUES",
        default="",
        help="extra strings that count as missing, comma-separated (e.g. NA,N/A)",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the profile as JSON"
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="write the report to FILE instead of stdout",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite --output file if it already exists",
    )
    parser.add_argument(
        "--version", action="version", version=f"colpeek {__version__}"
    )
    return parser


def _validate(args: argparse.Namespace) -> None:
    if args.limit is not None and args.limit < 1:
        raise ColpeekError("--limit must be at least 1", exit_code=2)
    if args.top < 0:
        raise ColpeekError("--top cannot be negative", exit_code=2)
    if args.delimiter is not None and len(args.delimiter) != 1:
        raise ColpeekError("--delimiter must be a single character", exit_code=2)
    if args.tsv and args.delimiter:
        raise ColpeekError("use --tsv or --delimiter, not both", exit_code=2)


def _write_output(path: Path, text: str, force: bool) -> None:
    """Write atomically (temp file + rename) and never clobber silently."""
    if path.exists() and not force:
        raise ColpeekError(
            f"Refusing to overwrite existing file: {path} (use --force)"
        )
    # Same directory as the target, so the rename stays on one filesystem.
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, prefix=path.name + ".", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    try:
        tmp_path.replace(path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _validate(args)
        delimiter = "\t" if args.tsv else args.delimiter
        headers, rows, warnings, rows_seen = read_rows(
            Path(args.file),
            delimiter=delimiter,
            has_header=not args.no_header,
            limit=args.limit,
        )

        wanted = None
        if args.columns:
            wanted = [c.strip() for c in args.columns.split(",") if c.strip()]
            unknown = [c for c in wanted if c not in headers]
            if unknown:
                raise ColpeekError(
                    f"Unknown column(s): {', '.join(unknown)} "
                    f"(file has: {', '.join(headers)})"
                )
            keep = [headers.index(c) for c in wanted]
            headers = wanted
            rows = [[row[i] for i in keep] for row in rows]

        na_values = (
            {v.strip() for v in args.na_values.split(",") if v.strip()}
            if args.na_values
            else set()
        )
        profile = profile_columns(
            headers, rows, rows_seen, top_n=args.top, missing_values=na_values
        )
        profile.warnings = warnings + profile.warnings

        text = render_json(profile) if args.json else render_table(profile)
        if args.output:
            _write_output(Path(args.output), text, args.force)
        else:
            sys.stdout.write(text)
        return EXIT_OK
    except ColpeekError as exc:
        print(f"colpeek: {exc.message}", file=sys.stderr)
        return exc.exit_code


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
