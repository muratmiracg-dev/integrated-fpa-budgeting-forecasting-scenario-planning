"""Create reviewed, GitHub-ready FP&A delivery packages and manifests."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "Delivery"
DELIVERY.mkdir(exist_ok=True)

FULL_ZIP = DELIVERY / "Integrated_FPA_Full_Project_Source_and_Deliverables.zip"
KEY_ZIP = DELIVERY / "Integrated_FPA_Portfolio_Key_Deliverables.zip"

KEY_FILES = [
    "README.md",
    "Excel/Integrated_FP&A_Budgeting_Forecasting_Scenario_Planning_Model.xlsx",
    "PowerBI/Integrated_FPA_Planning_PBIP.zip",
    "PowerBI/Integrated_FPA_Measures.dax",
    "Presentation/Integrated_FPA_Budgeting_Forecasting_Scenario_Planning_Professional_Deck_EN.pptx",
    "Presentation/Entegre_FPA_Butceleme_Tahminleme_Senaryo_Planlama_Profesyonel_Sunum_TR.pptx",
    "Reports/Integrated_FPA_Executive_Report_12_Page_Vector_HD.pdf",
    "Images/executive-overview.png",
    "Images/solution-architecture.png",
    "Images/budget-vs-forecast.png",
    "Images/forecast-governance.png",
    "Images/cash-liquidity.png",
    "Images/scenario-risk.png",
    "Images/excel-fpa-dashboard.png",
    "Docs/linkedin_project_description.md",
    "Docs/executive_summary.md",
    "QA/delivery_validation.md",
]

EXCLUDED_PARTS = {
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "excel-previews",
    "report-pages",
    "previews-en",
    "previews-tr",
    "rendered-en",
    "rendered-tr",
    "final-rendered-en",
    "final-rendered-tr",
}

EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".ndjson"}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if "Delivery" in relative.parts:
        return False
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.is_symlink():
        return False
    return path.is_file()


all_files = sorted(path for path in ROOT.rglob("*") if include(path))
manifest = {
    "project": "Integrated FP&A Budgeting, Forecasting & Scenario Planning System",
    "version": "1.0.0",
    "prepared_for": "Murat Miraç Gedik",
    "release_date": str(date(2026, 7, 26)),
    "quality_status": "PASS",
    "project_file_count": len(all_files),
    "counts": {
        "csv": sum(path.suffix.lower() == ".csv" for path in all_files),
        "python": sum(path.suffix.lower() == ".py" for path in all_files),
        "sql": sum(path.suffix.lower() == ".sql" for path in all_files),
        "markdown": sum(path.suffix.lower() == ".md" for path in all_files),
        "images": sum(path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} for path in all_files),
    },
    "key_artifacts": [
        {
            "path": relative,
            "bytes": (ROOT / relative).stat().st_size,
            "sha256": digest(ROOT / relative),
        }
        for relative in KEY_FILES
    ],
}

(DELIVERY / "DELIVERY_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)

manifest_lines = [
    "# Delivery Manifest",
    "",
    "**Integrated FP&A Budgeting, Forecasting & Scenario Planning System**",
    "",
    f"- Version: `{manifest['version']}`",
    f"- Release date: `{manifest['release_date']}`",
    f"- Prepared for: `{manifest['prepared_for']}`",
    f"- Quality status: **{manifest['quality_status']}**",
    f"- Packaged project files: **{manifest['project_file_count']}**",
    "",
    "## Key artifacts",
    "",
    "| File | Size | SHA-256 |",
    "|---|---:|---|",
]
for item in manifest["key_artifacts"]:
    manifest_lines.append(
        f"| `{item['path']}` | {item['bytes']:,} bytes | `{item['sha256']}` |"
    )
(DELIVERY / "DELIVERY_MANIFEST.md").write_text(
    "\n".join(manifest_lines) + "\n", encoding="utf-8"
)

with zipfile.ZipFile(FULL_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in all_files:
        archive.write(path, path.relative_to(ROOT))
    archive.write(
        DELIVERY / "DELIVERY_MANIFEST.json", "Delivery/DELIVERY_MANIFEST.json"
    )
    archive.write(
        DELIVERY / "DELIVERY_MANIFEST.md", "Delivery/DELIVERY_MANIFEST.md"
    )

with zipfile.ZipFile(KEY_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for relative in KEY_FILES:
        archive.write(ROOT / relative, relative)
    archive.write(
        DELIVERY / "DELIVERY_MANIFEST.json", "DELIVERY_MANIFEST.json"
    )
    archive.write(
        DELIVERY / "DELIVERY_MANIFEST.md", "DELIVERY_MANIFEST.md"
    )

print(
    json.dumps(
        {
            "full_package": str(FULL_ZIP),
            "key_deliverables": str(KEY_ZIP),
            "project_files": len(all_files),
            "full_package_bytes": FULL_ZIP.stat().st_size,
            "key_package_bytes": KEY_ZIP.stat().st_size,
        },
        indent=2,
    )
)
