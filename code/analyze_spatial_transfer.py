"""Spatial transfer and lead stratification of the calibrated window event.

Two questions a reviewer will ask of a three-station result:

1. Does a calibrator fitted on some sites work on sites it has never seen?
   (pooled transfer vs site-specific calibration vs the raw threshold)
2. How does the skill decay with forecast lead?

Both are answered on the expanded 46-station epoch table, with the same
available-information rule used everywhere else in the study.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from calibration import BinnedCalibrator, brier_skill_score

HORIZON = 12
LIMITS = (9.0, 12.0, 13.0, 16.5, 20.0)


def skill(p: np.ndarray, y: np.ndarray, ref: np.ndarray | None = None) -> dict:
    out = {"n": int(len(y)), "positives": int(y.sum())}
    if len(y) == 0 or y.sum() == 0:
        out["not_estimable"] = True
        return out
    base = np.full_like(y, y.mean())
    out["brier"] = float(np.mean((p - y) ** 2))
    out["skill_vs_climatology"] = brier_skill_score(p, y, base)
    if ref is not None:
        out["skill_vs_raw"] = brier_skill_score(p, y, ref)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--table", default="outputs/epochs_multi.csv")
    parser.add_argument("--limit", type=float, default=12.0)
    args = parser.parse_args()

    root: Path = args.root
    frame = pd.read_csv(root / args.table)
    frame["epoch"] = pd.to_datetime(frame["epoch"], utc=True)
    label = f"L{HORIZON}_thr{args.limit}"
    pred = f"block_max_L{HORIZON}"
    fit = frame[frame["split"] == "FIT"]
    cal = frame[frame["split"] == "CAL"]
    test = frame[frame["split"] == "TEST"]

    report: dict = {"limit": args.limit, "horizon": HORIZON,
                    "stations_total": int(frame["station_id"].nunique()),
                    "rows": int(len(frame))}

    # ---- 1. pooled calibration vs raw threshold ----
    pooled = BinnedCalibrator().fit(fit[pred].to_numpy(float), fit[label].to_numpy(float))
    x_test = test[pred].to_numpy(float)
    y_test = test[label].to_numpy(float)
    p_pooled = pooled.predict(x_test)
    raw = (x_test > args.limit).astype(float)
    report["pooled"] = {"test": skill(p_pooled, y_test, raw)}

    # ---- 2. spatial holdout: leave-one-station-out on the held-out split ----
    per_station = {}
    for station, block in test.groupby("station_id"):
        train = fit[fit["station_id"] != station]
        own = fit[fit["station_id"] == station]
        x = block[pred].to_numpy(float)
        y = block[label].to_numpy(float)
        entry = {"n": int(len(block)), "positives": int(y.sum())}
        # (a) transfer: fit without this station
        if y.sum() > 0 and len(train) > 0:
            model_t = BinnedCalibrator().fit(train[pred].to_numpy(float), train[label].to_numpy(float))
            entry["transfer"] = skill(model_t.predict(x), y, (x > args.limit).astype(float))
        # (b) site-specific: fit on this station's own history
        if y.sum() > 0 and own[label].sum() > 0:
            model_s = BinnedCalibrator().fit(own[pred].to_numpy(float), own[label].to_numpy(float))
            entry["site_specific"] = skill(model_s.predict(x), y, None)
        # (c) raw threshold baseline
        entry["raw_threshold"] = skill((x > args.limit).astype(float), y, None)
        per_station[str(station)] = entry
    report["per_station"] = per_station

    transfer_skills = [v["transfer"]["skill_vs_climatology"] for v in per_station.values()
                       if "transfer" in v and "skill_vs_climatology" in v["transfer"]]
    site_skills = [v["site_specific"]["skill_vs_climatology"] for v in per_station.values()
                   if "site_specific" in v and "skill_vs_climatology" in v["site_specific"]]
    raw_skills = [v["raw_threshold"]["skill_vs_climatology"] for v in per_station.values()
                  if "skill_vs_climatology" in v["raw_threshold"]]
    report["summary"] = {
        "stations_evaluated": len(per_station),
        "transfer_median_skill": float(np.median(transfer_skills)) if transfer_skills else None,
        "transfer_min_skill": float(np.min(transfer_skills)) if transfer_skills else None,
        "transfer_negative_stations": int(sum(1 for s in transfer_skills if s < 0)),
        "site_specific_median_skill": float(np.median(site_skills)) if site_skills else None,
        "raw_threshold_median_skill": float(np.median(raw_skills)) if raw_skills else None,
    }

    # ---- 3. decision-value transfer: does calibration beat a tuned raw threshold? ----
    # A monotone calibrator cannot reach an action set that some raw threshold could
    # not also reach, so the informative transfer question is whether the transported
    # probability table makes *better decisions* than a raw threshold tuned on the
    # other stations for the same cost ratio. Expense uses C = r, L = 1, so acting
    # costs r whether or not the event occurs and a missed event costs 1:
    #     expense = r * P(action) + P(event and not action).
    ratios = (0.1, 0.2, 0.4)
    x_cal_all = cal[pred].to_numpy(float)
    cand = np.unique(np.quantile(x_cal_all, np.linspace(0.0, 1.0, 201)))
    per_station_cal = {}
    for station, sc in cal.groupby("station_id"):
        xc = sc[pred].to_numpy(float)
        yc = sc[label].to_numpy(float)
        pos = yc == 1
        per_station_cal[str(station)] = {
            "n": int(len(yc)), "positives": int(pos.sum()),
            "ge": np.array([int((xc >= t).sum()) for t in cand]),
            "ge_pos": np.array([int(((xc >= t) & pos).sum()) for t in cand]),
        }

    def tuned_on_others(station: str, r: float) -> float | None:
        """Raw threshold minimising the CAL expense over every station but this one."""
        others = [v for k, v in per_station_cal.items() if k != station]
        n_tot = sum(v["n"] for v in others)
        p_tot = sum(v["positives"] for v in others)
        if not others or n_tot <= 0:
            return None
        ge = np.sum([v["ge"] for v in others], axis=0)
        gp = np.sum([v["ge_pos"] for v in others], axis=0)
        expense = r * (ge / n_tot) + (p_tot - gp) / n_tot
        return float(cand[int(np.argmin(expense))])

    def expense_of(act: np.ndarray, y: np.ndarray, r: float) -> float:
        return float(r * act.mean() + np.mean((~act) & (y == 1)))

    value_transfer = {}
    for station, block in test.groupby("station_id"):
        x = block[pred].to_numpy(float)
        y = block[label].to_numpy(float)
        if not len(y):
            continue
        s_obs = float(y.mean())
        train = fit[fit["station_id"] != station]
        model_t = (BinnedCalibrator().fit(train[pred].to_numpy(float), train[label].to_numpy(float))
                   if len(train) else None)
        entry = {}
        for r in ratios:
            e_clim, e_perfect = min(r, s_obs), r * s_obs
            denom = e_clim - e_perfect
            rules = {"climatology_expense": e_clim, "perfect_expense": e_perfect}
            if model_t is not None:
                rules["calibrated"] = expense_of(model_t.predict(x) >= r, y, r)
            t_other = tuned_on_others(str(station), r)
            if t_other is not None:
                rules["tuned_raw_transported"] = expense_of(x >= t_other, y, r)
                rules["tuned_raw_transported_threshold"] = t_other
            rules["fixed_limit"] = expense_of(x > args.limit, y, r)
            if denom > 0:
                for k in ("calibrated", "tuned_raw_transported", "fixed_limit"):
                    if k in rules:
                        rules[f"rev_{k}"] = (e_clim - rules[k]) / denom
            entry[f"r{r:g}"] = rules
        value_transfer[str(station)] = entry
    report["value_transfer"] = value_transfer

    value_summary = {}
    for r in ratios:
        key = f"r{r:g}"
        block = {k: v[key] for k, v in value_transfer.items()}
        row: dict = {}
        for rule in ("calibrated", "tuned_raw_transported", "fixed_limit"):
            revs = [b[f"rev_{rule}"] for b in block.values() if f"rev_{rule}" in b]
            if revs:
                row[rule] = {"median_rev": float(np.median(revs)),
                             "negative_stations": int(sum(1 for v in revs if v < 0)),
                             "n": len(revs)}
        diffs = [b["rev_calibrated"] - b["rev_tuned_raw_transported"] for b in block.values()
                 if "rev_calibrated" in b and "rev_tuned_raw_transported" in b]
        if diffs:
            row["calibrated_minus_tuned_raw"] = {
                "median_rev_gain": float(np.median(diffs)),
                "stations_calibrated_better": int(sum(1 for d in diffs if d > 1e-9)),
                "stations_tuned_raw_better": int(sum(1 for d in diffs if d < -1e-9)),
                "n": len(diffs),
            }
        value_summary[key] = row
    report["value_transfer_summary"] = value_summary

    # ---- 4. lead stratification ----
    lead_col = f"lead_L{HORIZON}"
    by_lead = {}
    if lead_col in frame.columns:
        for lead, block in frame[frame["split"] == "TEST"].groupby(lead_col):
            y = block[label].to_numpy(float)
            if y.sum() == 0:
                by_lead[str(int(lead))] = {"n": int(len(block)), "positives": 0,
                                           "not_estimable": True}
                continue
            model = BinnedCalibrator().fit(fit[pred].to_numpy(float), fit[label].to_numpy(float))
            x = block[pred].to_numpy(float)
            by_lead[str(int(lead))] = skill(model.predict(x), y, (x > args.limit).astype(float))
    report["by_lead_test"] = by_lead

    out = root / "outputs" / f"g5_spatial_transfer_{args.limit:g}ms.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"limit {args.limit} m/s | stations {report['stations_total']} | rows {report['rows']}")
    print(f"  pooled TEST: skill vs climate {report['pooled']['test'].get('skill_vs_climatology'):+.3f}, "
          f"vs raw {report['pooled']['test'].get('skill_vs_raw'):+.3f}")
    s = report["summary"]
    print(f"  leave-one-station-out transfer median {s['transfer_median_skill']:+.3f} "
          f"(min {s['transfer_min_skill']:+.3f}, negative on {s['transfer_negative_stations']} stations)")
    print(f"  site-specific median {s['site_specific_median_skill']:+.3f} | "
          f"raw threshold median {s['raw_threshold_median_skill']:+.3f}")
    print("  by lead (test):", {k: round(v.get("skill_vs_climatology", float("nan")), 3)
                                for k, v in by_lead.items()})
    for key, row in report["value_transfer_summary"].items():
        cal_row = row.get("calibrated")
        tun_row = row.get("tuned_raw_transported")
        diff = row.get("calibrated_minus_tuned_raw")
        if not (cal_row and tun_row):
            continue
        print(f"  value@{key}: calibrated REV median {cal_row['median_rev']:+.3f} | "
              f"tuned-raw transported {tun_row['median_rev']:+.3f}"
              + (f" | calibrated better at {diff['stations_calibrated_better']}/{diff['n']} stations"
                 if diff else ""))


if __name__ == "__main__":
    main()
