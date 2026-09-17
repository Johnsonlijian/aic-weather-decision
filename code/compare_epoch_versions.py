"""Verify that the corrected KNMI field semantics left the wind path unchanged.

Compares two decision-epoch tables built before and after the precipitation /
duration decoding fix. The wind columns must agree exactly on every shared
(station_id, epoch) key; only row coverage and the (now removed) joint-hazard
columns may differ. Any wind mismatch means the parser change leaked into the
paper's primary result and must be investigated before the analysis is re-run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

WIND_COLUMNS = ["block_max_L6", "lead_L6", "obs_max_gust_L6",
                "block_max_L12", "lead_L12", "obs_max_gust_L12",
                "block_max_L24", "lead_L24", "obs_max_gust_L24"]
LABEL_COLUMNS = [f"L{h}_thr{t}" for h in (6, 12, 24)
                 for t in ("9.0", "12.0", "13.0", "16.5", "20.0")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--old", default="outputs/epochs_multi2.csv")
    parser.add_argument("--new", default="outputs/epochs_multi3.csv")
    args = parser.parse_args()

    root: Path = args.root
    key = ["station_id", "epoch"]
    old = pd.read_csv(root / args.old)
    new = pd.read_csv(root / args.new)
    cols = [c for c in WIND_COLUMNS + LABEL_COLUMNS if c in old.columns and c in new.columns]
    missing_in_new = [c for c in WIND_COLUMNS + LABEL_COLUMNS if c in old.columns and c not in new.columns]

    merged = old[key + cols + ["split"]].merge(
        new[key + cols + ["split"]], on=key, suffixes=("_old", "_new"), how="outer",
        indicator=True)
    shared = merged[merged["_merge"] == "both"]
    mismatches = {}
    for c in cols:
        a, b = shared[f"{c}_old"], shared[f"{c}_new"]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            bad = int((~((a - b).abs() < 1e-9) & ~(a.isna() & b.isna())).sum())
        else:
            bad = int((a.astype(str) != b.astype(str)).sum())
        if bad:
            mismatches[c] = bad
    split_mismatch = int((shared["split_old"] != shared["split_new"]).sum())

    joint_old = [c for c in old.columns if "_joint" in c or c.endswith("_dry") or "tempok" in c]
    joint_new = [c for c in new.columns if "_joint" in c or c.endswith("_dry") or "tempok" in c]

    report = {
        "old": args.old, "new": args.new,
        "old_rows": int(len(old)), "new_rows": int(len(new)),
        "shared_keys": int(len(shared)),
        "only_in_old": int((merged["_merge"] == "left_only").sum()),
        "only_in_new": int((merged["_merge"] == "right_only").sum()),
        "wind_columns_compared": cols,
        "wind_columns_missing_in_new": missing_in_new,
        "wind_value_mismatches": mismatches,
        "split_mismatches": split_mismatch,
        "joint_columns_in_old": len(joint_old),
        "joint_columns_in_new": len(joint_new),
        "verdict": ("wind path unchanged by the parser correction"
                    if not mismatches and not split_mismatch and not missing_in_new
                    else "MISMATCH - investigate before re-running the analysis"),
    }
    out = root / "outputs" / "epochs_version_diff.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
