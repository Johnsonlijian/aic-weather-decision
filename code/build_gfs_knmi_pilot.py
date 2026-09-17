"""Build a small, resumable GFS-GUST/KNMI-FX alignment pilot.

The pilot deliberately uses one station (KNMI 260, De Bilt), one six-hour
lead, and a bounded list of archived issue times.  It is an offline historical
probe: GFS publication latency is not established, so the output cannot be
used as an operational backtest or a journal result without an additional
availability audit.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from download_inputs import fetch
from ingest_gfs import ingest


def parse_gust_ranges(index_text: str) -> list[dict]:
    lines = index_text.splitlines()
    hits = []
    for i, line in enumerate(lines):
        if ":GUST:surface:" not in line:
            continue
        parts = line.split(":")
        start = int(parts[1])
        end = int(lines[i + 1].split(":")[1]) - 1 if i + 1 < len(lines) else None
        hits.append({"index_entry": line, "start_byte": start, "end_byte": end})
    return hits


def run_url(day: date, cycle: str) -> tuple[str, str]:
    stamp = day.strftime("%Y%m%d")
    idx = (f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{stamp}/{cycle}/atmos/"
           f"gfs.t{cycle}z.pgrb2.0p25.f006.idx")
    return idx, idx[:-4]


def issue_times(start: date, end: date, cycles: list[str]):
    day = start
    while day <= end:
        for cycle in cycles:
            yield day, cycle
        day += timedelta(days=1)


def read_obs(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_end = {r["interval_end"]: r for r in rows}
    if len(by_end) != len(rows):
        raise ValueError(f"duplicate KNMI interval ends in {path}")
    return by_end


def fetch_and_decode(root: Path, day: date, cycle: str, station: dict[str, object]) -> tuple[dict, dict]:
    raw_root = root / "data" / "raw" / "gfs_pilot"
    raw_root.mkdir(parents=True, exist_ok=True)
    stem = f"gfs_{day.strftime('%Y%m%d')}_{cycle}_f006_gust"
    idx_path = raw_root / f"{stem}.idx"
    out_path = raw_root / f"{stem}.grib2"
    station_csv = out_path.with_suffix(".stations.csv")
    if station_csv.exists() and out_path.exists() and idx_path.exists():
        with station_csv.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        return {"status": "cached", "stem": stem}, rows[0]

    idx_url, grib_url = run_url(day, cycle)
    idx_raw, idx_meta = fetch(idx_url)
    idx_text = idx_raw.decode("utf-8")
    ranges = parse_gust_ranges(idx_text)
    if len(ranges) != 1 or ranges[0]["end_byte"] is None:
        raise ValueError(f"expected one bounded GUST range for {idx_url}")
    idx_path.write_bytes(idx_raw)
    idx_meta.update(gust_ranges=ranges, grib_url=grib_url,
                    source_type="gridded_forecast",
                    record_type="operational_archive_probe",
                    temporal_support="instantaneous GUST at valid time",
                    availability_status="offline historical archive; publication latency not established")
    idx_path.with_suffix(idx_path.suffix + ".metadata.json").write_text(
        json.dumps(idx_meta, indent=2), encoding="utf-8")
    result = ingest(idx_path, out_path, [station])
    result_meta = json.loads(out_path.with_suffix(out_path.suffix + ".metadata.json").read_text(encoding="utf-8"))
    result_meta.update(issue_date=day.isoformat(), issue_cycle=cycle,
                       record_type="operational_archive_probe",
                       availability_status="offline historical archive; publication latency not established")
    out_path.with_suffix(out_path.suffix + ".metadata.json").write_text(
        json.dumps(result_meta, indent=2), encoding="utf-8")
    return {"status": "downloaded", "stem": stem, "bytes": result["bytes"],
            "index_sha256": idx_meta["sha256"]}, result["stations"][0]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--start", default="2025-01-01")
    p.add_argument("--end", default="2025-01-31")
    p.add_argument("--cycles", default="00,06,12,18")
    p.add_argument("--lead", type=int, default=6)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()
    if args.lead != 6:
        raise ValueError("this bounded pilot is defined for f006 only")
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    if end < start:
        raise ValueError("end precedes start")
    cycles = [x for x in args.cycles.split(",") if re.fullmatch(r"(?:00|06|12|18)", x)]
    if not cycles:
        raise ValueError("no valid cycles")
    obs = read_obs(args.root / "data" / "raw" / "knmi" / "260_2025.csv")
    station = {"station_id": "260", "latitude": 52.1, "longitude": 5.18}
    paired: list[dict] = []
    attempts: list[dict] = []
    for day, cycle in issue_times(start, end, cycles):
        try:
            info, forecast = fetch_and_decode(args.root, day, cycle, station)
            valid = datetime.fromtimestamp(int(forecast["forecast_valid_unix"]), tz=timezone.utc).isoformat()
            item = {
                "issue_date": day.isoformat(),
                "issue_cycle": cycle,
                "issue_time": datetime.fromtimestamp(int(forecast["forecast_ref_unix"]), tz=timezone.utc).isoformat(),
                "valid_time": valid,
                "lead_hours": float(forecast["forecast_seconds"]) / 3600,
                "station_id": forecast["station_id"],
                "latitude": float(forecast["latitude"]),
                "longitude": float(forecast["longitude"]),
                "grid_longitude": float(forecast["grid_longitude"]),
                "grid_latitude": float(forecast["grid_latitude"]),
                "GUST_ms": float(forecast["GUST_ms"]),
                "KNMI_FX_ms": float(obs[valid]["FX_ms"]) if valid in obs and obs[valid]["FX_ms"] else None,
                "gfs_file": info["stem"] + ".grib2",
                "pairing_rule": "GFS valid_time == KNMI interval_end",
            }
            item["observation_available"] = valid in obs and obs[valid]["FX_ms"] != ""
            paired.append(item)
            attempts.append({**info, "issue_date": day.isoformat(), "issue_cycle": cycle,
                             "valid_time": valid, "paired_observation": item["observation_available"]})
        except Exception as exc:  # noqa: BLE001 - retain per-run failure provenance and continue the bounded pilot
            attempts.append({"status": "failed", "issue_date": day.isoformat(),
                             "issue_cycle": cycle, "error": repr(exc)})
    paired.sort(key=lambda r: r["issue_time"])
    out = args.out or args.root / "outputs" / "gfs_knmi_pilot.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(paired[0]) if paired else ["issue_date", "issue_cycle"]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(paired)
    meta = {
        "analysis_status": "OFFLINE_ALIGNMENT_PILOT_NO_OPERATIONAL_BACKTEST",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "station": station,
        "start": args.start,
        "end": args.end,
        "cycles": cycles,
        "lead_hours": args.lead,
        "forecast_variable": "GFS GUST instantaneous gridded forecast",
        "observation_variable": "KNMI FX preceding-hour maximum wind speed",
        "pairing_rule": "GFS valid_time == KNMI interval_end",
        "rows_written": len(paired),
        "paired_observations": sum(bool(r["observation_available"]) for r in paired),
        "failed_attempts": sum(a.get("status") == "failed" for a in attempts),
        "availability_status": "offline historical archive; publication latency not established",
        "attempts": attempts,
        "no_performance_claim": True,
        "next_gate": "establish operational publication latency, then predeclare calibration and frozen test split",
    }
    meta_path = out.with_suffix(".metadata.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "metadata": str(meta_path),
                      "rows_written": len(paired),
                      "paired_observations": meta["paired_observations"],
                      "failed_attempts": meta["failed_attempts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
