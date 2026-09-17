"""Re-parse the cached KNMI hourly responses with corrected field semantics.

The first collection decoded `R` as an amount in tenths of a millimetre
(`R_mm = R/10`) and renamed `DR` as `DR_deg`. Both are wrong: in the KNMI hourly
dataset `R` is a 0/1 occurrence flag, `RH` is the amount in 0.1 mm with -1
meaning "trace" (< 0.05 mm), and `DR` is the duration in 0.1 h.

This script re-derives every `data/raw/knmi_multi/<station>_<year>.csv` from the
retained raw `<station>_<year>.txt` response -- no network access -- and reports
the value ranges that decide the question on this archive, so the correction is
evidenced rather than assumed. The wind fields (FH/FX) and air temperature (T)
are unaffected by the change.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from download_inputs import parse_knmi


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--raw-dir", default="data/raw/knmi_multi")
    args = parser.parse_args()

    root: Path = args.root
    raw_dir = root / args.raw_dir
    files = sorted(raw_dir.glob("*.txt"))
    if not files:
        raise SystemExit(f"no cached raw responses in {raw_dir}")

    r_values: Counter = Counter()
    rh_values: Counter = Counter()
    dr_values: Counter = Counter()
    trace_hours = 0
    negative_rh_other: Counter = Counter()
    rows_total = 0
    written = []
    for path in files:
        text = path.read_text(encoding="utf-8-sig")
        rows = parse_knmi(text)
        rows_total += len(rows)
        for row in rows:
            if "R_occurrence" in row and row["R_occurrence"] is not None:
                r_values[row["R_occurrence"]] += 1
            if "RH_amount_mm" in row:
                if row["RH_trace"]:
                    trace_hours += 1
                elif row["RH_amount_mm"] is not None:
                    rh_values[round(row["RH_amount_mm"], 2)] += 1
            if "DR_hours" in row and row["DR_hours"] is not None:
                dr_values[round(row["DR_hours"], 2)] += 1
        dest = path.with_suffix(".csv")
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        written.append(dest.name)

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw_files": len(files),
        "csv_files_rewritten": len(written),
        "rows": rows_total,
        "R_occurrence_values": {str(k): v for k, v in sorted(r_values.items())},
        "R_is_binary_flag": set(r_values) <= {0, 1},
        "RH_amount_mm_distinct": len(rh_values),
        "RH_amount_mm_min": min(rh_values) if rh_values else None,
        "RH_amount_mm_max": max(rh_values) if rh_values else None,
        "RH_trace_hours": trace_hours,
        "RH_other_negative_codes": {str(k): v for k, v in negative_rh_other.items()},
        "DR_hours_distinct": len(dr_values),
        "DR_hours_min": min(dr_values) if dr_values else None,
        "DR_hours_max": max(dr_values) if dr_values else None,
        "note": ("R is a 0/1 occurrence flag; the previous R/10 'millimetre' total was "
                 "not an amount. RH is 0.1 mm with -1 meaning trace. DR is 0.1 h."),
    }
    out = root / "outputs" / "knmi_field_semantics_audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("created_at", "note")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
