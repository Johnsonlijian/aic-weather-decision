"""Emit every manuscript-facing number from the frozen v3 result set.

One file, one result version: the text is written from this report, and the
consistency checker re-derives the same quantities from the same JSON artefacts
and compares them against the text. Nothing here is hand-entered.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--table", default="outputs/epochs_multi3.csv")
    parser.add_argument("--prefix", default="g5_block_v3")
    parser.add_argument("--spatial", default="outputs/g5_spatial_transfer_12ms.json")
    args = parser.parse_args()
    root: Path = args.root

    frame = pd.read_csv(root / args.table, usecols=lambda c: not c.startswith(("latitude", "longitude")))
    test = frame[frame["split"] == "TEST"]
    lines: list[str] = []
    data: dict = {}

    # ---------- detector table ----------
    lines.append("## Table 1 - raw deterministic rule as a detector (TEST, 45 stations)")
    lines.append("| Limit | claim rate | true rate | false alarms | missed | positives |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    detector = {}
    for thr in (9.0, 12.0, 13.0, 16.5, 20.0):
        y = test[f"L12_thr{thr}"].to_numpy()
        claim = (test["block_max_L12"] > thr).to_numpy()
        row = {
            "claim_rate": round(100 * claim.mean(), 1),
            "true_rate": round(100 * y.mean(), 1),
            "false_alarm_rate": round(100 * (claim & (y == 0)).sum() / max((y == 0).sum(), 1), 1),
            "miss_rate": round(100 * ((~claim) & (y == 1)).sum() / max((y == 1).sum(), 1), 1),
            "positives": int(y.sum()),
        }
        detector[f"{thr:g}"] = row
        lines.append(f"| {thr:g} | {row['claim_rate']}% | {row['true_rate']}% | "
                     f"{row['false_alarm_rate']}% | {row['miss_rate']}% | {row['positives']:,} |")
    data["detector"] = detector
    data["test_epochs"] = int(len(test))
    data["splits"] = {k: int(v) for k, v in frame.groupby("split").size().items()}

    # ---------- calibration skill ----------
    cal = json.loads((root / "outputs" / f"{args.prefix}_calibration.json").read_text())
    lines.append("\n## Calibration skill (binned model, TEST)")
    lines.append("| Limit | vs climatology | vs raw threshold | vs logistic gap |")
    lines.append("|---:|---:|---:|---:|")
    skill = {}
    for row in cal:
        b, lg = row["models"]["binned"]["test"], row["models"]["logistic"]["test"]
        skill[f"{row['threshold']:g}"] = {
            "vs_climatology": round(b["skill_vs_climatology"], 3),
            "vs_raw_threshold": round(b["skill_vs_raw_threshold"], 3),
            "logistic_vs_climatology": round(lg["skill_vs_climatology"], 3),
            "reliability_bins_sum": b["reliability_n_total"],
            "split_n": b["split_n"],
        }
        lines.append(f"| {row['threshold']:g} | {b['skill_vs_climatology']:+.3f} | "
                     f"{b['skill_vs_raw_threshold']:+.3f} | "
                     f"{b['skill_vs_climatology'] - lg['skill_vs_climatology']:+.3f} |")
    data["skill"] = skill

    # ---------- economic value ----------
    rev = json.loads((root / "outputs" / f"{args.prefix}_economic_value.json").read_text())
    lines.append("\n## Cost-loss value (TEST): calibrated vs tuned raw vs documented limit")
    lines.append("| Limit | calibrated peak | tuned-raw peak | fixed-limit peak | max disagreements |")
    lines.append("|---:|---:|---:|---:|---:|")
    value = {}
    for row in rev:
        peaks = {}
        for rule in ("calibrated", "tuned_raw", "fixed_raw"):
            pts = [(c["rules"][rule]["relative_economic_value"], c["cost_loss_ratio"])
                   for c in row["curve"]
                   if c["rules"][rule]["relative_economic_value"] == c["rules"][rule]["relative_economic_value"]]
            peaks[rule] = max(pts) if pts else (float("nan"), float("nan"))
        dis = max(c["calibrated_vs_tuned_raw_disagreements"] for c in row["curve"])
        n = row["curve"][0]["test_n"]
        value[f"{row['threshold']:g}"] = {
            "calibrated_peak": round(peaks["calibrated"][0], 3),
            "calibrated_peak_ratio": round(peaks["calibrated"][1], 3),
            "tuned_raw_peak": round(peaks["tuned_raw"][0], 3),
            "tuned_raw_peak_ratio": round(peaks["tuned_raw"][1], 3),
            "fixed_raw_peak": round(peaks["fixed_raw"][0], 3),
            "max_disagreements": dis,
            "test_n": n,
            "disagreement_share": round(dis / n, 3),
        }
        lines.append(f"| {row['threshold']:g} | {peaks['calibrated'][0]:+.3f} @ {peaks['calibrated'][1]:.3f} | "
                     f"{peaks['tuned_raw'][0]:+.3f} @ {peaks['tuned_raw'][1]:.3f} | "
                     f"{peaks['fixed_raw'][0]:+.3f} | {dis}/{n} |")
    data["value"] = value

    # ---------- spatial transfer ----------
    sp = json.loads((root / args.spatial).read_text())
    s = sp["summary"]
    pooled = sp["pooled"]["test"]
    lines.append("\n## Spatial transfer and lead (12 m/s)")
    lines.append(f"- pooled held-out skill vs climatology: {pooled['skill_vs_climatology']:+.3f}")
    lines.append(f"- leave-one-station-out transfer median: {s['transfer_median_skill']:+.3f} "
                 f"(min {s['transfer_min_skill']:+.3f}, "
                 f"negative on {s['transfer_negative_stations']} stations)")
    lines.append(f"- site-specific median: {s['site_specific_median_skill']:+.3f}")
    lines.append(f"- documented-limit raw threshold median: {s['raw_threshold_median_skill']:+.3f}")
    lines.append(f"- by lead: {sp.get('by_lead_test')}")
    data["spatial"] = dict(s, pooled_skill_vs_climatology=pooled["skill_vs_climatology"],
                           pooled_skill_vs_raw=pooled["skill_vs_raw"],
                           test_positives=pooled["positives"])
    data["spatial_by_lead"] = sp.get("by_lead_test")

    # ---------- decision-value transfer ----------
    vt = sp.get("value_transfer_summary", {})
    if vt:
        lines.append("\n## Decision-value transfer: calibrated table vs transported tuned threshold")
        lines.append("| C/L | calibrated REV (median) | tuned-raw transported REV (median) | "
                     "calibrated better at |")
        lines.append("|---:|---:|---:|---:|")
        tv = {}
        for key, row in vt.items():
            cal_row, tun_row = row.get("calibrated"), row.get("tuned_raw_transported")
            diff = row.get("calibrated_minus_tuned_raw")
            if not (cal_row and tun_row):
                continue
            tv[key] = {"calibrated_median_rev": round(cal_row["median_rev"], 3),
                       "tuned_raw_median_rev": round(tun_row["median_rev"], 3),
                       "calibrated_better_stations": diff["stations_calibrated_better"] if diff else None,
                       "tuned_raw_better_stations": diff["stations_tuned_raw_better"] if diff else None,
                       "n": diff["n"] if diff else None}
            lines.append(f"| {key[1:]} | {cal_row['median_rev']:+.3f} | {tun_row['median_rev']:+.3f} | "
                         f"{diff['stations_calibrated_better']}/{diff['n']} |" if diff else "")
        data["value_transfer"] = tv

    # ---------- event frequency ----------
    gust_12 = float(test["L12_thr12.0"].mean())
    mean_event = None
    if "L12_thr_mean12.0" in frame.columns:
        mean_event = float(test["L12_thr_mean12.0"].mean())
    data["gust_12_rate"] = gust_12
    data["mean_wind_12_rate"] = mean_event
    lines.append(f"\n## Event frequency (TEST)\n- gust > 12 m/s: {100 * gust_12:.1f}%")
    if mean_event:
        lines.append(f"- hourly mean > 12 m/s: {100 * mean_event:.2f}% "
                     f"(ratio {gust_12 / mean_event:.1f}x rarer)")

    report = "\n".join(lines) + "\n"
    (root / "outputs" / "manuscript_numbers_v3.md").write_text(report, encoding="utf-8")
    (root / "outputs" / "manuscript_numbers_v3.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
