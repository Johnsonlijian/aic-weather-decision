"""Per-station decision replay with reconciled counts and paired cost-loss comparison.

Written in response to the second review, which found two things:

1. The published replay figure could not be reconciled with Table 1. It replayed
   only 00/12 UTC epochs and stopped each station after 24 completed windows, so
   the counts did not add up to the 9,518 held-out positives. This module replays
   every held-out decision epoch and asserts the counting identities.
2. Peak-versus-peak comparison is not a like-for-like comparison, because each
   cost-loss ratio describes a different user. This module reports paired
   differences on identical epochs at the *same* ratio, with a moving-block
   bootstrap that keeps each time block's stations together so that weather
   correlation is not treated as independence.

Action semantics: `protect = True` is the protective planning action (defer or
cancel the planned window). It never means permission to work. Realised expense
is `C*protect + L*(1-protect)*event` with `C = r`, `L = 1`.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_block_decisions import (COST_LOSS_RATIOS, pick_tuned_threshold,
                                     tuned_raw_curve)
from calibration import BinnedCalibrator

HORIZON = 12


def induced_threshold(model: BinnedCalibrator, r: float) -> float:
    """Raw forecast value at which the fitted calibration map first reaches r.

    Inverting a non-decreasing map: `{x : f(x) >= r}` is an upper-level set of x,
    so the same action set is produced by the raw rule `x >= induced`. This is
    an implementation check on the calibration, distinct from the independently
    tuned threshold that minimises empirical expense.
    """
    edges, probs = model.bin_edges, model.bin_prob
    hit = np.nonzero(probs >= r)[0]
    if hit.size == 0:
        return float("inf")
    return float(edges[int(hit[0])])


def moving_block_ids(epochs: pd.Series, block_days: float) -> np.ndarray:
    origin = epochs.min()
    return ((epochs - origin).dt.total_seconds() / (86400.0 * block_days)).astype(int).to_numpy()


def bootstrap_paired(diff: np.ndarray, block: np.ndarray, rng: np.random.Generator,
                     draws: int = 2000) -> dict:
    """Moving-block bootstrap over time blocks of a paired per-row difference."""
    order = np.argsort(block, kind="stable")
    diff_sorted, block_sorted = diff[order], block[order]
    uniq, starts, counts = np.unique(block_sorted, return_index=True, return_counts=True)
    slices = [diff_sorted[s:s + c] for s, c in zip(starts, counts)]
    n_blocks = len(slices)
    stats = np.empty(draws)
    for i in range(draws):
        pick = rng.integers(0, n_blocks, n_blocks)
        stats[i] = np.concatenate([slices[j] for j in pick]).mean()
    return {"mean": float(diff.mean()),
            "ci_low": float(np.percentile(stats, 2.5)),
            "ci_high": float(np.percentile(stats, 97.5)),
            "n_blocks": int(n_blocks),
            "draws": draws,
            "share_draws_positive": float((stats > 0).mean())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--table", default="outputs/epochs_multi3.csv")
    parser.add_argument("--out-prefix", default="g5_replay_v3")
    parser.add_argument("--limit", type=float, default=12.0)
    parser.add_argument("--ratios", default="0.05,0.1,0.2,0.4,0.6")
    parser.add_argument("--block-days", type=float, default=7.0)
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260916)
    args = parser.parse_args()
    root: Path = args.root
    label = f"L{HORIZON}_thr{args.limit}"
    pred = f"block_max_L{HORIZON}"

    frame = pd.read_csv(root / args.table,
                        usecols=["station_id", "epoch", "split", pred, label, f"lead_L{HORIZON}"])
    frame["epoch"] = pd.to_datetime(frame["epoch"], utc=True)
    fit = frame[frame["split"] == "FIT"]
    cal = frame[frame["split"] == "CAL"]
    test = frame[frame["split"] == "TEST"].sort_values(["epoch", "station_id"]).reset_index(drop=True)

    model = BinnedCalibrator().fit(fit[pred].to_numpy(float), fit[label].to_numpy(float))
    tun = tuned_raw_curve(cal[pred].to_numpy(float), cal[label].to_numpy(float))

    x = test[pred].to_numpy(float)
    y = test[label].to_numpy(float)
    p = model.predict(x)
    n_test, n_pos = int(x.size), int(y.sum())

    ratios = [float(v) for v in args.ratios.split(",")]
    rng = np.random.default_rng(args.seed)
    block = moving_block_ids(test["epoch"], args.block_days)

    report: dict = {
        "limit": args.limit, "horizon": HORIZON,
        "action_name": "protect (defer or cancel the planned window); never permission to work",
        "expense_model": "C*protect + L*(1-protect)*event, C=r, L=1",
        "test_epochs": n_test, "test_positives": n_pos,
        "stations": int(test["station_id"].nunique()),
        "block_days": args.block_days, "bootstrap_draws": args.draws,
        "policies": {}, "paired": {}, "induced_threshold_check": {},
    }

    # ---------- policies, full sample, no truncation ----------
    policies = {
        "blind_work": np.zeros(n_test, bool),
        "always_protect": np.ones(n_test, bool),
        "fixed_limit": x > args.limit,
    }
    for r in ratios:
        policies[f"calibrated_r{r:g}"] = p >= r
        policies[f"tuned_raw_r{r:g}"] = x >= pick_tuned_threshold(tun, r)

    rows = []
    for name, protect in policies.items():
        per_station = {}
        for station, idx in test.groupby("station_id").indices.items():
            ys, ps = y[idx], protect[idx]
            per_station[str(station)] = {
                "n_test": int(len(idx)),
                "n_positive": int(ys.sum()),
                "n_protected": int(ps.sum()),
                "n_protected_positive": int((ps & (ys == 1)).sum()),
                "n_unprotected_positive": int((~ps & (ys == 1)).sum()),
                "n_protected_negative": int((ps & (ys == 0)).sum()),
            }
        report["policies"][name] = {
            "n_protected": int(protect.sum()),
            "n_protected_positive": int((protect & (y == 1)).sum()),
            "n_unprotected_positive": int((~protect & (y == 1)).sum()),
            "per_station": per_station,
        }
        for station, v in per_station.items():
            rows.append({"policy": name, "station_id": station, **v})

    # counting identities demanded by the review
    checks = {
        "sum_station_positives_equals_test_positives":
            sum(v["n_positive"] for v in report["policies"]["blind_work"]["per_station"].values()) == n_pos,
        "blind_work_unprotected_positive_equals_positives":
            report["policies"]["blind_work"]["n_unprotected_positive"] == n_pos,
        "blind_work_protects_nothing": report["policies"]["blind_work"]["n_protected"] == 0,
        "always_protect_covers_every_epoch":
            report["policies"]["always_protect"]["n_protected"] == n_test,
        "every_policy_partitions_the_sample": all(
            v["n_protected_positive"] + v["n_unprotected_positive"] == v["n_positive"]
            and v["n_protected_positive"] + v["n_protected_negative"] == v["n_protected"]
            for pol in report["policies"].values() for v in pol["per_station"].values()),
    }
    report["count_checks"] = checks

    # ---------- induced-threshold implementation check ----------
    for r in ratios:
        t_ind = induced_threshold(model, r)
        same_test = bool(np.array_equal(p >= r, x >= t_ind))
        xc, yc = cal[pred].to_numpy(float), cal[label].to_numpy(float)
        same_cal = bool(np.array_equal(model.predict(xc) >= r, xc >= t_ind))
        report["induced_threshold_check"][f"r{r:g}"] = {
            "induced_threshold": t_ind,
            "reproduces_calibrated_action_set_on_test": same_test,
            "reproduces_calibrated_action_set_on_cal": same_cal,
            "independently_tuned_threshold": pick_tuned_threshold(tun, r),
        }

    # ---------- paired same-ratio comparison with block bootstrap ----------
    def row_loss(protect: np.ndarray, r: float) -> np.ndarray:
        return r * protect.astype(float) + (~protect) * y

    for r in ratios:
        pc = policies[f"calibrated_r{r:g}"]
        pt = policies[f"tuned_raw_r{r:g}"]
        pf = policies["fixed_limit"]
        entry = {
            "n_protected_calibrated": int(pc.sum()),
            "n_protected_tuned_raw": int(pt.sum()),
            "n_protected_fixed_limit": int(pf.sum()),
            "action_disagreements_cal_vs_tuned": int((pc != pt).sum()),
            "expense_calibrated": float(row_loss(pc, r).mean()),
            "expense_tuned_raw": float(row_loss(pt, r).mean()),
            "expense_fixed_limit": float(row_loss(pf, r).mean()),
        }
        for name, pa, pb in (("tuned_minus_calibrated", pt, pc),
                             ("fixed_minus_calibrated", pf, pc),
                             ("fixed_minus_tuned_raw", pf, pt)):
            diff = row_loss(pa, r) - row_loss(pb, r)
            entry[name] = bootstrap_paired(diff, block, rng, args.draws)
            # per-station paired difference: how often is each rule cheaper?
            ds = []
            for station, idx in test.groupby("station_id").indices.items():
                ds.append(float(row_loss(pa, r)[idx].mean() - row_loss(pb, r)[idx].mean()))
            ds = np.array(ds)
            entry[name]["stations_first_cheaper"] = int((ds < 0).sum())
            entry[name]["stations_second_cheaper"] = int((ds > 0).sum())
            entry[name]["stations_tied"] = int((ds == 0).sum())
            entry[name]["station_median_difference"] = float(np.median(ds))
            entry[name]["difference_sign"] = ("negative = first rule cheaper"
                                              if name != "tuned_minus_calibrated"
                                              else "negative = tuned raw cheaper")
        report["paired"][f"r{r:g}"] = entry

    # ---------- rare-event clustering ----------
    # 47,322 decision epochs are not 47,322 independent weather events: count the
    # distinct exceedance episodes, defined as positive epochs separated by more
    # than 24 h without an exceedance.
    epi = {}
    labels = [c for c in pd.read_csv(root / args.table, nrows=0).columns
              if c.startswith(f"L{HORIZON}_thr")]
    extra = pd.read_csv(root / args.table, usecols=["epoch", "split"] + labels)
    extra["epoch"] = pd.to_datetime(extra["epoch"], utc=True)
    et = extra[extra["split"] == "TEST"].sort_values("epoch").reset_index(drop=True)
    for lab in labels:
        limit = float(lab.split("thr")[1])
        pv = et[lab].to_numpy() == 1
        pos_times = et.loc[pv, "epoch"]
        if pos_times.empty:
            epi[f"{limit:g}"] = {"positive_epochs": 0, "episodes_gap24h": 0,
                                 "positive_epochs_per_episode": None}
            continue
        gaps_h = pos_times.diff().dt.total_seconds().div(3600.0).dropna()
        episodes = 1 + int((gaps_h > 24).sum())
        epi[f"{limit:g}"] = {
            "positive_epochs": int(pv.sum()),
            "episodes_gap24h": episodes,
            "positive_epochs_per_episode": round(float(pv.sum()) / episodes, 1),
            "share_of_test_rows_that_are_positive_epochs": round(float(pv.mean()), 4),
        }
    report["rare_event_clustering"] = epi

    out = root / "outputs" / f"{args.out_prefix}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(root / "outputs" / f"{args.out_prefix}_count_table.csv", index=False)

    print(f"limit {args.limit} m/s | stations {report['stations']} | test epochs {n_test:,} "
          f"| positives {n_pos:,}")
    print("count checks:", "ALL PASS" if all(checks.values()) else checks)
    print("induced threshold reproduces the calibrated action set:",
          all(v["reproduces_calibrated_action_set_on_test"]
              for v in report["induced_threshold_check"].values()))
    for r in ratios:
        e = report["paired"][f"r{r:g}"]
        print(f"  r={r:<4g} | protect: cal {e['n_protected_calibrated']:,} / "
              f"tuned {e['n_protected_tuned_raw']:,} / fixed {e['n_protected_fixed_limit']:,} | "
              f"E tuned-cal {e['tuned_minus_calibrated']['mean']:+.5f} "
              f"[{e['tuned_minus_calibrated']['ci_low']:+.5f},"
              f"{e['tuned_minus_calibrated']['ci_high']:+.5f}]")
    print("rare-event clustering:", epi)


if __name__ == "__main__":
    main()
