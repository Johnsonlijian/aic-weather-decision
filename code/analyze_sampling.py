"""Mechanism experiment: does the forecast's *sampling interval* cause the detector failure?

The second review asked for a paired test that separates three candidate causes of
the fixed trigger's failure: the forecast's temporal sampling, its grid-to-station
representativeness, its systematic bias, and the placement of the cut. This module
isolates the first by holding everything else fixed.

Design
------
Same issue times, same stations, same forward windows, same observation labels, same
availability rule. The only difference is how densely the forecast is sampled inside
the window:

* ``6-hourly`` - the archive as originally collected (leads 6, 12, 18, ...), so a 12 h
  window is represented by two forecast values;
* ``3-hourly`` - the same runs plus a denser pull (leads 3, 9, 15, 21), so the same
  window is represented by four forecast values over the union.

Because both constructions are evaluated on the *same epochs* against the *same*
labels, every comparison is paired and the common weather cancels. The dense months
available are 2021-06 to 2022-05; they fall inside the fitting period, so this is a
controlled mechanism experiment and **not** a held-out evaluation - the split used
below is internal to the experiment (tune on the earlier months, evaluate on the
later ones) and the paper says so.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_block_decisions import pick_tuned_threshold, tuned_raw_curve
from calibration import BinnedCalibrator, brier_skill_score

H = 12
GUST_GRID = (7.0, 9.0, 11.0, 12.0, 13.0, 15.0, 18.0, 21.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--limit", type=float, default=12.0)
    parser.add_argument("--half", default="2022-01-01", help="tune before this date, evaluate after")
    args = parser.parse_args()
    root: Path = args.root
    label = f"L{H}_thr{args.limit}"

    cols = ["station_id", "epoch", f"block_max_L{H}", label, f"obs_max_gust_L{H}"]
    six = pd.read_csv(root / "outputs" / "epochs_samp6.csv", usecols=cols)
    three = pd.read_csv(root / "outputs" / "epochs_samp3.csv", usecols=cols)
    for d in (six, three):
        d["epoch"] = pd.to_datetime(d["epoch"], utc=True)
    six = six.rename(columns={f"block_max_L{H}": "fx"})
    three = three.rename(columns={f"block_max_L{H}": "fx3"})

    key = ["station_id", "epoch"]
    m = six[key + ["fx", label, f"obs_max_gust_L{H}"]].merge(
        three[key + ["fx3"]], on=key, how="inner")
    m = m.sort_values("epoch").reset_index(drop=True)
    y = m[label].to_numpy(float)
    split = m["epoch"] < pd.Timestamp(args.half, tz="UTC")
    print(f"paired epochs {len(m):,} | stations {m['station_id'].nunique()} | "
          f"tune {int(split.sum()):,} / evaluate {int((~split).sum()):,} | "
          f"event rate {y.mean():.4f}")

    report: dict = {
        "limit": args.limit, "paired_epochs": int(len(m)),
        "stations": int(m["station_id"].nunique()),
        "tune_rows": int(split.sum()), "evaluate_rows": int((~split).sum()),
        "event_rate": float(y.mean()),
        "tune_before": args.half,
        "note": ("controlled mechanism experiment inside the fitting period; both "
                 "samplings share issue times, stations, windows and labels"),
        "sampling_effect_on_the_forecast": {},
        "detector": {}, "skill": {}, "best_tuned_threshold": {},
    }

    # ---- 1. what denser sampling does to the forecast itself ----
    fx6, fx3 = m["fx"].to_numpy(float), m["fx3"].to_numpy(float)
    d = fx3 - fx6
    report["sampling_effect_on_the_forecast"] = {
        "mean_6h": float(fx6.mean()), "mean_3h": float(fx3.mean()),
        "mean_difference": float(d.mean()), "median_difference": float(np.median(d)),
        "share_where_denser_is_higher": float((d > 1e-9).mean()),
        "share_identical": float((np.abs(d) <= 1e-9).mean()),
        "max_increase": float(d.max()),
    }

    # ---- 2. detector rates under each sampling ----
    for name, fx in (("6-hourly", fx6), ("3-hourly", fx3)):
        claim = fx > args.limit
        report["detector"][name] = {
            "miss_rate": float(((~claim) & (y == 1)).sum() / max((y == 1).sum(), 1)),
            "false_alarm_rate": float((claim & (y == 0)).sum() / max((y == 0).sum(), 1)),
            "claim_rate": float(claim.mean()),
        }

    # ---- 3. best threshold per sampling, tuned on the earlier months ----
    yt, ye = y[split], y[~split]
    for name, fx in (("6-hourly", fx6), ("3-hourly", fx3)):
        xt, xe = fx[split], fx[~split]
        curve = tuned_raw_curve(xt, yt)
        best = {}
        for r in (0.05, 0.1, 0.2, 0.4):
            tau = pick_tuned_threshold(curve, r)
            prot_e = xe >= tau
            exp = r * prot_e.mean() + np.mean((~prot_e) & (ye == 1))
            best[f"r{r:g}"] = {"threshold": tau, "expense": float(exp)}
        # the detector's best achievable cut, scored by the true skill statistic
        # (hit rate minus false-alarm rate). Minimising miss+FA would be degenerate,
        # because always claiming gives zero misses.
        grid = np.unique(np.quantile(xt, np.linspace(0, 1, 201)))
        tss = [((xt > t) & (yt == 1)).sum() / max((yt == 1).sum(), 1)
               - ((xt > t) & (yt == 0)).sum() / max((yt == 0).sum(), 1) for t in grid]
        tau_min = float(grid[int(np.argmax(tss))])
        claim_e = xe > tau_min
        report["best_tuned_threshold"][name] = {
            "threshold_maximising_tss": tau_min,
            "tune_tss": float(max(tss)),
            "evaluate_miss_rate": float(((~claim_e) & (ye == 1)).sum() / max((ye == 1).sum(), 1)),
            "evaluate_false_alarm_rate": float((claim_e & (ye == 0)).sum() / max((ye == 0).sum(), 1)),
            "evaluate_tss": float(((claim_e) & (ye == 1)).sum() / max((ye == 1).sum(), 1)
                                  - ((claim_e) & (ye == 0)).sum() / max((ye == 0).sum(), 1)),
            "by_cost_ratio": best,
        }

    # ---- 4. calibration skill under each sampling ----
    for name, fx in (("6-hourly", fx6), ("3-hourly", fx3)):
        model = BinnedCalibrator().fit(fx[split], yt)
        p = model.predict(fx[~split])
        base = np.full_like(ye, float(yt.mean()))
        raw = (fx[~split] > args.limit).astype(float)
        report["skill"][name] = {
            "brier": float(np.mean((p - ye) ** 2)),
            "skill_vs_climatology": float(brier_skill_score(p, ye, base)),
            "skill_vs_its_own_raw_threshold": float(brier_skill_score(p, ye, raw)),
        }

    # ---- 5. paired comparison of the two samplings on the evaluation months ----
    paired = {}
    for r in (0.05, 0.1, 0.2, 0.4):
        entry = {}
        expenses = {}
        for name, fx in (("6-hourly", fx6), ("3-hourly", fx3)):
            curve = tuned_raw_curve(fx[split], yt)
            tau = pick_tuned_threshold(curve, r)
            prot = fx[~split] >= tau
            expenses[name] = r * prot.mean() + np.mean((~prot) & (ye == 1))
            entry[f"{name}_threshold"] = tau
        entry["expense_6h"] = float(expenses["6-hourly"])
        entry["expense_3h"] = float(expenses["3-hourly"])
        entry["difference_3h_minus_6h"] = float(expenses["3-hourly"] - expenses["6-hourly"])
        paired[f"r{r:g}"] = entry
    report["paired_cost_by_ratio"] = paired

    out = root / "outputs" / "g5_sampling_experiment.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    e = report["sampling_effect_on_the_forecast"]
    print(f"  forecast mean 6h {e['mean_6h']:.3f} -> 3h {e['mean_3h']:.3f} "
          f"(mean +{e['mean_difference']:.3f}, higher in {100 * e['share_where_denser_is_higher']:.1f}% of epochs, "
          f"identical in {100 * e['share_identical']:.1f}%)")
    for name in ("6-hourly", "3-hourly"):
        det = report["detector"][name]
        sk = report["skill"][name]
        print(f"  {name:9s} fixed limit: miss {det['miss_rate']:.3f} FA {det['false_alarm_rate']:.3f} "
              f"| calibrated skill vs clim {sk['skill_vs_climatology']:+.3f}")
    for name in ("6-hourly", "3-hourly"):
        b = report["best_tuned_threshold"][name]
        print(f"  {name:9s} best TSS threshold {b['threshold_maximising_tss']:.1f} m/s "
              f"(tune TSS {b['tune_tss']:.3f}) -> evaluate miss {b['evaluate_miss_rate']:.3f} "
              f"FA {b['evaluate_false_alarm_rate']:.3f} TSS {b['evaluate_tss']:.3f}")
    for k, v in paired.items():
        print(f"  {k}: expense 6h {v['expense_6h']:.5f} vs 3h {v['expense_3h']:.5f} "
              f"(3h - 6h {v['difference_3h_minus_6h']:+.5f})")


if __name__ == "__main__":
    main()
