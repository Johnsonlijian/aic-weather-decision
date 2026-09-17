"""Assemble the decision dataset from KNMI observations and archived GFS GUST.

For every (station, valid hour, forecast lead) this writes one row containing

* the realised observation ``FX_ms`` (preceding-hour maximum gust),
* the archived forecast gust taken from exactly one issue run,
* the block-exceedance labels for each contract threshold and horizon length.

Label definition (frozen in ``protocol/G5_preregistration_2026-09-15.md``):
    Y(station, valid_hour, L) = 1 if any hour in
    (valid_hour - L, valid_hour] has observed FX_ms > threshold.
The block is *backward looking from the forecast valid hour*, which is exactly the
window a planner covers when they act on that forecast value; a label built from
hours after the valid time would make the forecast look better than it is.

Availability: a run issued at time ``t`` is treated as publishable at
``t + publication_latency_hours`` and usable at the first 6-hourly decision epoch
at or after that moment.  A 12Z run is therefore usable from 06Z the next day, not
from 06Z the same day.  Rows whose decision epoch precedes publication are dropped
rather than silently kept with a hindsight advantage.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

THRESHOLDS = (9.0, 12.0, 13.0, 16.5, 20.0)
HORIZONS = (2, 4, 6, 8)
DECISION_EPOCH_HOURS = (0, 6, 12, 18)


def load_observations(root: Path) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in sorted((root / "data" / "raw" / "knmi").glob("*.csv"))]
    if not frames:
        raise SystemExit("no KNMI observation CSVs found")
    obs = pd.concat(frames, ignore_index=True)
    obs["station_id"] = obs["station_id"].astype(str)
    obs["valid_time"] = pd.to_datetime(obs["interval_end"], utc=True)
    obs = obs[["station_id", "valid_time", "FX_ms", "FH_ms"]].drop_duplicates(
        subset=["station_id", "valid_time"])
    if obs["FX_ms"].isna().any():
        raise SystemExit("observation series contains missing FX; refusing to impute")
    return obs.sort_values(["station_id", "valid_time"]).reset_index(drop=True)


def load_forecasts(root: Path) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in sorted((root / "data" / "raw" / "gfs_gust").glob("*_gust.csv"))]
    if not frames:
        raise SystemExit("no GFS GUST tables found; run collect_gfs_gust_archive.py")
    fc = pd.concat(frames, ignore_index=True)
    fc["station_id"] = fc["station_id"].astype(str)
    fc["valid_time"] = pd.to_datetime(fc["valid_time"], utc=True)
    fc["issue_time"] = pd.to_datetime(fc["issue_time"], utc=True)
    fc["lead_hours"] = fc["lead_hours"].astype(int)
    before = len(fc)
    fc = fc.drop_duplicates(subset=["station_id", "valid_time", "issue_time", "lead_hours"])
    if len(fc) != before:
        print(f"dropped {before - len(fc)} duplicate forecast rows")
    return fc


def observation_blocks(obs: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Backward-looking block maxima and exceedance labels per station."""
    obs = obs.set_index(["station_id", "valid_time"]).sort_index()
    frames, gaps = [], {}
    for station, block in obs.groupby(level=0):
        series = block.droplevel(0)["FX_ms"]
        full = pd.date_range(series.index.min(), series.index.max(), freq="h", tz="UTC")
        series = series.reindex(full)
        gaps[str(station)] = int(series.isna().sum())
        # Hourly coverage is complete; a missing hour would make every label that
        # spans it unknowable, so the completeness check below is not cosmetic.
        labels = {}
        for horizon in HORIZONS:
            past = series.shift(0)  # the valid hour itself
            for step in range(1, horizon):
                past = past.combine(series.shift(step), np.fmax)
            for threshold in THRESHOLDS:
                labels[f"L{horizon}_thr{threshold}"] = (past > threshold).astype("float")
        frame = pd.DataFrame({"FX_ms": series, **labels})
        frame["station_id"] = station
        frame.index.name = "valid_time"
        frames.append(frame.reset_index())
    return pd.concat(frames, ignore_index=True), gaps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--study-start", default="2021-06-01")
    parser.add_argument("--study-end", default="2025-09-30")
    parser.add_argument("--publication-latency-hours", type=float, default=4.0)
    parser.add_argument("--min-decision-margin-hours", type=float, default=2.0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    root: Path = args.root
    obs = load_observations(root)
    fc = load_forecasts(root)
    obs = obs[(obs.valid_time >= pd.Timestamp(args.study_start, tz="UTC"))
              & (obs.valid_time <= pd.Timestamp(args.study_end, tz="UTC"))]
    blocks, gaps = observation_blocks(obs)

    merged = fc.merge(blocks, on=["station_id", "valid_time"], how="inner")
    publishable = merged["issue_time"] + pd.to_timedelta(args.publication_latency_hours, unit="h")
    # First 6-hourly epoch at or after the moment the object could have been seen.
    candidates = []
    for hour in DECISION_EPOCH_HOURS:
        candidate = publishable.dt.normalize() + pd.to_timedelta(hour, unit="h")
        candidates.append(candidate.where(candidate >= publishable,
                                          candidate + pd.to_timedelta(24, unit="h")))
    merged["decision_time"] = pd.to_datetime(
        np.minimum.reduce([c.to_numpy() for c in candidates]), utc=True)
    merged["observed_latency_hours"] = (
        pd.to_datetime(merged["index_last_modified"], utc=True, format="mixed")
        - merged["issue_time"]).dt.total_seconds() / 3600.0
    merged["decision_margin_hours"] = (
        merged["decision_time"] - merged["issue_time"]).dt.total_seconds() / 3600.0
    kept = merged[merged["decision_margin_hours"] >= args.min_decision_margin_hours].copy()
    dropped = len(merged) - len(kept)

    audit = {
        "study_start": args.study_start,
        "study_end": args.study_end,
        "declared_publication_latency_hours": args.publication_latency_hours,
        "declared_min_decision_margin_hours": args.min_decision_margin_hours,
        "thresholds": list(THRESHOLDS),
        "horizons": list(HORIZONS),
        "observation_rows": int(len(obs)),
        "observation_gap_hours_per_station": gaps,
        "forecast_rows": int(len(fc)),
        "joined_rows": int(len(merged)),
        "rows_dropped_by_availability_rule": int(dropped),
        "rows_kept": int(len(kept)),
        "observed_object_latency_hours": {
            "min": float(merged["observed_latency_hours"].min()),
            "median": float(merged["observed_latency_hours"].median()),
            "max": float(merged["observed_latency_hours"].max())},
        "decision_margin_hours": {
            "min": float(kept["decision_margin_hours"].min()),
            "median": float(kept["decision_margin_hours"].median()),
            "max": float(kept["decision_margin_hours"].max())},
        "label_counts": {
            f"L{h}_thr{t}": {"positives": int(kept[f"L{h}_thr{t}"].sum()),
                             "n": int(kept[f"L{h}_thr{t}"].notna().sum())}
            for h in HORIZONS for t in THRESHOLDS},
        "per_station_rows": {str(k): int(v) for k, v in kept.groupby("station_id").size().items()},
        "per_year_rows": {str(k): int(v) for k, v in kept.groupby(kept["valid_time"].dt.year).size().items()},
        "per_lead_rows": {str(k): int(v) for k, v in kept.groupby("lead_hours").size().items()},
        "note": ("GFS GUST is an instantaneous gridded gust forecast; KNMI FX is a "
                 "preceding-hour maximum. Rows pair the two at the declared time "
                 "endpoint only and are never treated as a direct observation-minus-"
                 "forecast error sample."),
    }
    out = args.out or (root / "outputs" / "decision_dataset.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    kept.to_csv(out, index=False)
    (out.with_suffix(".audit.json")).write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: audit[k] for k in
                      ("rows_kept", "rows_dropped_by_availability_rule",
                       "decision_margin_hours", "per_station_rows", "per_year_rows",
                       "label_counts")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
