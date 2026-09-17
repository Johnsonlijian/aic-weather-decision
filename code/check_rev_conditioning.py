#!/usr/bin/env python
"""Check where the relative-economic-value normalisation is well conditioned.

Relative value is

    REV = (E_clim - E) / (E_clim - E_perfect),  E_clim = min(r, s),  E_perfect = r*s

with ``r`` the cost-loss ratio and ``s`` the event rate. The denominator ``min(r,s) - r*s``
is ``s*(1-r)`` once ``r > s``, so it vanishes as ``r -> 1``. Near the top of the ratio grid
REV is therefore a ratio of two near-zero expenses: the artifact contains a fixed-limit
value of about -30.9 at ``r = 0.99``, which is a property of the normalisation and not an
economic finding.

This script reports the denominator and REV at the ends of the grid, so the manuscript's
choice to report the paired comparison at five well-conditioned ratios is checkable rather
than asserted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# below this the normalisation denominator carries too little signal to divide by
DENOMINATOR_FLOOR = 0.02


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact", default="outputs/g5_block_v3_economic_value.json")
    ap.add_argument("--limit", type=float, default=12.0)
    ap.add_argument("--event-rate", type=float, default=None,
                    help="default: read from the replay artifact")
    args = ap.parse_args()

    rev = json.loads((ROOT / args.artifact).read_text(encoding="utf-8"))
    entry = next(r for r in rev if abs(r["threshold"] - args.limit) < 1e-9)
    curve = entry["curve"]

    rate = args.event_rate
    if rate is None:
        rate = float(entry.get("event_rate") or entry.get("base_rate") or 0.0)
    if not rate:
        replay = json.loads((ROOT / "outputs" / "g5_replay_v3.json").read_text(encoding="utf-8"))
        rate = float(replay["test_positives"]) / float(replay["test_epochs"])

    rules = list(curve[0]["rules"].keys())
    print(f"limit {args.limit:g} m/s | event rate s = {rate:.4f} | "
          f"{len(curve)} grid points from {curve[0]['cost_loss_ratio']:.3f} "
          f"to {curve[-1]['cost_loss_ratio']:.3f}")
    header = f"{'r':>7} {'denominator':>12} " + " ".join(f"{k:>12}" for k in rules)
    print(header)
    print("-" * len(header))

    ill_conditioned = []
    for c in curve:
        r = c["cost_loss_ratio"]
        den = min(r, rate) - r * rate
        if den < DENOMINATOR_FLOOR:
            ill_conditioned.append(r)
        if r <= 0.06 or r >= 0.55 or den < DENOMINATOR_FLOOR:
            vals = " ".join(f"{c['rules'][k]['relative_economic_value']:>12.3f}" for k in rules)
            print(f"{r:>7.4f} {den:>12.5f} {vals}")

    print()
    if ill_conditioned:
        print(f"{len(ill_conditioned)} grid point(s) have denominator < {DENOMINATOR_FLOOR}: "
              f"{ill_conditioned[0]:.3f}..{ill_conditioned[-1]:.3f}")
        print("REV is not interpretable there; the reported paired ratios must avoid that end.")
    else:
        print(f"every grid point has denominator >= {DENOMINATOR_FLOOR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
