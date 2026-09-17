"""Forecast-latency sensitivity of the headline results.

The 4 h publication latency is a declared assumption supported by sampled
archive metadata, not a provider guarantee, so the audit chain is re-run on
epoch tables built with 4, 6, 8 and 12 h rules. All four tables are built with
the same 6/12 h window gates, so the only thing that changes between them is
which archived run each decision epoch is allowed to see.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def peak(curve: list[dict], rule: str) -> float:
    vals = [c["rules"][rule]["relative_economic_value"] for c in curve
            if c["rules"][rule]["relative_economic_value"]
            == c["rules"][rule]["relative_economic_value"]]
    return float(max(vals)) if vals else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--limit", type=float, default=12.0)
    args = parser.parse_args()
    root: Path = args.root

    rows = []
    for hours in (4, 6, 8, 12):
        table = root / "outputs" / f"epochs_lat{hours}.csv"
        prefix = root / "outputs" / f"g5_lat{hours}_calibration.json"
        if not table.exists() or not prefix.exists():
            rows.append({"latency_hours": hours, "status": "not built"})
            continue
        frame = pd.read_csv(table, usecols=["split", f"L12_thr{args.limit}"])
        test = frame[frame["split"] == "TEST"]
        cal = json.loads(prefix.read_text(encoding="utf-8"))
        rev = json.loads((root / "outputs" / f"g5_lat{hours}_economic_value.json").read_text(encoding="utf-8"))
        entry = next(r for r in cal if abs(r["threshold"] - args.limit) < 1e-9)
        rv = next(r for r in rev if abs(r["threshold"] - args.limit) < 1e-9)
        rows.append({
            "latency_hours": hours,
            "status": "built",
            "test_epochs": int(len(test)),
            "test_positives": int(test[f"L12_thr{args.limit}"].sum()),
            "skill_vs_climatology": round(entry["models"]["binned"]["test"]["skill_vs_climatology"], 3),
            "skill_vs_raw": round(entry["models"]["binned"]["test"]["skill_vs_raw_threshold"], 3),
            "rev_calibrated": round(peak(rv["curve"], "calibrated"), 3),
            "rev_tuned_raw": round(peak(rv["curve"], "tuned_raw"), 3),
            "rev_fixed_limit": round(peak(rv["curve"], "fixed_raw"), 3),
        })

    report = {"limit": args.limit, "rows": rows}
    (root / "outputs" / "g5_latency_sensitivity.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"| Latency (h) | Test epochs | Skill vs clim | Skill vs raw | REV calibrated | REV tuned raw | REV documented |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        if r["status"] != "built":
            print(f"| {r['latency_hours']} | {r['status']} | | | | | |")
            continue
        print(f"| {r['latency_hours']} | {r['test_epochs']:,} | {r['skill_vs_climatology']:+.3f} | "
              f"{r['skill_vs_raw']:+.3f} | {r['rev_calibrated']:.3f} | {r['rev_tuned_raw']:.3f} | "
              f"{r['rev_fixed_limit']:.3f} |")


if __name__ == "__main__":
    main()
