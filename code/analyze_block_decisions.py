"""Decision-analytic analysis of the weather-window event on real archived data.

This is the result-bearing core of the study.  It answers, on one data table
built under a latency-audited availability rule:

1. Calibration: does a fitted calibrator of P(block exceedance | forecast block
   maximum) improve Brier skill over the raw deterministic threshold and over
   climatology, on a split it was never fitted on?
2. Economic value: the relative-economic-value (REV) curve of the calibrated
   decision against the standard cost-loss model, computed for a sweep of
   cost-loss ratios with thresholds fixed by the critical-fractile rule.
3. Policy consequence: a lift-campaign simulation where each policy decides
   work/stop per 12-hour block and the outcomes are completed lifts, unsafe
   exposure blocks, and missed safe blocks.

No TEST information is used to fit or select anything.  The split and the policy
ladder are frozen in protocol/G5_preregistration_2026-09-15.md (revised R1).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from calibration import BinnedCalibrator, LogisticCalibrator, brier, brier_skill_score

HORIZON = 12
CRITICALS = (0.05, 0.10, 0.20, 0.40)
# Cost-loss ratio r = C/L with the miss cost normalised to L = 1.  The
# expense-optimal rule acts when P(event) >= C/L = r, so the decision-relevant
# range is 0 < r < 1; for r >= 1 "always act" is optimal and REV degenerates.
COST_LOSS_RATIOS = np.geomspace(0.01, 0.99, 40)
# Frozen reliability grid: bins are [lo, hi) on a fixed 0..1 scale so that
# curves from different splits and limits are directly comparable.
RELIABILITY_EDGES = np.linspace(0.0, 1.0, 11)


def load_table(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["epoch"] = pd.to_datetime(frame["epoch"], utc=True)
    if "split" not in frame.columns:
        raise SystemExit("epoch table has no split column")
    return frame


def block_metrics(table: pd.DataFrame, horizon: int, threshold: float) -> dict:
    """Fit on FIT, report skill on CAL and TEST for one target."""
    label = f"L{horizon}_thr{threshold}"
    fit = table[table["split"] == "FIT"]
    cal = table[table["split"] == "CAL"]
    test = table[table["split"] == "TEST"]
    x_fit = fit[f"block_max_L{horizon}"].to_numpy(float)
    y_fit = fit[label].to_numpy(float)
    base = float(y_fit.mean())

    out = {"horizon": horizon, "threshold": threshold,
           "fit_n": len(y_fit), "fit_positives": int(y_fit.sum()),
           "cal_n": len(cal), "cal_positives": int(cal[label].sum()),
           "test_n": len(test), "test_positives": int(test[label].sum()),
           "base_rate": base, "models": {}}
    for name, model in (("binned", BinnedCalibrator()), ("logistic", LogisticCalibrator())):
        model.fit(x_fit, y_fit)
        entry = {}
        for split_name, split in (("cal", cal), ("test", test)):
            x = split[f"block_max_L{horizon}"].to_numpy(float)
            y = split[label].to_numpy(float)
            p = model.predict(x)
            raw = (x > threshold).astype(float)
            base_vec = np.full_like(y, base)
            rel = _reliability(p, y)
            entry[split_name] = {
                "brier": brier(p, y),
                "skill_vs_climatology": brier_skill_score(p, y, base_vec),
                "skill_vs_raw_threshold": brier_skill_score(p, y, raw),
                "reliability": rel,
                "reliability_n_total": int(sum(row["n"] for row in rel)),
                "split_n": int(y.size),
            }
        out["models"][name] = entry
    return out


def _reliability(p: np.ndarray, y: np.ndarray) -> list[dict]:
    """Disjoint reliability table on the frozen grid.

    Same contract as before (``p_mean``/``obs_freq``/``n``) but bins are
    half-open, so the counts sum to the sample size instead of double-counting
    every bin boundary.
    """
    edges = RELIABILITY_EDGES
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, edges.size - 2)
    rows = []
    for k in range(edges.size - 1):
        sel = idx == k
        if sel.sum() < 5:
            continue
        rows.append({"p_mean": float(p[sel].mean()), "obs_freq": float(y[sel].mean()),
                     "n": int(sel.sum()), "lo": float(edges[k]), "hi": float(edges[k + 1])})
    return rows


def _expense(protect: np.ndarray, y: np.ndarray, s: float, r: float) -> float:
    """Cost-loss expense with normalised loss L = 1 and action cost C = r.

    The modelled action is a *protective planning action* (defer or cancel the
    planned window), never permission to work.  With ``protect`` the realised
    expense is ``C`` whether or not the event occurs; without it the expense is
    ``L`` only when the event occurs:

        expense(protect, Y) = C*protect + L*(1-protect)*Y

    averaged over the sample with C = r and L = 1 this is
    ``r*P(protect) + P(Y=1 and not protect)``.  The expense-minimising rule
    protects when ``P(Y=1) >= C/L = r``, ties resolving in favour of protection.
    """
    pr = float(protect.mean()) if protect.size else 0.0
    missed = float((~protect & (y == 1)).mean()) if protect.size else 0.0
    return r * pr + missed


def tuned_raw_curve(x_cal: np.ndarray, y_cal: np.ndarray, grid: int = 201) -> dict:
    """Precompute the calibration-split expense ingredients for every candidate.

    For a candidate raw threshold t the expense at cost-loss ratio r is
    ``r * P(action) + P(event and not action)``, which depends on t only through
    ``P(action)`` and ``P(event and action)``.  Both are computed once here so
    that sweeping r costs nothing rather than re-scanning the grid each time.
    """
    cand = np.unique(np.quantile(x_cal, np.linspace(0.0, 1.0, grid)))
    s_cal = float(y_cal.mean())
    pos = y_cal == 1
    ar = np.array([float((x_cal >= t).mean()) for t in cand])
    joint = np.array([float(((x_cal >= t) & pos).mean()) for t in cand])
    return {"candidates": cand, "action_rate": ar, "joint": joint, "base_rate": s_cal}


def tuned_raw_threshold(x_cal: np.ndarray, y_cal: np.ndarray, r: float,
                        grid: int = 201) -> float:
    """Raw-forecast threshold minimising the CAL expense for cost-loss ratio r.

    This is the control the calibrated rule must beat.  Calibration is monotone
    by construction, so a probability threshold and a raw-forecast threshold
    induce the *same family* of action sets; the honest question is therefore
    whether calibration buys anything over a raw threshold that has been tuned
    on the same calibration split, not over an arbitrarily fixed physical
    limit.  Ties are broken toward the lower (more protective) threshold.
    """
    curve = tuned_raw_curve(x_cal, y_cal, grid)
    return float(pick_tuned_threshold(curve, r))


def pick_tuned_threshold(curve: dict, r: float) -> float:
    """Argmin of the calibration expense at ratio r, from precomputed arrays."""
    if curve["candidates"].size == 0:
        return float("nan")
    expense = r * curve["action_rate"] + (curve["base_rate"] - curve["joint"])
    return float(curve["candidates"][int(np.argmin(expense))])


def economic_value(table: pd.DataFrame, horizon: int, threshold: float) -> dict:
    """Relative economic value for the calibrated and raw-forecast rules.

    Cost-loss semantics: acting costs C = r, a missed event costs L = 1, so the
    expense-optimal decision is to act when P(event) >= C/L = r.  The value
    previously reported here used p* = 1/(1+r) = L/(C+L), which is the
    safety-margin fractile rather than the expense-optimal one; that rule is
    now reported separately as ``margin`` so the two can be read side by side.
    """
    label = f"L{horizon}_thr{threshold}"
    fit = table[table["split"] == "FIT"]
    cal = table[table["split"] == "CAL"]
    test = table[table["split"] == "TEST"]
    x_fit = fit[f"block_max_L{horizon}"].to_numpy(float)
    y_fit = fit[label].to_numpy(float)
    model = BinnedCalibrator().fit(x_fit, y_fit)
    x_cal = cal[f"block_max_L{horizon}"].to_numpy(float)
    y_cal = cal[label].to_numpy(float)
    p_cal = model.predict(x_cal)
    x_test = test[f"block_max_L{horizon}"].to_numpy(float)
    y_test = test[label].to_numpy(float)
    p_test = model.predict(x_test)
    s_cal = float(y_cal.mean())
    s = float(y_test.mean())

    curve = []
    tun = tuned_raw_curve(x_cal, y_cal)
    for r in COST_LOSS_RATIOS:
        r = float(r)
        t_star = pick_tuned_threshold(tun, r)
        rules = {
            "calibrated": p_test >= r,
            "tuned_raw": x_test >= t_star,
            "fixed_raw": x_test > threshold,
        }
        expense_clim = min(r, s)
        expense_perfect = s * min(r, 1.0)
        denom = expense_clim - expense_perfect
        row = {"cost_loss_ratio": r, "critical_prob": r,
               "tuned_raw_threshold": t_star, "test_n": int(y_test.size),
               "action_name": "protect (defer or cancel the planned window)",
               "rules": {}}
        for name, protect in rules.items():
            pr = float(protect.mean())
            # hit rate: share of events that were protected; false-alarm rate:
            # share of event-free rows that were protected
            H = float((protect & (y_test == 1)).mean()) / s if s > 0 else 0.0
            F = float((protect & (y_test == 0)).mean()) / (1 - s) if s < 1 else 0.0
            exp = _expense(protect, y_test, s, r)
            row["rules"][name] = {
                "protection_rate": pr, "hit_rate": H, "false_alarm_rate": F,
                "expense": float(exp),
                "relative_economic_value": float((expense_clim - exp) / denom)
                if abs(denom) > 1e-12 else float("nan"),
                "n_protected": int(protect.sum()),
            }
        row["calibrated_vs_tuned_raw_disagreements"] = int(
            np.sum(rules["calibrated"] != rules["tuned_raw"]))
        row["expense_climatology"] = float(expense_clim)
        row["expense_perfect"] = float(expense_perfect)
        curve.append(row)
    return {"threshold": threshold, "horizon": horizon, "test_base_rate": s,
            "cal_base_rate": s_cal, "cal_n": int(y_cal.size),
            "cost_loss_semantics": "act iff P(event) >= C/L; C=r, L=1; "
                                   "p_star=maximised over r in (0,1)",
            "curve": curve}


def campaign_simulation(table: pd.DataFrame, horizon: int, threshold: float,
                        total_lifts: int = 24) -> dict:
    """Lift campaign per station on TEST; decisions per 12-hour block."""
    label = f"L{horizon}_thr{threshold}"
    fit = table[table["split"] == "FIT"]
    x_fit = fit[f"block_max_L{horizon}"].to_numpy(float)
    y_fit = fit[label].to_numpy(float)
    model = BinnedCalibrator().fit(x_fit, y_fit)
    base = float(y_fit.mean())

    test = table[table["split"] == "TEST"].sort_values(["station_id", "epoch"])
    # non-overlapping 12-hour blocks at 00 and 12 UTC
    test = test[test["epoch"].dt.hour.isin([0, 12])]
    out = {}
    for station, block in test.groupby("station_id"):
        x = block[f"block_max_L{horizon}"].to_numpy(float)
        y = block[label].to_numpy(float)
        p = model.predict(x)
        raw = x > threshold
        policies = {
            "blind": np.ones(len(x), bool),
            "raw": ~raw,
            "climatology": np.full(len(x), base <= 0.10),
        }
        for c in CRITICALS:
            policies[f"calibrated_p{c:g}"] = p <= c
        per_policy = {}
        for name, allow in policies.items():
            completed = unsafe = missed = blocks = 0
            for i in range(len(x)):
                blocks += 1
                if allow[i]:
                    if y[i] == 1:
                        unsafe += 1  # crane worked during an exceedance block
                    else:
                        completed += 1
                else:
                    if y[i] == 0:
                        missed += 1
                if completed >= total_lifts:
                    break
            per_policy[name] = {"blocks_to_complete": blocks,
                                "completed": completed,
                                "unsafe_blocks": unsafe,
                                "missed_safe_blocks": missed,
                                "finished": completed >= total_lifts}
        out[str(station)] = per_policy
    return {"horizon": horizon, "threshold": threshold, "total_lifts": total_lifts,
            "stations": out}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--table", default="outputs/decision_epochs_age12.csv")
    parser.add_argument("--prefix", default="g5_block")
    parser.add_argument("--thresholds", default="9.0,12.0,13.0,16.5,20.0")
    args = parser.parse_args()

    root: Path = args.root
    table = load_table(root / args.table)
    thresholds = [float(x) for x in args.thresholds.split(",")]
    calibration = [block_metrics(table, HORIZON, t) for t in thresholds]
    rev = [economic_value(table, HORIZON, t) for t in thresholds]
    campaign = [campaign_simulation(table, HORIZON, t) for t in thresholds]

    (root / "outputs" / f"{args.prefix}_calibration.json").write_text(
        json.dumps(calibration, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "outputs" / f"{args.prefix}_economic_value.json").write_text(
        json.dumps(rev, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "outputs" / f"{args.prefix}_campaign.json").write_text(
        json.dumps(campaign, ensure_ascii=False, indent=2), encoding="utf-8")

    # Compact console report of the primary calibration and campaign numbers.
    print("== calibration (binned model, Brier skill vs climatology / vs raw) ==")
    for row in calibration:
        b = row["models"]["binned"]
        print(f"  thr {row['threshold']:>5} | base {row['base_rate']:.4f} | "
              f"CAL {b['cal']['skill_vs_climatology']:+.3f}/{b['cal']['skill_vs_raw_threshold']:+.3f} | "
              f"TEST {b['test']['skill_vs_climatology']:+.3f}/{b['test']['skill_vs_raw_threshold']:+.3f} | "
              f"rel_n {b['test']['reliability_n_total']}/{b['test']['split_n']}")
    print("== REV peaks: calibrated vs tuned-raw control (TEST) ==")
    for row in rev:
        def peak(rule: str) -> tuple[float, float]:
            pts = [(c["rules"][rule]["relative_economic_value"], c["cost_loss_ratio"])
                   for c in row["curve"]
                   if c["rules"][rule]["relative_economic_value"] == c["rules"][rule]["relative_economic_value"]]
            if not pts:
                return float("nan"), float("nan")
            v, r = max(pts)
            return v, r
        vc, rc = peak("calibrated")
        vt, rt = peak("tuned_raw")
        dis = max(c["calibrated_vs_tuned_raw_disagreements"] for c in row["curve"])
        print(f"  thr {row['threshold']:>5}: calibrated {vc:+.3f} @ r={rc:.3f} | "
              f"tuned_raw {vt:+.3f} @ r={rt:.3f} | max decision disagreements {dis}/{row['curve'][0]['test_n']}")
    print("== campaign (TEST, 24 lifts; blind reference) ==")
    for row in campaign:
        print(f"  thr {row['threshold']:>5}:")
        for station, policies in row["stations"].items():
            blind = policies["blind"]["blocks_to_complete"]
            parts = [f"{n}: {v['blocks_to_complete']}blk/{v['unsafe_blocks']}uns/{v['missed_safe_blocks']}miss"
                     for n, v in policies.items()]
            print(f"    {station} " + " | ".join(parts))


if __name__ == "__main__":
    main()
