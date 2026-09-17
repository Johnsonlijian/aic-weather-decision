"""Uncertainty for the headline point estimates.

The review's objection is that 47,322 held-out rows are not 47,322 independent
observations: 12 h windows overlap every 6 h, neighbouring stations share synoptic
situations, and the 20 m/s event occurs in 18 episodes. This module reports the
headline numbers with intervals computed on the units that are actually
exchangeable:

* **time-block bootstrap** for skill and detector rates. Seven-day blocks are
  resampled with every station kept inside its block, so cross-station correlation
  and overlapping windows are preserved rather than assumed away.
* **station bootstrap** for the leave-one-station-out transfer median, where the
  exchangeable unit is the station.
* **episode count** as the honest denominator for the rare end.

Nothing here changes a point estimate; it states how much of it is signal.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from calibration import BinnedCalibrator, brier_skill_score

HORIZON = 12


def moving_block_ids(epochs: pd.Series, block_days: float) -> np.ndarray:
    origin = epochs.min()
    return ((epochs - origin).dt.total_seconds() / (86400.0 * block_days)).astype(int).to_numpy()


def block_bootstrap_metric(block: np.ndarray, statistic, draws: int,
                           rng: np.random.Generator, **arrays) -> dict:
    """Moving-block bootstrap over time blocks.

    Blocks are resampled whole and concatenated, so rows inside a block keep their
    order and their cross-station correlation. ``statistic`` receives the resampled
    arrays as keyword arguments and returns a scalar.
    """
    order = np.argsort(block, kind="stable")
    b = block[order]
    uniq, starts, counts = np.unique(b, return_index=True, return_counts=True)
    block_idx = [order[s:s + c] for s, c in zip(starts, counts)]
    n = len(block_idx)
    stats = np.empty(draws)
    for i in range(draws):
        pick = rng.integers(0, n, n)
        idx = np.concatenate([block_idx[j] for j in pick])
        stats[i] = statistic(**{k: v[idx] for k, v in arrays.items()})
    return {"estimate": float(statistic(**arrays)),
            "ci_low": float(np.percentile(stats, 2.5)),
            "ci_high": float(np.percentile(stats, 97.5)),
            "blocks": int(n), "draws": draws}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--table", default="outputs/epochs_multi3.csv")
    parser.add_argument("--prefix", default="g5_block_v3")
    parser.add_argument("--limit", type=float, default=12.0)
    parser.add_argument("--block-days", type=float, default=7.0)
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260916)
    args = parser.parse_args()
    root: Path = args.root
    rng = np.random.default_rng(args.seed)

    label = f"L{HORIZON}_thr{args.limit}"
    pred = f"block_max_L{HORIZON}"
    frame = pd.read_csv(root / args.table,
                        usecols=["station_id", "epoch", "split", pred, label, f"lead_L{HORIZON}"])
    frame["epoch"] = pd.to_datetime(frame["epoch"], utc=True)
    fit = frame[frame["split"] == "FIT"]
    test = frame[frame["split"] == "TEST"].sort_values("epoch").reset_index(drop=True)

    model = BinnedCalibrator().fit(fit[pred].to_numpy(float), fit[label].to_numpy(float))
    x = test[pred].to_numpy(float)
    y = test[label].to_numpy(float)
    p = model.predict(x)
    raw = (x > args.limit).astype(float)
    base = np.full_like(y, float(fit[label].mean()))
    block = moving_block_ids(test["epoch"], args.block_days)

    report: dict = {"limit": args.limit, "test_rows": int(len(y)),
                    "test_positives": int(y.sum()), "block_days": args.block_days,
                    "draws": args.draws, "window_hours": HORIZON}

    # ---- skill, resampling time blocks with stations kept together ----
    report["skill_vs_climatology"] = block_bootstrap_metric(
        block, lambda p, y, base: brier_skill_score(p, y, base), args.draws, rng,
        p=p, y=y, base=base)
    report["skill_vs_raw_threshold"] = block_bootstrap_metric(
        block, lambda p, y, raw: brier_skill_score(p, y, raw), args.draws, rng,
        p=p, y=y, raw=raw)

    # ---- detector rates on the rows where each rate is defined ----
    claim = x > args.limit
    pos = y == 1
    neg = y == 0
    report["miss_rate"] = block_bootstrap_metric(
        block[pos], lambda m: float(np.mean(m)), args.draws, rng,
        m=(~claim[pos]).astype(float))
    report["false_alarm_rate"] = block_bootstrap_metric(
        block[neg], lambda m: float(np.mean(m)), args.draws, rng,
        m=claim[neg].astype(float))

    # ---- station bootstrap for the transfer median ----
    spatial = json.loads((root / "outputs" / f"g5_spatial_transfer_{args.limit:g}ms.json")
                         .read_text(encoding="utf-8"))
    per_station = spatial["per_station"]
    transfer = np.array([v["transfer"]["skill_vs_climatology"] for v in per_station.values()
                         if "transfer" in v and "skill_vs_climatology" in v["transfer"]])
    station_stats = np.array([np.median(transfer[rng.integers(0, transfer.size, transfer.size)])
                              for _ in range(args.draws)])
    report["transfer_median_station_bootstrap"] = {
        "estimate": float(np.median(transfer)), "ci_low": float(np.percentile(station_stats, 2.5)),
        "ci_high": float(np.percentile(station_stats, 97.5)), "stations": int(transfer.size),
        "draws": args.draws, "negative_stations": int((transfer < 0).sum())}

    # ---- episode denominators for every documented limit ----
    cols = [c for c in pd.read_csv(root / args.table, nrows=0).columns
            if c.startswith(f"L{HORIZON}_thr")]
    extra = pd.read_csv(root / args.table, usecols=["epoch", "split"] + cols)
    extra["epoch"] = pd.to_datetime(extra["epoch"], utc=True)
    et = extra[extra["split"] == "TEST"].sort_values("epoch")
    episodes = {}
    for c in cols:
        lim = float(c.split("thr")[1])
        t = et.loc[et[c] == 1, "epoch"]
        if t.empty:
            episodes[f"{lim:g}"] = {"positives": 0, "episodes": 0}
            continue
        gaps = t.diff().dt.total_seconds().div(3600).dropna()
        episodes[f"{lim:g}"] = {"positives": int(len(t)), "episodes": int(1 + (gaps > 24).sum()),
                                "positives_per_episode": round(len(t) / (1 + (gaps > 24).sum()), 1)}
    report["episodes"] = episodes

    out = root / "outputs" / "g5_uncertainty.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    print(f"limit {args.limit} m/s | {report['test_rows']:,} rows, "
          f"{report['test_positives']:,} positives | {report['skill_vs_climatology']['blocks']} blocks")
    for k in ("skill_vs_climatology", "skill_vs_raw_threshold", "miss_rate", "false_alarm_rate"):
        v = report[k]
        print(f"  {k:24s} {v['estimate']:+.4f} [{v['ci_low']:+.4f}, {v['ci_high']:+.4f}]")
    v = report["transfer_median_station_bootstrap"]
    print(f"  {'transfer median':24s} {v['estimate']:+.4f} [{v['ci_low']:+.4f}, {v['ci_high']:+.4f}] "
          f"over {v['stations']} stations")
    print("  episodes:", {k: v["episodes"] for k, v in episodes.items()})


if __name__ == "__main__":
    main()
