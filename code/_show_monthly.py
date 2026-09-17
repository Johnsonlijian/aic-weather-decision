"""Show the post-sample monthly decomposition."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
d = json.loads((ROOT / "outputs" / "g5_holdout_evaluation.json").read_text(encoding="utf-8"))
print("window", d["holdout_window"][0][:10], "->", d["holdout_window"][1][:10],
      "|", f"{d['holdout_rows']:,} rows,", f"{d['holdout_positives']:,} positives,",
      f"{d['episodes']['episodes']} episodes")
print(f"frozen base rate {d['frozen_base_rate']:.4f} | holdout {d['holdout_base_rate']:.4f}")
print(f"miss {d['detector']['miss_rate']['estimate']:.3f} "
      f"[{d['detector']['miss_rate']['ci_low']:.3f}, {d['detector']['miss_rate']['ci_high']:.3f}] | "
      f"FA {d['detector']['false_alarm_rate']['estimate']:.3f} "
      f"[{d['detector']['false_alarm_rate']['ci_low']:.3f}, {d['detector']['false_alarm_rate']['ci_high']:.3f}]")
s = d["skill"]["vs_frozen_climatology"]
print(f"skill vs frozen climatology {s['estimate']:+.3f} [{s['ci_low']:+.3f}, {s['ci_high']:+.3f}]")
print()
print("month     rows   event    skill    miss")
for m, v in sorted(d["monthly"].items()):
    print(f"  {m}  {v['rows']:6,d}  {v['event_rate']:.3f}  "
          f"{v['skill_vs_frozen_climatology']:+.3f}  {v['miss_rate']:.3f}")
neg = [m for m, v in d["monthly"].items() if v["skill_vs_frozen_climatology"] < 0]
print(f"\nmonths with negative skill: {len(neg)}/{len(d['monthly'])} -> {sorted(neg)}")
