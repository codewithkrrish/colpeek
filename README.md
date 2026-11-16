# colpeek

Peek inside a CSV or TSV before you commit to opening it properly. One line of stats per column: what type it looks like, how much is missing, how many unique values, min/max, and the most common values.

```
$ colpeek examples/employees.csv
10 rows

column  type     missing    unique  min         max         top values
------  -------  ---------  ------  ----------  ----------  ------------------------------------------------
name    text     0 (0.0%)   10      —           —           Asha (1), Rohan (1), Meera (1), Arjun (1), ...
age     integer  1 (10.0%)  7       28          41          28 (3), 34 (1), 41 (1), 29 (1), 33 (1)
city    text     0 (0.0%)   4       —           —           Mumbai (3), Delhi (3), Bengaluru (2), Pune (2)
joined  date     0 (0.0%)   10      2021-09-18  2024-02-10  2023-01-15 (1), 2022-06-01 (1), ...
salary  number   2 (20.0%)  7       78000       110000      85000.5 (2), 92000 (1), 110000 (1), ...
active  boolean  0 (0.0%)   5       —           —           TRUE (3), true (2), false (2), yes (2), no (1)
```

## Why I built this

I kept getting handed CSVs — exports, scraped data, files from friends — and my first question was always the same: what is actually in here? Opening pandas for a ten-second question felt silly, and `head` tells you nothing about the 50,000 rows below it. So I wrote the tool I wanted: point it at a file, get the shape of every column in one screen.

## Install

```bash
pip install git+https://github.com/codewithkrrish/colpeek.git
```

Needs Python 3.9 or newer. No dependencies — it is only the standard library, so it installs anywhere in seconds.

Or clone it and run it straight from the folder:

```bash
git clone https://github.com/codewithkrrish/colpeek.git
cd colpeek
python -m colpeek examples/employees.csv
```

## Usage

```bash
colpeek data.csv                  # profile the whole file
colpeek data.tsv                  # tabs and semicolons are auto-detected
colpeek data.csv --json           # machine-readable output for scripts
colpeek data.csv --columns city,age
colpeek data.csv --limit 1000     # only profile the first 1000 rows
colpeek data.csv --top 10         # show 10 top values instead of 5
colpeek data.csv --na-values NA,N/A   # treat these as missing too
colpeek data.csv --no-header      # first row is data, columns become col_1, col_2...
colpeek data.csv --output report.txt --force
```

A few things I made sure of while writing it:

- **It never overwrites your files.** `--output` refuses to clobber an existing file unless you pass `--force`, and writes go through a temp file plus rename so a crash cannot leave a half-written report.
- **It tells you when it is guessing.** Mixed-type columns are labelled `mixed` instead of being forced into a type, and ragged rows get a warning line rather than silently dropping data.
- **It stays light on big files.** Rows stream through one at a time and unique-value tracking caps at 10,000 per column, so a 10-million-row export does not eat your RAM. Past the cap the unique count shows as a lower bound (`10000+`).

## How types are guessed

For each column, every non-empty value is checked against the strictest type first: integer, then number, then boolean (`true/false/yes/no`), then date (ISO and the common day-first/US formats). A column is only called an integer if *every* value parses as one — one stray `N/A` and the whole column is `mixed`, not a number with an asterisk. A column of `0`s and `1`s is an integer, not a boolean; booleans have to spell it out.

## Limitations

Honest ones, because the guessing is the whole point of the tool:

- **Type inference is a guess, not a fact.** Dates outside the common formats read as text, and a column of years (`2021`, `2022`) will read as integer, not date. Check the top values when something looks off.
- **Unique counts cap at 10,000 per column.** Past that you get a lower bound, not the exact number.
- **CSV and TSV only.** No Excel files, no JSON — that is a different tool.
- **Top values are case-sensitive.** `TRUE` and `true` count separately, because that is what is actually in your file.

## Project structure

```
colpeek/
  colpeek/
    __init__.py    # version
    __main__.py    # python -m colpeek
    cli.py         # flags, exit codes, atomic --output writes
    sniff.py       # delimiter detection, headers, ragged rows, encodings
    infer.py       # per-column type inference
    profile.py     # the one-pass stats engine
    render.py      # plain-text table and JSON output
    errors.py      # one exception type, human messages
  tests/           # pytest: inference, profiling, CLI end-to-end
  examples/
    employees.csv  # sample file used in the README
  pyproject.toml
```

## Tests

```bash
python -m pytest
```

30 tests covering happy paths and the awkward cases: empty files, missing files, header-only files, ragged rows, BOMs, bad flags, and the `--output` overwrite guard.

## License

MIT — see [LICENSE](LICENSE).

## Author

Built by [Krrish](https://github.com/codewithkrrish) — I make small tools that answer a question in ten seconds instead of ten minutes.
