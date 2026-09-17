"""What does the collector think is left, and what is actually in the manifest?

The last run exited 0, yet several 2026 months are well short of complete. Either the
remaining keys are failing quietly, or the collector's own enumeration never covered
them. This separates the two before any long re-run is started.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEADS = tuple(range(6, 73, 6))
CYCLES = ("00", "12")

manifest = [json.loads(l) for l in
            (ROOT / "outputs" / "gfs_gust_manifest_newperiod.jsonl").read_text(
                encoding="utf-8").splitlines() if l.strip()]
have: dict[tuple[str, str], set[int]] = defaultdict(set)
for r in manifest:
    have[(r["issue_date"], r["issue_cycle"])].add(int(r["lead_hours"]))

start, end = date(2025, 10, 1), date(2026, 8, 31)
n_days = (end - start).days + 1
expected_keys = n_days * len(CYCLES) * len(LEADS)
present_keys = sum(len(v) for v in have.values())
print(f"range {start} .. {end}: {n_days} days")
print(f"expected (date,cycle,lead) keys : {expected_keys:,}")
print(f"keys present in the manifest    : {present_keys:,}")
print(f"keys absent                     : {expected_keys - present_keys:,}")

print("\nper month: days with ANY data / days in month, and keys present")
for m in range(10, 22):
    year, month = (2026, m - 12) if m > 12 else (2025, m)
    first = date(year, month, 1)
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    days = [(first + timedelta(days=i)).isoformat() for i in range((nxt - first).days)]
    with_any = sum(1 for d in days if have.get((d, "00")) or have.get((d, "12")))
    keys = sum(len(have.get((d, c), ())) for d in days for c in CYCLES)
    want = len(days) * len(CYCLES) * len(LEADS)
    print(f"  {year}-{month:02d}: days with data {with_any:2d}/{len(days):2d} | "
          f"keys {keys:5,d}/{want:5,d} ({100 * keys / want:5.1f}%)")

# how many days have both cycles at all
missing_cycles = [d for d in ((start + timedelta(days=i)).isoformat() for i in range(n_days))
                  if not all(have.get((d, c)) for c in CYCLES)]
print(f"\ndays missing an entire cycle: {len(missing_cycles)}")
print("first few:", missing_cycles[:8])

fails = [json.loads(l) for l in
         (ROOT / "outputs" / "gfs_gust_failures_newperiod.jsonl").read_text(
             encoding="utf-8").splitlines() if l.strip()]
fail_keys = {(f["issue_date"], f["issue_cycle"], int(f["lead_hours"])) for f in fails}
print(f"\nfailure records: {len(fails)} ({len(fail_keys)} distinct keys)")
print("=> absent keys that are NOT explained by a logged failure: "
      f"{expected_keys - present_keys - len(fail_keys):,}")
