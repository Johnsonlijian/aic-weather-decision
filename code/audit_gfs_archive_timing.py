"""Audit archive-object timestamps without treating them as live availability."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from statistics import median


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = p.parse_args()
    raw = args.root / "data" / "raw" / "gfs_pilot"
    rows = []
    failures = []
    for station_file in sorted(raw.glob("*.stations.csv")):
        meta_file = station_file.with_suffix("").with_suffix(".grib2.metadata.json")
        if not meta_file.exists():
            failures.append({"station_file": station_file.name, "error": "metadata missing"})
            continue
        with station_file.open(encoding="utf-8", newline="") as f:
            station = next(csv.DictReader(f))
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        last_modified = meta.get("headers", {}).get("Last-Modified")
        if not last_modified:
            failures.append({"station_file": station_file.name, "error": "Last-Modified missing"})
            continue
        issue = datetime.fromtimestamp(int(station["forecast_ref_unix"]), tz=timezone.utc)
        valid = datetime.fromtimestamp(int(station["forecast_valid_unix"]), tz=timezone.utc)
        archive_time = parsedate_to_datetime(last_modified).astimezone(timezone.utc)
        rows.append({
            "gfs_file": station_file.name.replace(".stations.csv", ".grib2"),
            "issue_time": issue.isoformat(),
            "valid_time": valid.isoformat(),
            "last_modified_utc": archive_time.isoformat(),
            "archive_lag_hours": (archive_time - issue).total_seconds() / 3600,
            "valid_minus_archive_hours": (valid - archive_time).total_seconds() / 3600,
            "interpretation": "archive object timestamp proxy; not operational publication evidence",
        })
    rows.sort(key=lambda r: r["issue_time"])
    out = args.root / "outputs" / "gfs_pilot_archive_timing.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["gfs_file", "error"])
        writer.writeheader()
        writer.writerows(rows)
    lags = [r["archive_lag_hours"] for r in rows]
    result = {
        "analysis_status": "ARCHIVE_OBJECT_TIMING_ONLY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "failures": failures,
        "archive_lag_hours": {
            "min": min(lags) if lags else None,
            "median": median(lags) if lags else None,
            "max": max(lags) if lags else None,
        },
        "interpretation": "Last-Modified is retained as a cloud-object timestamp proxy. It does not prove that a forecast was published or visible to a controller at that time.",
        "operational_availability_status": "NOT_ESTABLISHED",
        "required_rule": "Use a conservative declared availability lag or obtain provider publication logs before online backtesting.",
    }
    meta_out = out.with_suffix(".metadata.json")
    meta_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "metadata": str(meta_out), "rows": len(rows), "failures": len(failures), "archive_lag_hours": result["archive_lag_hours"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
