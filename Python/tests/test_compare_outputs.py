"""The CI reproducibility check must flag committed outputs that the pipeline no longer produces."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "compare_outputs", ROOT / "Tools" / "compare_outputs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_pack(root: Path, revenue: float, status: str, rows: list[tuple]) -> None:
    (root / "Data").mkdir(parents=True)
    (root / "SQL").mkdir()
    (root / "Data" / "monthly_pnl.csv").write_text(
        f"month,revenue,status\n2026-01,{revenue:.6f},{status}\n2026-02,10.000000,\n",
        encoding="utf-8",
    )
    (root / "Data" / "validation_report.json").write_text(
        json.dumps({"all_passed": True, "passed_checks": 17}), encoding="utf-8"
    )
    with sqlite3.connect(root / "SQL" / "integrated_fpa_analytics.db") as connection:
        connection.execute("CREATE TABLE fact_actuals (month TEXT, amount REAL)")
        connection.executemany("INSERT INTO fact_actuals VALUES (?, ?)", rows)


@pytest.fixture()
def compare_outputs():
    return _load()


def test_identical_packs_match(tmp_path, compare_outputs):
    rows = [("2026-01", 1.0), ("2026-02", 2.0)]
    _write_pack(tmp_path / "a", 100.0, "Favorable", rows)
    _write_pack(tmp_path / "b", 100.0 * (1 + 1e-12), "Favorable", rows)
    assert compare_outputs.compare(tmp_path / "a", tmp_path / "b") == []


def test_stale_values_are_reported(tmp_path, compare_outputs):
    _write_pack(tmp_path / "committed", 100.0, "Favorable", [("2026-01", 1.0), ("2026-02", 2.0)])
    _write_pack(tmp_path / "fresh", 101.0, "Unfavorable", [("2026-01", 1.0)])
    (tmp_path / "fresh" / "Data" / "validation_report.json").write_text(
        json.dumps({"all_passed": True, "passed_checks": 16}), encoding="utf-8"
    )
    (tmp_path / "fresh" / "Data" / "new_table.csv").write_text("a\n1\n", encoding="utf-8")

    errors = compare_outputs.compare(tmp_path / "committed", tmp_path / "fresh")

    assert "Data/monthly_pnl.csv row 1 column revenue: 100.0 != 101.0" in errors
    assert "Data/validation_report.json.passed_checks: 17 != 16" in errors
    assert "Data/new_table.csv: missing in committed" in errors
    assert "SQL/integrated_fpa_analytics.db:fact_actuals: 2 rows != 1 rows" in errors
    argv = ["compare_outputs.py", str(tmp_path / "committed"), str(tmp_path / "fresh")]
    assert compare_outputs.main(argv) == 1
