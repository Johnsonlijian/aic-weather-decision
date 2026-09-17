"""Create a selective, non-redistributive DSLIB construction inventory.

Only the analysis-sheet metadata are read from the release ZIP.  No project
Excel, Protrack, or project-card files are extracted.  The resulting CSV is a
candidate-network inventory, not evidence that any project contains a
weather-sensitive operation contract.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import openpyxl


def archive_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def members_by_code(names: list[str], folder: str) -> set[str]:
    result = set()
    for name in names:
        if not name.startswith(f"DSLIB 3.4/{folder}/") or name.endswith("/") or "/._" in name:
            continue
        match = re.match(r"C\d{4}-\d{2}", Path(name).name)
        if match:
            result.add(match.group(0))
    return result


def rows_from_workbook(data: bytes) -> list[dict]:
    workbook = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    sheet = workbook["DSLIB"]
    headers = [cell.value for cell in sheet[3]]
    indexes = {h: i for i, h in enumerate(headers) if h}
    rows = []
    for values in sheet.iter_rows(min_row=4, values_only=True):
        if values[0] is None:
            continue
        sector = str(values[indexes["Sector"]] or "")
        if not sector.lower().startswith("construction"):
            continue
        rows.append({
            "code": values[indexes["Code"]],
            "project_name": values[indexes["Project name"]],
            "sector": sector,
            "keywords": values[indexes["Keywords"]],
            "baseline_schedule": values[indexes["Baseline Schedule"]],
            "risk_analysis": values[indexes["Risk Analysis"]],
            "project_control": values[indexes["Project Control"]],
            "project_flag": values[indexes["Project"]],
            "tracking": values[indexes["Tracking"]],
            "n_activities": values[indexes["# activities"]],
            "planned_duration_days": values[indexes["PD (days)"]],
            "bac": values[indexes["BAC"]],
            "resources_flag": values[indexes["Resources"]],
            "renewable_resources": values[indexes["Renewable"]],
            "consumable_resources": values[indexes["Consumable"]],
            "resource_conflict": values[indexes["Resource Conflict in Schedule"]],
            "early_late": values[indexes["Early/late"]],
            "under_over_budget": values[indexes["Under/over budget"]],
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    archive = args.root / "data" / "raw" / "networks" / "DSLIB3.4.zip"
    digest = archive_hash(archive)
    with ZipFile(archive) as z:
        names = z.namelist()
        workbook = z.read("DSLIB 3.4/DSLIB_Analysis_Sheet.xlsx")
    protrack = members_by_code(names, "Protrack")
    excel = members_by_code(names, "Excel")
    cards = members_by_code(names, "Project Card")
    rows = rows_from_workbook(workbook)
    for row in rows:
        code = str(row["code"])
        row.update({
            "source_archive": "data/raw/networks/DSLIB3.4.zip",
            "archive_sha256": digest,
            "analysis_sheet_member": "DSLIB 3.4/DSLIB_Analysis_Sheet.xlsx",
            "has_protrack": code in protrack,
            "has_excel": code in excel,
            "has_project_card": code in cards,
            "inclusion_rule": "sector starts with Construction (case-insensitive)",
            "rights_status": "third-party release; redistribution and project-level use rights require audit",
        })
    fields = [
        "source_archive", "archive_sha256", "analysis_sheet_member", "code", "project_name", "sector",
        "keywords", "baseline_schedule", "risk_analysis", "project_control", "project_flag", "tracking",
        "n_activities", "planned_duration_days", "bac", "resources_flag", "renewable_resources",
        "consumable_resources", "resource_conflict", "early_late", "under_over_budget", "has_protrack",
        "has_excel", "has_project_card", "inclusion_rule", "rights_status",
    ]
    out = args.out or args.root / "outputs" / "dslib_construction_inventory.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "analysis_status": "SELECTIVE_METADATA_INVENTORY_NO_PROJECT_FILES_EXTRACTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "archive": str(archive),
        "archive_sha256": digest,
        "archive_members": len(names),
        "workbook_member": "DSLIB 3.4/DSLIB_Analysis_Sheet.xlsx",
        "all_dslib_rows": 231,
        "construction_rows": len(rows),
        "protrack_codes": len(protrack),
        "excel_codes": len(excel),
        "project_card_codes": len(cards),
        "project_card_missing_for_construction": sum(not (str(r["code"]) in cards) for r in rows),
        "rights_status": "third-party release; redistribution and project-level use rights require audit",
        "scientific_boundary": "Inventory fields are candidate project-network metadata; they do not establish weather sensitivity, operation duration, forecast availability, or empirical scheduling value.",
    }
    meta_out = out.with_suffix(".metadata.json")
    meta_out.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "metadata": str(meta_out),
                      "construction_rows": len(rows),
                      "project_card_missing_for_construction": metadata["project_card_missing_for_construction"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
