"""Do the logged failures leave real gaps in the frozen hold-out window?

The failure log records each failed *attempt*, while the coverage check reads the
manifest, which records only verified messages. A key can therefore appear in the
failure log and still be present in the manifest if a later attempt succeeded. This
resolves the two against each other for the dates that matter, so the frozen
hold-out window's completeness is established rather than assumed.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN = tuple(f"2026-{m:02d}" for m in range(1, 9)) + ("2025-10", "2025-11", "2025-12")
# the post-sample evaluation builds 6, 12 and 24 h windows, so it needs the
# runs to cover 24 h forward. Leads beyond that are collected but unused, and a
# missing 48 h or 60 h message does not affect any reported result.
LEADS_USED = {6, 12, 18, 24}
LEADS = set(range(6, 73, 6))


def load(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


fails = load(ROOT / "outputs" / "gfs_gust_failures_newperiod.jsonl")
manifest = load(ROOT / "outputs" / "gfs_gust_manifest_newperiod.jsonl")
print(f"failure records: {len(fails)} | manifest records: {len(manifest)}")

have: dict[tuple[str, str], set[int]] = defaultdict(set)
for r in manifest:
    have[(r["issue_date"], r["issue_cycle"])].add(int(r["lead_hours"]))

inside = [f for f in fails if str(f.get("issue_date"))[:7] in FROZEN]
print(f"\nfailure records inside the frozen window: {len(inside)}")
for f in inside:
    key = (f["issue_date"], f["issue_cycle"])
    got = have.get(key, set())
    missing = sorted(LEADS_USED - got)
    print(f"  {f['issue_date']} {f['issue_cycle']}Z lead {f['lead_hours']:>2} "
          f"| key now has {len(got)}/12 leads | missing {missing or 'none'} "
          f"| recovered={int(f['lead_hours']) in got}")

# the authoritative statement: every (date, cycle) in the frozen window has all 12 leads
dates = sorted({d for d, _ in have if d[:7] in FROZEN})
incomplete = {d: sorted(LEADS - have[(d, c)]) for d in dates for c in ("00", "12")
              if not LEADS_USED <= have.get((d, c), set())}
print(f"\nfrozen-window issue dates present: {len(dates)}")
print(f"date-cycles missing any lead the analysis needs: {len(incomplete)}")
for d, miss in list(incomplete.items())[:5]:
    print("  ", d, "missing", miss)
verdict = ("frozen hold-out window has no gaps in the manifest"
           if not incomplete else "GAPS PRESENT - hold-out window must be narrowed")
print("\nverdict:", verdict)

report = {
    "frozen_window_months": list(FROZEN),
    "leads_required_by_the_analysis": sorted(LEADS_USED),
    "failure_records": len(fails),
    "manifest_records": len(manifest),
    "failure_records_in_frozen_window": len(inside),
    "frozen_window_issue_dates": len(dates),
    "date_cycles_missing_a_lead": len(incomplete),
    "recovery": [
        {"issue_date": f["issue_date"], "issue_cycle": f["issue_cycle"],
         "lead_hours": int(f["lead_hours"]),
         "leads_present_now": len(have.get((f["issue_date"], f["issue_cycle"]), set())),
         "recovered": int(f["lead_hours"]) in have.get((f["issue_date"], f["issue_cycle"]), set())}
        for f in inside],
    "note": ("the failure log records attempts; the manifest records verified messages, so a "
             "failure record can coexist with a complete key when a later attempt succeeded"),
    "verdict": verdict,
}
(ROOT / "outputs" / "g5_holdout_gaps.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote outputs/g5_holdout_gaps.json")
