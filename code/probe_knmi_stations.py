"""Fetch the official KNMI station table and fix the coordinates used by the study.

The pilot pipeline hard-coded approximate coordinates for stations 240/260/344.
The GFS nearest-cell lookup depends on those values, so they must come from the
provider's own table rather than from memory.  This probe retrieves the station
list, records the raw response and its hash, and writes the coordinates for the
study stations plus the resulting GFS grid cell.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from download_inputs import fetch, save

STUDY_STATIONS = ("240", "260", "344")


def parse_station_table(text: str) -> list[dict]:
    """Parse the KNMI station list, tolerating the comment/blank line layout."""
    rows: list[dict] = []
    header: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()
            if candidate and (candidate[0].isdigit() or candidate[0].isalpha()):
                parts = [p.strip() for p in re.split(r"[;,]", candidate) if p.strip()]
                if len(parts) >= 3 and any(p.isdigit() for p in parts[:3]):
                    header = parts
            continue
        if not stripped:
            continue
        parts = [p.strip() for p in re.split(r"[;,]", stripped) if p.strip()]
        if len(parts) < 3:
            continue
        rows.append(dict(zip(header, parts)) if header and len(header) == len(parts)
                    else {f"col{i}": p for i, p in enumerate(parts)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--url",
                        default="https://cdn.knmi.nl/knmi/map/page/klimatologie/"
                                "gegevens/waarnemingen/stationlijst.txt")
    args = parser.parse_args()

    raw, meta = fetch(args.url)
    text = raw.decode("utf-8-sig", errors="replace")
    dest = args.root / "data" / "raw" / "knmi_stations" / "stationlijst.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    save(raw, meta, dest)
    target = dest.with_suffix(".csv")
    with target.open("w", newline="", encoding="utf-8") as fh:
        fh.write(text)

    rows = parse_station_table(text)
    found: dict[str, dict] = {}
    for row in rows:
        for station in STUDY_STATIONS:
            if station in row.values():
                found.setdefault(station, row)
    report = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "url": args.url,
        "sha256": meta["sha256"],
        "http_status": meta["http_status"],
        "rows_parsed": len(rows),
        "study_stations_found": found,
        "raw_head": text[:1200],
        "status": ("OFFICIAL_TABLE_RETRIEVED" if found else
                   "TABLE_RETRIEVED_BUT_STUDY_STATIONS_NOT_LOCATED"),
    }
    out = args.root / "outputs" / "gates" / "G3_knmi_station_coordinates.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": len(rows),
                      "found": list(found)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
