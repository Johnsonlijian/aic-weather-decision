"""One-shot: make the coverage check honest, and audit the full post-sample range.

Two corrections. The coverage checker called a month "partial" when a single
(date, cycle, lead) key was absent, which read as though whole days were missing when
in fact no day lacks a cycle; it now reports key completeness. And the gap audit is
extended from the five-month window to the whole post-sample range, testing only the
leads the evaluation actually builds windows from.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ---- 1. coverage checker: report key completeness, not binary day flags ----
cov = ROOT / "code" / "check_collection_coverage.py"
t = cov.read_text(encoding="utf-8")
old = '''    by_month: dict[str, dict] = {}
    for iso in sorted(dates):
        d = date.fromisoformat(iso)
        complete = sum(1 for c in CYCLES if seen.get((iso, c), set()) >= set(leads))
        m = by_month.setdefault(iso[:7], {"days_present": 0, "days_complete": 0,
                                          "days_in_month": 0})
        m["days_present"] += 1
        m["days_complete"] += 1 if complete == len(CYCLES) else 0'''
new = '''    by_month: dict[str, dict] = {}
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
        m["keys_expected"] += len(CYCLES) * len(leads)'''
if old not in t:
    raise SystemExit("coverage block not found")
t = t.replace(old, new, 1)
old_print = '''    for month, v in sorted(by_month.items()):
        flag = "COMPLETE" if v["days_complete"] == v["days_in_month"] else "partial"
        print(f"  {month}: {v['days_complete']:3d}/{v['days_in_month']:3d} days complete  [{flag}]")'''
new_print = '''    for month, v in sorted(by_month.items()):
        pct = 100.0 * v["keys"] / v["keys_expected"] if v["keys_expected"] else 0.0
        print(f"  {month}: keys {v['keys']:5,d}/{v['keys_expected']:5,d} ({pct:5.1f}%) | "
              f"days with every lead {v['days_complete']:2d}/{v['days_in_month']:2d}")'''
if old_print not in t:
    raise SystemExit("print block not found")
t = t.replace(old_print, new_print, 1)
cov.write_text(t, encoding="utf-8")
print("coverage checker now reports key completeness")

# ---- 2. gap audit: full post-sample range ----
gap = ROOT / "code" / "check_holdout_gaps.py"
g = gap.read_text(encoding="utf-8")
g = g.replace('FROZEN = ("2025-10", "2025-11", "2025-12", "2026-01", "2026-02")',
              'FROZEN = tuple(f"2026-{m:02d}" for m in range(1, 9)) + ("2025-10", "2025-11", "2025-12")')
gap.write_text(g, encoding="utf-8")
print("gap audit now covers the whole post-sample range")
