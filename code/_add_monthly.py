"""One-shot: add a per-month breakdown to the hold-out evaluation."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / "code" / "analyze_holdout.py"
text = target.read_text(encoding="utf-8")

anchor = '''    # paired cost-loss at matched ratios, threshold frozen from CAL'''
addition = '''    # per-month skill: the failure is not necessarily uniform across the year, and
    # saying where it is concentrated matters more than a single annual number
    monthly = {}
    hold_m = hold.assign(month=hold["epoch"].dt.strftime("%Y-%m"))
    for month, block in hold_m.groupby("month"):
        yb = block[label].to_numpy(float)
        xb = block[pred].to_numpy(float)
        pb = model.predict(xb)
        bb = np.full_like(yb, frozen_base_rate)
        monthly[month] = {
            "rows": int(len(yb)), "positives": int(yb.sum()),
            "event_rate": float(yb.mean()),
            "skill_vs_frozen_climatology": float(brier_skill_score(pb, yb, bb)),
            "miss_rate": float(((xb <= args.limit) & (yb == 1)).sum() / max((yb == 1).sum(), 1)),
        }
    report["monthly"] = monthly

'''

if "report[\"monthly\"]" in text:
    print("already present")
else:
    if anchor not in text:
        raise SystemExit("anchor not found")
    text = text.replace(anchor, addition + anchor, 1)
    target.write_text(text, encoding="utf-8")
    print("added per-month breakdown")
