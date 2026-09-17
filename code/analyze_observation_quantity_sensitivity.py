"""Observation-quantity sensitivity: FX (gust) vs FH (hourly mean) block events.

The crane limit's own averaging interval is undocumented, so the governing wind
quantity is not known.  This comparison bounds the answer by recomputing the block
calibration for the same thresholds using the hourly mean wind (FH) instead of the
preceding-hour maximum gust (FX).  If the decision-relevant skill conclusion is
similar under both quantities, the temporal-support ambiguity does not drive the
result; if not, the conclusion must be stated per-quantity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from calibration import BinnedCalibrator, brier_skill_score

HORIZON = 12
SPLITS = {"FIT": ("2021-06-01", "2023-12-31"), "CAL": ("2024-01-01", "2024-12-31"),
          "TEST": ("2025-01-01", "2025-09-30")}


def skill(table: pd.DataFrame, threshold: float) -> dict:
    label = f"L{HORIZON}_thr{threshold}"
    fit = table[table["split"] == "FIT"]
    cal = table[table["split"] == "CAL"]
    test = table[table["split"] == "TEST"]
    model = BinnedCalibrator().fit(fit[f"block_max_L{HORIZON}"].to_numpy(float),
                                   fit[label].to_numpy(float))
    base = float(fit[label].mean())
    out = {}
    for name, split in (("cal", cal), ("test", test)):
        x = split[f"block_max_L{HORIZON}"].to_numpy(float)
        y = split[label].to_numpy(float)
        p = model.predict(x)
        raw = (x > threshold).astype(float)
        base_vec = np.full_like(y, base)
        out[name] = {
            "skill_vs_climatology": brier_skill_score(p, y, base_vec),
            "skill_vs_raw_threshold": brier_skill_score(p, y, raw),
            "positives": int(y.sum()), "n": int(len(y)),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--thresholds", default="9.0,12.0,13.0,16.5,20.0")
    args = parser.parse_args()
    root: Path = args.root

    def load(path):
        frame = pd.read_csv(root / path)
        frame["epoch"] = pd.to_datetime(frame["epoch"], utc=True)
        frame["split"] = "OTHER"
        for name, (lo, hi) in SPLITS.items():
            lo_ts, hi_ts = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1)
            frame.loc[(frame["epoch"] >= lo_ts) & (frame["epoch"] < hi_ts), "split"] = name
        return frame

    fx = load("outputs/decision_epochs_age12_fx.csv")
    fh = load("outputs/decision_epochs_age12_fh.csv")
    thresholds = [float(x) for x in args.thresholds.split(",")]
    report = {"horizon": HORIZON, "thresholds": []}
    for t in thresholds:
        fx_skill = skill(fx, t)
        fh_skill = skill(fh, t)
        report["thresholds"].append({
            "threshold": t,
            "fx_test": fx_skill["test"], "fx_cal": fx_skill["cal"],
            "fh_test": fh_skill["test"], "fh_cal": fh_skill["cal"],
        })
    (root / "outputs" / "g5_observation_quantity_sensitivity.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("threshold | FX test (vs clim / vs raw) | FH test (vs clim / vs raw)")
    for r in report["thresholds"]:
        fx, fh = r["fx_test"], r["fh_test"]
        print(f"  {r['threshold']:>5} | {fx['skill_vs_climatology']:+.3f} / {fx['skill_vs_raw_threshold']:+.3f} "
              f"| {fh['skill_vs_climatology']:+.3f} / {fh['skill_vs_raw_threshold']:+.3f} "
              f"(n={fx['n']}, pos FX {fx['positives']} / FH {fh['positives']})")


if __name__ == "__main__":
    main()
