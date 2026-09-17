#!/usr/bin/env python
"""Check that Table 4 and Table 5 do not report the same quantity two ways.

Table 4 reports peak relative economic value on the primary held-out split. Table 5
reports the same three peaks for each declared publication-latency rule, on a rebuild that
holds the window gates common across the four rules so the comparison is like-for-like.

A reviewer noticed that the 4 h row of Table 5 (0.615 / 0.617 / 0.529) differs from the
12 m/s row of Table 4 (0.616 / 0.618 / 0.530) while the text claimed the 4 h column
"reproduces the primary analysis exactly, epoch for epoch". The two are not the same
sample: the rebuild admits more epochs than the primary split, which is why the peaks move
in the third decimal.

This script prints both samples and both peak sets, and states whether the "exactly, epoch
for epoch" claim is supportable. It is the guard that keeps the two tables from silently
drifting apart again.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "outputs" / "g5_block_v3_economic_value.json"
LATENCY = ROOT / "outputs" / "g5_latency_sensitivity.json"
REPLAY = ROOT / "outputs" / "g5_replay_v3.json"
RULES = ("calibrated", "tuned_raw", "fixed_raw")


def peaks(path: Path, limit: float) -> dict[str, tuple[float, float]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    row = next(r for r in rows if abs(r["threshold"] - limit) < 1e-9)
    out = {}
    for rule in row["curve"][0]["rules"]:
        if rule not in RULES:
            continue
        best = max(((c["cost_loss_ratio"], c["rules"][rule]["relative_economic_value"])
                    for c in row["curve"]), key=lambda kv: kv[1])
        out[rule] = best
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=float, default=12.0)
    args = ap.parse_args()

    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    primary_n = replay["test_epochs"]

    print(f"primary split (Table 4): {primary_n:,} epochs, "
          f"{replay['test_positives']:,} positives")
    print("Table 4 peaks at the 12 m/s limit:")
    p_peaks = peaks(PRIMARY, args.limit)
    for rule in RULES:
        r, v = p_peaks[rule]
        print(f"   {rule:<12} {v:.4f}  (r={r:.4f})")

    lat = json.loads(LATENCY.read_text(encoding="utf-8"))
    print()
    print("Table 5 rows (common window gates across the four rules):")
    print(f"   {'lat':>4} {'epochs':>10} {'positives':>10} "
          f"{'calibrated':>11} {'tuned_raw':>10} {'fixed_raw':>10}")
    for row in lat["rows"]:
        print(f"   {row['latency_hours']:>4} {row['test_epochs']:>10,} "
              f"{row['test_positives']:>10,} {row['rev_calibrated']:>11.4f} "
              f"{row['rev_tuned_raw']:>10.4f} {row['rev_fixed_limit']:>10.4f}")

    row4 = next(r for r in lat["rows"] if r["latency_hours"] == 4)
    same_n = row4["test_epochs"] == primary_n
    print()
    print(f"4 h row epoch count == primary split? {same_n} "
          f"({row4['test_epochs']:,} vs {primary_n:,}, "
          f"difference {row4['test_epochs'] - primary_n:+,})")

    deltas = {"calibrated": row4["rev_calibrated"] - p_peaks["calibrated"][1],
              "tuned_raw": row4["rev_tuned_raw"] - p_peaks["tuned_raw"][1],
              "fixed_raw": row4["rev_fixed_limit"] - p_peaks["fixed_raw"][1]}
    print("4 h row minus Table 4:")
    for rule, d in deltas.items():
        print(f"   {rule:<12} {d:+.4f}")
    worst = max(abs(d) for d in deltas.values())
    print(f"largest absolute difference: {worst:.4f}")

    print()
    if same_n and worst < 5e-5:
        print("VERDICT: the 4 h row reproduces the primary split exactly. The manuscript "
              "may claim 'exactly, epoch for epoch'.")
        return 0
    print("VERDICT: the 4 h row does NOT reproduce the primary split. The rebuild uses a "
          "different sample,\nso the two tables legitimately differ in the third decimal "
          "and the manuscript must not claim\nthey agree epoch for epoch. It must instead "
          "state the differing sample size and treat the\nagreement as close rather than "
          "exact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
