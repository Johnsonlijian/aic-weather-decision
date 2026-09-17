"""Scientific cohort and lineage checks for the GFS/KNMI pilot table."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--input", type=Path, default=None)
    args = p.parse_args()
    root = args.root
    source = args.input or root / "outputs" / "gfs_knmi_pilot.csv"
    df = pd.read_csv(source, parse_dates=["issue_time", "valid_time"])
    checks = {}
    checks["nonempty"] = bool(len(df) > 0)
    checks["unique_issue_station_lead"] = bool(not df.duplicated(["issue_time", "station_id", "lead_hours"]).any())
    checks["unique_valid_station"] = bool(not df.duplicated(["valid_time", "station_id"]).any())
    checks["lead_matches_timestamps"] = bool(((df.valid_time - df.issue_time).dt.total_seconds() / 3600 == df.lead_hours).all())
    checks["pairing_rule_constant"] = bool((df.pairing_rule == "GFS valid_time == KNMI interval_end").all())
    checks["observation_complete"] = bool(df.KNMI_FX_ms.notna().all() and df.observation_available.all())
    checks["nonnegative_wind"] = bool((df[["GUST_ms", "KNMI_FX_ms"]] >= 0).all().all())
    checks["source_files_exist"] = bool(all((root / "data" / "raw" / "gfs_pilot" / name).exists() for name in df.gfs_file.unique()))
    checks["single_station_declared"] = bool(df.station_id.astype(str).nunique() == 1)
    train = df[(df.valid_time >= "2025-01-01") & (df.valid_time < "2025-01-17")]
    validation = df[(df.valid_time >= "2025-01-17") & (df.valid_time < "2025-01-24")]
    test = df[(df.valid_time >= "2025-01-24") & (df.valid_time < "2025-02-02")]
    split_counts = {
        "train": len(train), "validation": len(validation), "test": len(test),
        "overlap_issue_times": len(set(train.issue_time) & set(validation.issue_time) | set(train.issue_time) & set(test.issue_time) | set(validation.issue_time) & set(test.issue_time)),
    }
    profiler_path = root / "outputs" / "gfs_knmi_pilot_data_profiler.json"
    profiler = json.loads(profiler_path.read_text(encoding="utf-8")) if profiler_path.exists() else {}
    result = {
        "audit_status": "PASS_WITH_PILOT_LIMITS" if all(checks.values()) else "FAIL",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(source),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "rows": len(df),
        "checks": checks,
        "split_counts": split_counts,
        "generic_profile": {
            "dqs_reference": profiler.get("dqs", {}).get("score"),
            "source": str(profiler_path) if profiler_path.exists() else None,
            "interpretation": "secondary completeness/consistency signal; not proof of scientific validity, independence, representativeness, or submission readiness",
        },
        "scientific_unit": "one archived forecast issue time × one station × one six-hour lead",
        "p0_findings": [],
        "p1_findings": [
            "GFS publication latency is not established; this is not an operational replay.",
            "Only one station, one month, and one lead are included.",
            "The 20 m/s observation event has zero cases and is not estimable.",
        ],
        "p2_findings": [
            "GUST and FX have different temporal support and require an explicit mapping in any downstream model.",
            "The aligned table is a derived non-redistribution artifact; raw archives remain under data/raw.",
        ],
        "claim_consequence": "Use only to validate ingestion, endpoint alignment, frozen split code, and calibration plumbing; do not report forecast skill or scheduling value.",
    }
    out = root / "outputs" / "gfs_knmi_pilot_audit.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "audit_status": result["audit_status"], "checks_failed": [k for k, v in checks.items() if not v]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
