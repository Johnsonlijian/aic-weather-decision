"""Build a conservative, auditable weather-variable semantics probe.

This is a metadata and one-pair smoke analysis.  It does not estimate forecast
skill, calibration, or scheduling value.  KNMI FX is a preceding-hour maximum;
the GFS GUST field is an instantaneous gridded forecast.  The only permitted
pairing rule here is to match the GFS valid instant to a KNMI interval end.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def iso_from_unix(value: int) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def summarize_knmi(root: Path, stations: list[str], years: list[int]) -> dict:
    chunks: list[dict] = []
    total = missing_fx = missing_fh = 0
    for station in stations:
        for year in years:
            path = root / "data" / "raw" / "knmi" / f"{station}_{year}.csv"
            rows = read_csv(path)
            ends = [r["interval_end"] for r in rows]
            if ends != sorted(ends) or len(ends) != len(set(ends)):
                raise ValueError(f"non-monotone or duplicate KNMI interval: {path}")
            fx_missing = sum(not r["FX_ms"] for r in rows)
            fh_missing = sum(not r["FH_ms"] for r in rows)
            chunks.append({
                "station_id": station,
                "year": year,
                "rows": len(rows),
                "first_interval_end": ends[0],
                "last_interval_end": ends[-1],
                "missing_FX": fx_missing,
                "missing_FH": fh_missing,
            })
            total += len(rows)
            missing_fx += fx_missing
            missing_fh += fh_missing
    return {
        "source_type": "station_observation",
        "variable": "FX_ms",
        "provider_semantics": "maximum wind speed during the preceding hour",
        "availability_status": "historical archive; operational latency not established",
        "stations": stations,
        "years": years,
        "chunks": chunks,
        "total_rows": total,
        "missing_FX": missing_fx,
        "missing_FH": missing_fh,
    }


def summarize_gfs(root: Path, stations_csv: Path) -> dict:
    metadata = json.loads((root / "data" / "raw" / "gfs_20250101_00_f006_gust.grib2.metadata.json").read_text(encoding="utf-8"))
    rows = read_csv(stations_csv)
    if len(rows) != 1:
        raise ValueError("the probe expects exactly one decoded GFS station row")
    row = rows[0]
    ref = int(row["forecast_ref_unix"])
    valid = int(row["forecast_valid_unix"])
    return {
        "source_type": "gridded_forecast",
        "variable": "GUST_ms",
        "provider_semantics": "instantaneous surface gust forecast at the valid time",
        "record_type": "operational_archive_probe",
        "reference_time": iso_from_unix(ref),
        "valid_time": iso_from_unix(valid),
        "lead_hours": round((valid - ref) / 3600, 6),
        "publication_proxy": metadata.get("headers", {}).get("Last-Modified"),
        "publication_latency_status": metadata.get("information_time_status"),
        "decoded_station_row": row,
        "grid_shape": metadata.get("grid_shape"),
        "decoder": metadata.get("decoder"),
    }


def pair_smoke(root: Path, gfs_summary: dict) -> dict:
    valid = gfs_summary["valid_time"]
    path = root / "data" / "raw" / "knmi" / "260_2025.csv"
    rows = [r for r in read_csv(path) if r["interval_end"] == valid]
    if len(rows) != 1:
        raise ValueError(f"expected one KNMI row at {valid}, got {len(rows)}")
    obs = rows[0]
    pred = gfs_summary["decoded_station_row"]
    return {
        "pairing_rule": "GFS valid_time == KNMI interval_end",
        "gfs_valid_time": valid,
        "station_id": obs["station_id"],
        "gfs_GUST_ms": float(pred["GUST_ms"]),
        "knmi_FX_ms": float(obs["FX_ms"]) if obs["FX_ms"] else None,
        "interpretation": "semantic smoke pair only; no skill or calibration estimate",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()
    stations = ["240", "260", "344"]
    years = [2021, 2022, 2023, 2024, 2025]
    knmi = summarize_knmi(args.root, stations, years)
    gfs = summarize_gfs(args.root, args.root / "data" / "raw" / "gfs_20250101_00_f006_gust.stations.csv")
    result = {
        "analysis_status": "PROBE_ONLY_NO_PERFORMANCE_RESULT",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "knmi": knmi,
        "gfs": gfs,
        "pair_smoke": pair_smoke(args.root, gfs),
        "required_before_calibration": [
            "operational forecast publication/availability archive",
            "multiple issue times and leads",
            "frozen train/validation/test split",
            "calibration model specified before test evaluation",
            "predeclared missingness and administrative-cutoff denominator rules",
        ],
    }
    out = args.out or args.root / "outputs" / "weather_semantics_probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
