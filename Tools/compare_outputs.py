"""Compare regenerated pipeline outputs with a copy of the committed ones.

Usage: python Tools/compare_outputs.py COMMITTED_ROOT [REGENERATED_ROOT]

COMMITTED_ROOT is a directory holding copies of the committed ``Data/`` folder and
``SQL/integrated_fpa_analytics.db`` (same relative paths). REGENERATED_ROOT defaults
to the repository after ``python -m fpa_system.run_pipeline``.

The pipeline rewrites ``Data/`` in place, so tests that run after it only see fresh
output; and SQLite bytes are not stable across runs. This check compares content
instead: CSV and JSON values (numbers within a relative
tolerance of 1e-9) and the rows of every SQLite table. Exit code 1 on any drift.
"""

from __future__ import annotations

import json
import math
import sqlite3
import sys
from pathlib import Path

import pandas as pd

REL_TOL = 1e-9
ABS_TOL = 1e-12
CSV_DIRS = ("Data",)
SQLITE_FILE = "SQL/integrated_fpa_analytics.db"
MANIFEST_EXCLUDED: tuple[str, ...] = ()


def _same_value(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if isinstance(left, float) and isinstance(right, float) and math.isnan(left):
            return math.isnan(right)
        return math.isclose(left, right, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return left == right


def _compare_json(left: object, right: object, where: str, errors: list[str]) -> None:
    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            errors.append(f"{where}: keys differ {sorted(left.keys() ^ right.keys())}")
            return
        for key in left:
            _compare_json(left[key], right[key], f"{where}.{key}", errors)
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            errors.append(f"{where}: length {len(left)} != {len(right)}")
            return
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            _compare_json(a, b, f"{where}[{index}]", errors)
    elif not _same_value(left, right):
        errors.append(f"{where}: {left!r} != {right!r}")


def _compare_rows(
    left: list[tuple], right: list[tuple], columns: list[str], where: str, errors: list[str]
) -> None:
    if len(left) != len(right):
        errors.append(f"{where}: {len(left)} rows != {len(right)} rows")
        return
    for row_number, (a, b) in enumerate(zip(left, right, strict=True), start=1):
        for column, x, y in zip(columns, a, b, strict=True):
            if not _same_value(x, y):
                errors.append(f"{where} row {row_number} column {column}: {x!r} != {y!r}")
                return


def _frame_rows(frame: pd.DataFrame) -> list[tuple]:
    clean = frame.astype(object).where(frame.notna(), None)
    return [tuple(row) for row in clean.itertuples(index=False, name=None)]


def compare(committed: Path, regenerated: Path) -> list[str]:
    errors: list[str] = []
    excluded = set(MANIFEST_EXCLUDED)
    for directory in CSV_DIRS:
        names = {
            path.relative_to(root).as_posix()
            for root in (committed, regenerated)
            for path in (root / directory).glob("*")
            if path.suffix in {".csv", ".json"}
        }
        for relative in sorted(names - excluded):
            old, new = committed / relative, regenerated / relative
            if not old.is_file() or not new.is_file():
                errors.append(f"{relative}: missing in {'committed' if new.is_file() else 'run'}")
                continue
            if old.suffix == ".json":
                _compare_json(
                    json.loads(old.read_text(encoding="utf-8")),
                    json.loads(new.read_text(encoding="utf-8")),
                    relative,
                    errors,
                )
                continue
            left = pd.read_csv(old, keep_default_na=False, na_values=[""])
            right = pd.read_csv(new, keep_default_na=False, na_values=[""])
            if list(left.columns) != list(right.columns):
                errors.append(f"{relative}: columns differ")
                continue
            _compare_rows(
                _frame_rows(left), _frame_rows(right), list(left.columns), relative, errors
            )

    old_db, new_db = committed / SQLITE_FILE, regenerated / SQLITE_FILE
    if old_db.is_file() and new_db.is_file():
        with sqlite3.connect(old_db) as a, sqlite3.connect(new_db) as b:
            schema = "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
            old_schema, new_schema = a.execute(schema).fetchall(), b.execute(schema).fetchall()
            if old_schema != new_schema:
                errors.append(f"{SQLITE_FILE}: table schema differs")
            else:
                for name, _ in old_schema:
                    query = f'SELECT * FROM "{name}"'
                    cursor = a.execute(query)
                    columns = [item[0] for item in cursor.description]
                    _compare_rows(
                        cursor.fetchall(),
                        b.execute(query).fetchall(),
                        columns,
                        f"{SQLITE_FILE}:{name}",
                        errors,
                    )
    elif old_db.is_file() != new_db.is_file():
        errors.append(f"{SQLITE_FILE}: present in only one side")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    committed = Path(argv[1])
    regenerated = Path(argv[2]) if len(argv) == 3 else Path(__file__).resolve().parents[1]
    errors = compare(committed, regenerated)
    for error in errors[:50]:
        print(f"DRIFT {error}")
    if errors:
        print(f"{len(errors)} difference(s) between committed and regenerated outputs.")
        return 1
    print("Regenerated outputs match the committed Data/ and SQLite layer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
