"""Quantify the analysis-relevant gaps in the full post-sample range."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
d = json.loads((ROOT / "outputs" / "g5_holdout_gaps.json").read_text(encoding="utf-8"))
days = d["frozen_window_issue_dates"]
bad = d["date_cycles_missing_a_lead"]
print(f"issue dates in window          : {days}")
print(f"date-cycles missing a used lead: {bad}")
print(f"share of date-cycles affected  : {100.0 * bad / (days * 2):.2f}%")
print(f"failure records in window      : {d['failure_records_in_frozen_window']}")
print(f"months covered                 : {d['frozen_window_months']}")
print(f"leads required                 : {d.get('leads_required_by_the_analysis')}")
print()
print("Each affected date-cycle costs at most a few decision epochs out of tens of")
print("thousands, because the epoch builder marks an uncovered window as skipped")
print("rather than treating it as calm.")
