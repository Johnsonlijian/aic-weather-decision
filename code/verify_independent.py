"""Independent recomputation of the paper's headline numbers.

Why this exists
---------------
`submission_consistency_check.py` verifies that the manuscript agrees with the shipped
artefacts, but for skill and economic value it reads those artefacts rather than
recomputing them. That is an internal-consistency check, not an independent one, and it
is exactly the gap through which a row-alignment bug in the hold-out evaluator passed
unnoticed and reversed a published result.

This module recomputes the headline numbers from the frozen epoch table using its own
implementation of the estimator - equal-count binning with weighted pool-adjacent-
violators - written here rather than imported from `calibration.py`. It then compares
against the shipped artefacts and fails loudly on any disagreement. Two implementations
agreeing is much weaker evidence than a proof, but it does catch the class of defect
that motivated it: an estimator or an index that is silently wrong in one code path.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HORIZON = 12
LIMITS = (9.0, 12.0, 13.0, 16.5, 20.0)


# --------------------------------------------------------------------------- #
# Independent estimator: equal-count bins + weighted PAVA, from scratch
# --------------------------------------------------------------------------- #
def weighted_pava(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Pool adjacent violators, returning one pooled value per original bin.

    An earlier version of this function deleted pooled entries and then indexed the
    shortened array by original bin number, which silently sent every high bin to the
    last pooled value and produced nonsense skill for the rare-event limits. The group
    membership is tracked so the output always aligns with the input.
    """
    vals = [float(v) for v in values]
    wts = [float(w) for w in weights]
    groups = [[i] for i in range(len(values))]
    i = 0
    while i < len(vals) - 1:
        if vals[i] > vals[i + 1] + 1e-15:
            total = wts[i] + wts[i + 1]
            vals[i] = (vals[i] * wts[i] + vals[i + 1] * wts[i + 1]) / total
            wts[i] = total
            groups[i] = groups[i] + groups[i + 1]
            del vals[i + 1], wts[i + 1], groups[i + 1]
            i = max(0, i - 1)
        else:
            i += 1
    out = np.empty(len(values), dtype=float)
    for v, members in zip(vals, groups):
        for m in members:
            out[m] = v
    return out


def binned_probability(x_fit: np.ndarray, y_fit: np.ndarray, x_new: np.ndarray,
                       *, max_bins: int = 40, min_count: int = 30) -> np.ndarray:
    order = np.argsort(x_fit, kind="stable")
    xs, ys = x_fit[order], y_fit[order]
    n = len(xs)
    n_bins = int(min(max_bins, max(1, n // min_count)))
    edges = np.unique(np.quantile(xs, np.linspace(0.0, 1.0, n_bins + 1)))
    if edges.size < 2:
        return np.full_like(x_new, float(ys.mean()), dtype=float)
    idx = np.clip(np.searchsorted(edges, xs, side="right") - 1, 0, edges.size - 2)
    sums = np.bincount(idx, weights=ys, minlength=edges.size - 1)
    cnts = np.bincount(idx, minlength=edges.size - 1).astype(float)
    rates = np.divide(sums, np.maximum(cnts, 1.0))
    monotone = weighted_pava(rates, cnts)
    new_idx = np.clip(np.searchsorted(edges, x_new, side="right") - 1, 0, edges.size - 2)
    return monotone[new_idx]


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def bss(p: np.ndarray, y: np.ndarray, ref: np.ndarray) -> float:
    return float(1.0 - brier(p, y) / brier(ref, y))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--table", default="outputs/epochs_multi3.csv")
    parser.add_argument("--prefix", default="g5_block_v3")
    args = parser.parse_args()
    root: Path = args.root

    pred = f"block_max_L{HORIZON}"
    labels = [f"L{HORIZON}_thr{t}" for t in LIMITS]
    frame = pd.read_csv(root / args.table,
                        usecols=["station_id", "epoch", "split", pred] + labels)
    fit = frame[frame["split"] == "FIT"]
    test = frame[frame["split"] == "TEST"]
    x_fit_all = fit[pred].to_numpy(float)
    base_all = float(fit[labels[0]].mean())

    findings: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        findings.append((name, bool(ok), detail))
        print(f"{'AGREE ' if ok else 'DIFFER'}  {name}: {detail}")

    # ---- 1. Table 1 detector behaviour, straight from the table ----
    expected_detector = {9.0: (40.8, 47.1, 15.5, 30.9), 12.0: (18.8, 20.1, 8.0, 38.3),
                         13.0: (13.3, 14.5, 5.8, 42.7), 16.5: (3.8, 5.1, 1.6, 53.7),
                         20.0: (1.2, 1.1, 0.7, 53.8)}
    for limit in LIMITS:
        y = test[f"L{HORIZON}_thr{limit}"].to_numpy(float)
        claim = test[pred].to_numpy(float) > limit
        got = (round(100 * claim.mean(), 1), round(100 * y.mean(), 1),
               round(100 * (claim & (y == 0)).sum() / max((y == 0).sum(), 1), 1),
               round(100 * ((~claim) & (y == 1)).sum() / max((y == 1).sum(), 1), 1))
        check(f"Table 1 at {limit:g} m/s", got == expected_detector[limit],
              f"recomputed {got} vs printed {expected_detector[limit]}")

    # ---- 2. calibration skill, with the independent estimator ----
    shipped = json.loads((root / "outputs" / f"{args.prefix}_calibration.json")
                         .read_text(encoding="utf-8"))
    x_test = test[pred].to_numpy(float)
    for limit, row in zip(LIMITS, shipped):
        y_fit = fit[f"L{HORIZON}_thr{limit}"].to_numpy(float)
        y_test = test[f"L{HORIZON}_thr{limit}"].to_numpy(float)
        p = binned_probability(x_fit_all, y_fit, x_test)
        ref = np.full_like(y_test, float(y_fit.mean()))
        mine = round(bss(p, y_test, ref), 3)
        theirs = round(row["models"]["binned"]["test"]["skill_vs_climatology"], 3)
        check(f"skill vs climatology at {limit:g} m/s", abs(mine - theirs) <= 0.02,
              f"independent {mine:+.3f} vs shipped {theirs:+.3f}")

    # ---- 3. replay counting identities, recomputed from the table ----
    replay = json.loads((root / "outputs" / "g5_replay_v3.json").read_text(encoding="utf-8"))
    y12 = test[f"L{HORIZON}_thr12.0"].to_numpy(float)
    per_station = test.assign(_y=y12).groupby("station_id")["_y"].sum()
    check("replay positives reconcile with the table",
          int(per_station.sum()) == replay["test_positives"] == int(y12.sum()),
          f"{int(per_station.sum()):,} positives over {len(per_station)} stations")
    check("replay epoch count matches the table",
          int(len(test)) == replay["test_epochs"],
          f"{len(test):,} test epochs")

    # ---- 4. economic value, recomputed from probabilities ----
    rev = json.loads((root / "outputs" / f"{args.prefix}_economic_value.json")
                     .read_text(encoding="utf-8"))
    y_fit12 = fit[f"L{HORIZON}_thr12.0"].to_numpy(float)
    p12 = binned_probability(x_fit_all, y_fit12, x_test)
    row12 = next(r for r in rev if abs(r["threshold"] - 12.0) < 1e-9)
    r_mid = 0.2
    act = p12 >= r_mid
    expense = r_mid * act.mean() + float(((~act) & (y12 == 1)).mean())
    s = float(y12.mean())
    clim, perfect = min(r_mid, s), r_mid * s
    mine_rev = (clim - expense) / (clim - perfect)
    theirs_row = min(row12["curve"], key=lambda c: abs(c["cost_loss_ratio"] - r_mid))
    theirs_rule = theirs_row["rules"]["calibrated"]["relative_economic_value"]
    check("REV at C/L = 0.2 (calibrated rule)", abs(mine_rev - theirs_rule) <= 0.05,
          f"independent {mine_rev:+.3f} vs shipped {theirs_rule:+.3f}")

    bad = [f for f in findings if not f[1]]
    print(f"\n{len(findings) - len(bad)}/{len(findings)} independent checks agree")
    out = root / "outputs" / "g5_independent_recomputation.json"
    out.write_text(json.dumps(
        {"checks": [{"name": n, "agrees": ok, "detail": d} for n, ok, d in findings],
         "note": ("recomputed from the frozen epoch table with a locally implemented "
                  "estimator, not by importing calibration.py"),
         "all_agree": not bad}, ensure_ascii=False, indent=2), encoding="utf-8")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
