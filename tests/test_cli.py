"""End-to-end CLI tests: real files, real exit codes, real output."""

import json
import subprocess
import sys

from colpeek.cli import run

SAMPLE = "name,age,city\nAsha,28,Mumbai\nRohan,34,Delhi\nMeera,,Mumbai\n"


def _write(tmp_path, name, content, encoding="utf-8"):
    path = tmp_path / name
    path.write_text(content, encoding=encoding)
    return path


def test_table_output_happy_path(tmp_path, capsys):
    path = _write(tmp_path, "a.csv", SAMPLE)
    assert run([str(path)]) == 0
    out = capsys.readouterr().out
    assert "3 rows" in out
    assert "age" in out and "integer" in out
    assert "Mumbai (2)" in out
    assert "1 (33.3%)" in out  # one missing age out of three


def test_json_output_is_parseable(tmp_path, capsys):
    path = _write(tmp_path, "a.csv", SAMPLE)
    assert run([str(path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["rows"] == 3
    age = next(c for c in data["columns"] if c["column"] == "age")
    assert age["type"] == "integer"
    assert age["missing"] == 1


def test_missing_file_is_a_clean_error_not_a_traceback(tmp_path, capsys):
    assert run([str(tmp_path / "nope.csv")]) == 1
    err = capsys.readouterr().err
    assert "No such file" in err
    assert "Traceback" not in err


def test_empty_file(tmp_path, capsys):
    path = _write(tmp_path, "empty.csv", "")
    assert run([str(path)]) == 1
    assert "empty" in capsys.readouterr().err


def test_header_only_file(tmp_path, capsys):
    path = _write(tmp_path, "headers.csv", "a,b,c\n")
    assert run([str(path)]) == 0
    assert "0 rows" in capsys.readouterr().out


def test_tsv_sniffed_automatically(tmp_path, capsys):
    path = _write(tmp_path, "a.tsv", "a\tb\n1\tx\n2\ty\n")
    assert run([str(path)]) == 0
    assert "integer" in capsys.readouterr().out


def test_semicolon_delimiter_sniffed(tmp_path, capsys):
    path = _write(tmp_path, "a.csv", "a;b\n1;x\n2;y\n")
    assert run([str(path)]) == 0
    assert "integer" in capsys.readouterr().out


def test_no_header_flag(tmp_path, capsys):
    path = _write(tmp_path, "a.csv", "1,x\n2,y\n")
    assert run([str(path), "--no-header"]) == 0
    out = capsys.readouterr().out
    assert "col_1" in out and "col_2" in out


def test_columns_filter_and_unknown_column(tmp_path, capsys):
    path = _write(tmp_path, "a.csv", SAMPLE)
    assert run([str(path), "--columns", "city"]) == 0
    out = capsys.readouterr().out
    assert "city" in out and "age" not in out

    assert run([str(path), "--columns", "nope"]) == 1
    assert "Unknown column" in capsys.readouterr().err


def test_ragged_rows_warn_but_still_work(tmp_path, capsys):
    path = _write(tmp_path, "a.csv", "a,b\n1,x\n2\n3,y,extra\n")
    assert run([str(path)]) == 0
    out = capsys.readouterr().out
    assert "note:" in out
    assert "shorter" in out and "extra fields" in out


def test_bom_is_stripped(tmp_path, capsys):
    path = _write(tmp_path, "a.csv", "\ufeffa,b\n1,x\n", encoding="utf-8")
    assert run([str(path)]) == 0
    out = capsys.readouterr().out
    assert "col_1" not in out  # header kept its real name, not "col_1"
    assert "a" in out


def test_output_refuses_to_overwrite_without_force(tmp_path, capsys):
    src = _write(tmp_path, "a.csv", SAMPLE)
    out = tmp_path / "report.txt"
    out.write_text("previous report")
    assert run([str(src), "--output", str(out)]) == 1
    assert "Refusing to overwrite" in capsys.readouterr().err
    assert out.read_text() == "previous report"

    assert run([str(src), "--output", str(out), "--force"]) == 0
    assert "3 rows" in out.read_text()


def test_bad_flags(capsys):
    # Validation errors are clean stderr messages with exit code 2,
    # matching argparse's convention for bad flags.
    assert run(["--limit", "0", "whatever.csv"]) == 2
    assert "--limit must be at least 1" in capsys.readouterr().err
    assert run(["--delimiter", ",,", "whatever.csv"]) == 2
    assert "single character" in capsys.readouterr().err


def test_limit_flag(tmp_path, capsys):
    path = _write(tmp_path, "a.csv", SAMPLE)
    assert run([str(path), "--limit", "2"]) == 0
    out = capsys.readouterr().out
    assert "2 rows" in out
    assert "--limit" in out  # the truncation note is shown


def test_module_entry_point_runs():
    result = subprocess.run(
        [sys.executable, "-m", "colpeek", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "colpeek 0.1.0" in result.stdout
