"""Which months of a collection are complete enough to be used as a hold-out?

A partially collected period can only serve as a post-sample test if some
contiguous block of issue dates is fully covered at both cycles and every lead in
the grid that collection was asked for. This reports completeness per calendar
month, and writes outputs/g5_collection_coverage.json so the choice of hold-out
window in the manuscript is auditable rather than asserted.

The expected lead grid is inferred from the manifest, because the 6-hourly and the
denser 3-hourly pull use different grids.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

CYCLES = ("00", "12")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", default="outputs/gfs_gust_manifest_newperiod.jsonl")
    parser.add_argument("--out", default="outputs/g5_collection_coverage.json")
    args = parser.parse_args()
    root: Path = args.root

    seen: dict[tuple[str, str], set[int]] = defaultdict(set)
    dates: set[str] = set()
    expected: set[int] = set()
    path = root / args.manifest
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        seen[(r["issue_date"], r["issue_cycle"])].add(int(r["lead_hours"]))
        dates.add(r["issue_date"])
        expected.add(int(r["lead_hours"]))
    leads = tuple(sorted(expected))

    by_month: dict[str, dict] = {}
    # A day is "fully complete" only when both cycles carry every lead, but that
    # binary flag is a poor summary: one absent lead in one cycle marks the whole
    # month partial and hides the fact that 99% of the month is present. Key
    # completeness is reported alongside it, and a day is "partly present" when it
    # carries at least one cycle but not all leads.
    for iso in sorted(dates):
        complete = sum(1 for c in CYCLES if seen.get((iso, c), set()) >= set(leads))
        keys = sum(len(seen.get((iso, c), ())) for c in CYCLES)
        m = by_month.setdefault(iso[:7], {"days_present": 0, "days_complete": 0,
                                          "days_in_month": 0, "keys": 0, "keys_expected": 0})
        m["days_present"] += 1
        m["days_complete"] += 1 if complete == len(CYCLES) else 0
        m["keys"] += keys
        m["keys_expected"] += len(CYCLES) * len(leads)
    for month in by_month:
        y, mo = (int(v) for v in month.split("-"))
        nxt = date(y + (mo == 12), (mo % 12) + 1, 1)
        by_month[month]["days_in_month"] = (nxt - date(y, mo, 1)).days

    complete_months = [m for m, v in sorted(by_month.items())
                       if v["days_complete"] == v["days_in_month"]]
    report = {
        "manifest": args.manifest,
        "lead_grid": list(leads),
        "cycles": list(CYCLES),
        "issue_dates": len(dates),
        "run_cycles": sum(len(v) for v in seen.values()),
        "by_month": by_month,
        "complete_months": complete_months,
        "first_date": min(dates) if dates else None,
        "last_date": max(dates) if dates else None,
    }
    (root / args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                 encoding="utf-8")

    print(f"{args.manifest}: {len(dates)} issue dates, "
          f"{sum(len(v) for v in seen.values())} run-cycles, lead grid {list(leads)}")
    for month, v in sorted(by_month.items()):
        pct = 100.0 * v["keys"] / v["keys_expected"] if v["keys_expected"] else 0.0
        print(f"  {month}: keys {v['keys']:5,d}/{v['keys_expected']:5,d} ({pct:5.1f}%) | "
              f"days with every lead {v['days_complete']:2d}/{v['days_in_month']:2d}")
    print("complete months:", complete_months or "none")


if __name__ == "__main__":
    main()
