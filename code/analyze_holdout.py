"""Post-sample evaluation on a period that did not exist when the model was frozen.

This is the strongest test the review asks for (gate 5): the calibrator is fitted
once on the 2021-2023 split, every decision rule is frozen - the calibrated
probability, the threshold tuned on the 2024 calibration split, and the operating
limit left alone - and nothing whatsoever is re-estimated on the new period. The
new period is then replayed exactly as the original one was, under the same
declared 4 h publication latency.

Reported: detector rates, Brier skill against the *frozen* climatology, and the
paired cost-loss comparison at matched ratios with a moving-block bootstrap. A
model that was overfitted to 2025 will show it here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_block_decisions import pick_tuned_threshold, tuned_raw_curve
from calibration import BinnedCalibrator, brier, brier_skill_score

HORIZON = 12


def moving_block_ids(epochs: pd.Series, block_days: float) -> np.ndarray:
    origin = epochs.min()
    return ((epochs - origin).dt.total_seconds() / (86400.0 * block_days)).astype(int).to_numpy()


def block_ci(block: np.ndarray, arrays: dict, statistic, draws: int,
             rng: np.random.Generator) -> dict:
    order = np.argsort(block, kind="stable")
    uniq, starts, counts = np.unique(block[order], return_index=True, return_counts=True)
    chunks = [order[s:s + c] for s, c in zip(starts, counts)]
    stats = np.empty(draws)
    for i in range(draws):
        idx = np.concatenate([chunks[j] for j in rng.integers(0, len(chunks), len(chunks))])
        stats[i] = statistic(**{k: v[idx] for k, v in arrays.items()})
    return {"estimate": float(statistic(**arrays)),
            "ci_low": float(np.percentile(stats, 2.5)),
            "ci_high": float(np.percentile(stats, 97.5)),
            "blocks": int(len(chunks)), "draws": draws}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--frozen-table", default="outputs/epochs_multi3.csv")
    parser.add_argument("--holdout-table", default="outputs/epochs_holdout.csv")
    parser.add_argument("--out", default="outputs/g5_holdout_evaluation.json",
                        help="output path; redirect this in tests so a synthetic\n"
                             "run can never overwrite the reported result")
    parser.add_argument("--limit", type=float, default=12.0)
    parser.add_argument("--block-days", type=float, default=7.0)
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260916)
    args = parser.parse_args()
    root: Path = args.root
    rng = np.random.default_rng(args.seed)

    label = f"L{HORIZON}_thr{args.limit}"
    pred = f"block_max_L{HORIZON}"
    cols = ["station_id", "epoch", "split", pred, label]
    frozen = pd.read_csv(root / args.frozen_table, usecols=cols)
    frozen["epoch"] = pd.to_datetime(frozen["epoch"], utc=True)
    hold = pd.read_csv(root / args.holdout_table, usecols=cols)
    hold["epoch"] = pd.to_datetime(hold["epoch"], utc=True)

    fit = frozen[frozen["split"] == "FIT"]
    cal = frozen[frozen["split"] == "CAL"]
    model = BinnedCalibrator().fit(fit[pred].to_numpy(float), fit[label].to_numpy(float))
    tuned_curve = tuned_raw_curve(cal[pred].to_numpy(float), cal[label].to_numpy(float))
    frozen_base_rate = float(fit[label].mean())

    # Sort once, then build every array from the sorted frame. An earlier version
    # wrote `x, y, p = hold[pred]..., hold[label]..., model.predict(x)` on one line
    # after sorting `hold`: Python evaluates the right-hand side before binding, so
    # `p` was predicted from the *pre-sort* row order while `x` and `y` came from the
    # sorted frame. That silently misaligned probabilities against labels and turned a
    # positive out-of-sample skill into a negative one.
    hold = hold.sort_values("epoch").reset_index(drop=True)
    x = hold[pred].to_numpy(float)
    y = hold[label].to_numpy(float)
    p = model.predict(x)
    block = moving_block_ids(hold["epoch"], args.block_days)
    base = np.full_like(y, frozen_base_rate)
    raw = (x > args.limit).astype(float)

    report: dict = {
        "limit": args.limit,
        "holdout_window": [str(hold["epoch"].min()), str(hold["epoch"].max())],
        "holdout_rows": int(len(y)), "holdout_positives": int(y.sum()),
        "holdout_stations": int(hold["station_id"].nunique()),
        "frozen_base_rate": frozen_base_rate,
        "holdout_base_rate": float(y.mean()),
        "note": ("model, threshold and operating limit frozen before the holdout period; "
                 "nothing re-estimated here"),
        "detector": {}, "skill": {}, "paired": {}, "episodes": {},
    }

    claim = x > args.limit
    for name, mask, value in (("miss_rate", y == 1, ~claim),
                              ("false_alarm_rate", y == 0, claim)):
        report["detector"][name] = block_ci(
            block[mask], {"v": value[mask].astype(float)},
            lambda v: float(np.mean(v)), args.draws, rng)

    report["skill"]["vs_frozen_climatology"] = block_ci(
        block, {"p": p, "y": y, "base": base},
        lambda p, y, base: brier_skill_score(p, y, base), args.draws, rng)
    report["skill"]["vs_frozen_base_rate_point"] = float(
        brier_skill_score(p, y, base))

    # episodes: how many independent situations the holdout actually contains
    pos_times = hold.loc[y == 1, "epoch"]
    if len(pos_times):
        gaps = pos_times.diff().dt.total_seconds().div(3600).dropna()
        report["episodes"] = {"positives": int(len(pos_times)),
                              "episodes": int(1 + (gaps > 24).sum())}

    # per-month skill: the failure is not necessarily uniform across the year, and
    # saying where it is concentrated matters more than a single annual number
    monthly = {}
    hold_m = hold.assign(month=hold["epoch"].dt.strftime("%Y-%m"))
    for month, mon in hold_m.groupby("month"):
        yb = mon[label].to_numpy(float)
        xb = mon[pred].to_numpy(float)
        pb = model.predict(xb)
        bb = np.full_like(yb, frozen_base_rate)
        monthly[month] = {
            "rows": int(len(yb)), "positives": int(yb.sum()),
            "event_rate": float(yb.mean()),
            "skill_vs_frozen_climatology": float(brier_skill_score(pb, yb, bb)),
            "miss_rate": float(((xb <= args.limit) & (yb == 1)).sum() / max((yb == 1).sum(), 1)),
        }
    report["monthly"] = monthly

    # Self-consistency: a Brier score is a mean over rows, so the pooled score must
    # equal the row-weighted average of the monthly scores, and the pooled skill must
    # follow from those two averages. If the probabilities are ever misaligned with
    # the labels - which is how a sign error slipped through once - the pooled number
    # and the monthly numbers disagree and this raises.
    n = np.array([v["rows"] for v in monthly.values()], dtype=float)
    bs_model = np.array([brier(model.predict(hold_m.loc[hold_m["month"] == m, pred]
                                             .to_numpy(float)),
                               hold_m.loc[hold_m["month"] == m, label].to_numpy(float))
                         for m in monthly], dtype=float)
    bs_clim = np.array([np.mean((np.full(int(rows), frozen_base_rate)
                                 - hold_m.loc[hold_m["month"] == m, label].to_numpy(float)) ** 2)
                        for m, rows in zip(monthly, n)], dtype=float)
    w_model = float((bs_model * n).sum() / n.sum())
    w_clim = float((bs_clim * n).sum() / n.sum())
    implied = 1.0 - w_model / w_clim if w_clim else float("nan")
    pooled = report["skill"]["vs_frozen_climatology"]["estimate"]
    if abs(pooled - implied) > 1e-6:
        raise AssertionError(
            f"pooled skill {pooled:+.6f} contradicts the row-weighted monthly skill "
            f"{implied:+.6f}: probabilities and labels are not aligned")
    report["skill_consistency"] = {"pooled": pooled, "from_monthly": implied,
                                   "agree": True}

    # paired cost-loss at matched ratios, threshold frozen from CAL
    paired = {}
    for r in (0.05, 0.1, 0.2, 0.4, 0.6):
        tau = pick_tuned_threshold(tuned_curve, r)
        rules = {"calibrated": p >= r, "tuned_raw": x >= tau, "fixed_limit": x > args.limit}
        row = {"tuned_threshold": tau}
        for name, protect in rules.items():
            row[name] = {"protect_rate": float(protect.mean()),
                         "expense": float(r * protect.mean()
                                          + np.mean((~protect) & (y == 1)))}
        row["tuned_minus_calibrated"] = row["tuned_raw"]["expense"] - row["calibrated"]["expense"]
        row["fixed_minus_calibrated"] = row["fixed_limit"]["expense"] - row["calibrated"]["expense"]
        diffs = r * rules["tuned_raw"].astype(float) + (~rules["tuned_raw"]) * y \
            - (r * rules["calibrated"].astype(float) + (~rules["calibrated"]) * y)
        row["tuned_minus_calibrated_ci"] = block_ci(
            block, {"d": diffs}, lambda d: float(np.mean(d)), args.draws, rng)
        paired[f"r{r:g}"] = row
    report["paired"] = paired

    out = root / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float),
                   encoding="utf-8")

    print(f"holdout {report['holdout_window'][0][:10]} -> {report['holdout_window'][1][:10]} | "
          f"{report['holdout_rows']:,} rows, {report['holdout_positives']:,} positives, "
          f"{report['holdout_stations']} stations")
    print(f"  frozen base rate {frozen_base_rate:.4f} | holdout base rate {y.mean():.4f}")
    for k, v in report["detector"].items():
        print(f"  {k:18s} {v['estimate']:+.4f} [{v['ci_low']:+.4f}, {v['ci_high']:+.4f}]")
    v = report["skill"]["vs_frozen_climatology"]
    print(f"  {'skill vs frozen':18s} {v['estimate']:+.4f} [{v['ci_low']:+.4f}, {v['ci_high']:+.4f}]")
    print("  episodes:", report["episodes"])
    for k, row in paired.items():
        ci = row["tuned_minus_calibrated_ci"]
        print(f"  {k}: tuned-cal {row['tuned_minus_calibrated']:+.4f} "
              f"[{ci['ci_low']:+.4f}, {ci['ci_high']:+.4f}] | "
              f"fixed-cal {row['fixed_minus_calibrated']:+.4f}")


if __name__ == "__main__":
    main()
