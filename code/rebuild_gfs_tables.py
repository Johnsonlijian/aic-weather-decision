"""Rebuild the per-station GUST tables from the JSONL manifest.

The first version of ``collect_gfs_gust_archive.py`` wrote rows with naive string
joining, so the HTTP ``Last-Modified`` value (which contains a comma, e.g.
``Wed, 24 Mar 2021 15:36:28 GMT``) shifted every following column by one.  The
manifest itself is JSON Lines and therefore intact, so the station tables can be
re-derived exactly, with correct CSV quoting, without re-downloading anything.

The rebuild also de-duplicates on (station, valid_time, issue_time, lead_hours),
which removes the rows the resumable collector wrote twice.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = ["station_id", "valid_time", "issue_time", "issue_date", "issue_cycle",
           "lead_hours", "GUST_ms", "grid_longitude", "grid_latitude",
           "message_sha256", "byte_start", "byte_end", "index_sha256",
           "index_last_modified"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", default="outputs/gfs_gust_manifest.jsonl")
    parser.add_argument("--data-dir", default="data/raw/gfs_gust")
    parser.add_argument("--backup-dir", default="data/raw/gfs_gust_broken_v1")
    args = parser.parse_args()

    root: Path = args.root
    manifest = root / args.manifest
    if not manifest.exists():
        raise SystemExit(f"manifest not found: {manifest}")

    data_dir = root / args.data_dir
    backup = root / args.backup_dir
    if data_dir.exists() and any(data_dir.glob("*_gust.csv")):
        backup.mkdir(parents=True, exist_ok=True)
        for path in data_dir.glob("*_gust.csv"):
            target = backup / path.name
            if not target.exists():
                path.replace(target)
        print(f"moved previous tables to {backup.name}")

    seen: set[tuple] = set()
    counters: Counter = Counter()
    writers: dict[tuple[str, int], csv.DictWriter] = {}
    handles: dict[tuple[str, int], object] = {}
    records = 0
    rejected = 0
    try:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            records += 1
            required = ("valid_time", "issue_time", "lead_hours", "stations",
                        "message_sha256", "index_sha256")
            missing = [k for k in required if k not in rec]
            if missing:
                rejected += 1
                continue
            year = int(rec["valid_time"][:4])
            for row in rec["stations"]:
                key = (str(row["station_id"]), rec["valid_time"], rec["issue_time"],
                       int(rec["lead_hours"]))
                if key in seen:
                    continue
                seen.add(key)
                bucket = (key[0], year)
                if bucket not in writers:
                    path = data_dir / f"{bucket[0]}_{year}_gust.csv"
                    fh = path.open("w", newline="", encoding="utf-8")
                    writer = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
                    writer.writeheader()
                    handles[bucket] = fh
                    writers[bucket] = writer
                writers[bucket].writerow({
                    "station_id": row["station_id"],
                    "valid_time": rec["valid_time"],
                    "issue_time": rec["issue_time"],
                    "issue_date": rec["issue_date"],
                    "issue_cycle": rec["issue_cycle"],
                    "lead_hours": rec["lead_hours"],
                    "GUST_ms": row["GUST_ms"],
                    "grid_longitude": row["grid_longitude"],
                    "grid_latitude": row["grid_latitude"],
                    "message_sha256": rec["message_sha256"],
                    "byte_start": rec["byte_start"],
                    "byte_end": rec["byte_end"],
                    "index_sha256": rec["index_sha256"],
                    "index_last_modified": rec["index_last_modified"] or "",
                })
                counters[bucket] += 1
    finally:
        for fh in handles.values():
            fh.close()

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest_records": records,
        "manifest_records_rejected": rejected,
        "unique_station_rows": int(sum(counters.values())),
        "rows_per_station_year": {f"{k[0]}_{k[1]}": v for k, v in sorted(counters.items())},
        "columns": COLUMNS,
        "note": ("Rebuilt from the JSONL manifest after the comma-in-Last-Modified CSV "
                 "defect. No data was re-downloaded and no value was altered."),
    }
    out = root / "outputs" / ("gfs_gust_tables_rebuild" + ("_" + args.manifest.split("manifest_")[-1].replace(".jsonl","") if "manifest_" in args.manifest else "") + ".json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("manifest_records", "unique_station_rows")}, ensure_ascii=False))
    print(json.dumps(report["rows_per_station_year"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
