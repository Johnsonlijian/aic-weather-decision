"""Epoch-level decision table: what a planner saw, and what actually happened.

One row is one decision epoch at one station under one declared forecast age.
The row records the forecast the planner held and the observation that followed,
so the calibration target and the policy predictor are the same quantity by
construction rather than by a second, independent calculation.

Definitions
-----------
``epoch``            a 6-hourly decision moment (00, 06, 12, 18 UTC).
``run_issue``        ``epoch - age_hours``; the only run the declared latency allows.
``block_max_gust``   maximum archived GFS gust over the run's forecast grid points
                     that fall inside ``(epoch, epoch + horizon]``.  This is exactly
                     what a planner reads off that run for a horizon-hour window.
``label``            1 if any observed KNMI FX hour in ``(epoch, epoch + horizon]``
                     exceeds the threshold.  The window is strictly forward looking,
                     so the row carries no hindsight.

Rows are dropped, never imputed, when the run does not cover the window or the
observation series is incomplete inside it.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

EPOCH_HOURS = (0, 6, 12, 18)
SPLITS = {
    "FIT": ("2021-06-01", "2023-12-31"),
    "CAL": ("2024-01-01", "2024-12-31"),
    "TEST": ("2025-01-01", "2025-09-30"),
}


def load_observations(root: Path, station: str, var: str = "FX_ms") -> pd.Series:
    frames = [pd.read_csv(p) for p in sorted((root / "data" / "raw" / "knmi").glob(f"{station}_*.csv"))]
    if not frames:
        raise SystemExit(f"no KNMI observations for station {station}")
    obs = pd.concat(frames, ignore_index=True)
    obs["valid_time"] = pd.to_datetime(obs["interval_end"], utc=True)
    if var not in obs.columns:
        raise SystemExit(f"KNMI table lacks observation column {var}")
    series = (obs.drop_duplicates("valid_time").set_index("valid_time")[var].sort_index())
    if series.isna().any():
        raise SystemExit(f"station {station} observation series has missing {var}; refusing to impute")
    return series


def load_forecast_series(root: Path, station: str) -> dict[pd.Timestamp, dict[pd.Timestamp, float]]:
    frames = [pd.read_csv(p) for p in
              sorted((root / "data" / "raw" / "gfs_gust").glob(f"{station}_*_gust.csv"))]
    if not frames:
        raise SystemExit(f"no GFS GUST tables for station {station}")
    fc = pd.concat(frames, ignore_index=True)
    fc["valid_time"] = pd.to_datetime(fc["valid_time"], utc=True)
    fc["issue_time"] = pd.to_datetime(fc["issue_time"], utc=True)
    fc = fc.drop_duplicates(subset=["valid_time", "issue_time", "lead_hours"])
    lookup: dict[pd.Timestamp, dict[pd.Timestamp, float]] = {}
    for issue, block in fc.groupby("issue_time", sort=False):
        lookup[issue] = dict(zip(block["valid_time"], block["GUST_ms"].astype(float)))
    return lookup


def build_station(root: Path, station: str, *, age_hours: int, horizons: list[int],
                  thresholds: list[float], publication_latency_hours: float,
                  decision_margin_hours: float, study_start: str, study_end: str,
                  obs_var: str = "FX_ms") -> tuple[pd.DataFrame, dict]:
    obs = load_observations(root, station, obs_var)
    runs = load_forecast_series(root, station)
    run_issues = sorted(runs)
    start = pd.Timestamp(study_start, tz="UTC")
    end = pd.Timestamp(study_end, tz="UTC") + pd.Timedelta(days=1)
    rows, skips = [], {"run_missing": 0, "window_not_covered": 0, "observation_incomplete": 0}
    epoch = start.ceil("6h")
    while epoch < end:
        # The latest run whose publication time (issue + declared latency) is at or
        # before the decision epoch.  With 00Z/12Z cycles and a 4 h latency this
        # yields a 6 h or 12 h old run alternating across the 6-hourly epochs, which
        # is exactly what an operator would actually have held.
        eligible = [i for i in run_issues if i + timedelta(hours=publication_latency_hours) <= epoch]
        if not eligible:
            skips["run_missing"] += 1
            epoch += timedelta(hours=6)
            continue
        issue = eligible[-1]
        series = runs[issue]
        margin = (epoch - issue).total_seconds() / 3600.0
        if margin < decision_margin_hours:
            skips["run_missing"] += 1
            epoch += timedelta(hours=6)
            continue
        record = {"station_id": station, "epoch": epoch, "run_issue": issue,
                  "age_hours": age_hours, "decision_margin_hours": margin}
        usable = True
        for horizon in horizons:
            window_times = [ts for ts in series if epoch < ts <= epoch + timedelta(hours=horizon)]
            if not window_times:
                skips["window_not_covered"] += 1
                usable = False
                break
            record[f"block_max_L{horizon}"] = float(max(series[ts] for ts in window_times))
            obs_window = obs.loc[(obs.index > epoch) & (obs.index <= epoch + timedelta(hours=horizon))]
            if len(obs_window) != horizon:
                skips["observation_incomplete"] += 1
                usable = False
                break
            for threshold in thresholds:
                record[f"L{horizon}_thr{threshold}"] = int(bool((obs_window > threshold).any()))
        if usable:
            rows.append(record)
        epoch += timedelta(hours=6)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, skips
    frame["split"] = "OTHER"
    for name, (lo, hi) in SPLITS.items():
        lo_ts, hi_ts = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1)
        frame.loc[(frame["epoch"] >= lo_ts) & (frame["epoch"] < hi_ts), "split"] = name
    return frame, skips


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stations", default="240,260,344")
    parser.add_argument("--age-hours", type=int, default=12)
    parser.add_argument("--horizons", default="2,4,6,8")
    parser.add_argument("--thresholds", default="9.0,12.0,13.0,16.5,20.0")
    parser.add_argument("--obs-var", default="FX_ms", choices=("FX_ms", "FH_ms"))
    parser.add_argument("--publication-latency-hours", type=float, default=4.0)
    parser.add_argument("--decision-margin-hours", type=float, default=2.0)
    parser.add_argument("--study-start", default="2021-06-01")
    parser.add_argument("--study-end", default="2025-09-30")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    root: Path = args.root
    horizons = [int(x) for x in args.horizons.split(",")]
    thresholds = [float(x) for x in args.thresholds.split(",")]
    stations = [s for s in args.stations.split(",") if s]
    frames, skip_report = [], {}
    for station in stations:
        frame, skips = build_station(
            root, station, age_hours=args.age_hours, horizons=horizons, thresholds=thresholds,
            publication_latency_hours=args.publication_latency_hours,
            decision_margin_hours=args.decision_margin_hours,
            study_start=args.study_start, study_end=args.study_end, obs_var=args.obs_var)
        skip_report[station] = skips
        frames.append(frame)
        print(f"  station {station}: {len(frame)} epochs", flush=True)
    table = pd.concat(frames, ignore_index=True)
    obs_suffix = "fx" if args.obs_var == "FX_ms" else "fh"
    out = args.out or (root / "outputs" / f"decision_epochs_age{args.age_hours}_{obs_suffix}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)

    audit = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "age_hours": args.age_hours,
        "horizons": horizons,
        "thresholds": thresholds,
        "declared_publication_latency_hours": args.publication_latency_hours,
        "declared_decision_margin_hours": args.decision_margin_hours,
        "study_start": args.study_start,
        "study_end": args.study_end,
        "rows": len(table),
        "skips": skip_report,
        "rows_per_split": {str(k): int(v) for k, v in table.groupby("split").size().items()},
        "rows_per_station": {str(k): int(v) for k, v in table.groupby("station_id").size().items()},
        "positive_rates": {
            f"L{h}_thr{t}": {
                "all": float(table[f"L{h}_thr{t}"].mean()),
                "fit": float(table.loc[table["split"] == "FIT", f"L{h}_thr{t}"].mean()),
                "cal": float(table.loc[table["split"] == "CAL", f"L{h}_thr{t}"].mean()),
                "test": float(table.loc[table["split"] == "TEST", f"L{h}_thr{t}"].mean()),
                "test_positives": int(table.loc[table["split"] == "TEST", f"L{h}_thr{t}"].sum()),
                "test_n": int((table["split"] == "TEST").sum()),
            } for h in horizons for t in thresholds},
        "note": ("block_max_gust is the maximum archived GFS gust among the run's forecast "
                 "grid points inside (epoch, epoch+horizon]; the label is the observed "
                 "exceedance in the same window. Forecast and observation share the window, "
                 "so a row is a genuine decision-time statement."),
    }
    (out.with_suffix(".audit.json")).write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: audit[k] for k in
                      ("rows", "rows_per_split", "skips")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
