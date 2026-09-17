"""Epoch table for the expanded study: 46 stations, multi-hazard labels, leads.

One row is one decision epoch at one station: the forecast the planner could hold
under the audited availability rule, the observed window that followed, and the
event labels for wind, rain and temperature.  Columns record which forecast lead
supplied the predictor, so skill can be stratified by lead without re-deriving it.

Wind limits are the documented cross-jurisdiction spread; the rain and
temperature limits come from the published specification contracts recorded in
outputs/gates/G2_operation_contract_evidence_2026-09-15.md (dry window for
lifting; 5-35 C placing window for concrete; 4.4-46 C for epoxy jointing).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

EPOCH_HOURS = (0, 6, 12, 18)
SPLITS = {"FIT": ("2021-06-01", "2023-12-31"),
          "CAL": ("2024-01-01", "2024-12-31"),
          "TEST": ("2025-01-01", "2025-09-30")}
WIND_LIMITS = (9.0, 12.0, 13.0, 16.5, 20.0)
# documented in the contract evidence: concrete placing 5-35 C, epoxy jointing 4.4-46 C
TEMP_WINDOWS = {"concrete": (5.0, 35.0), "epoxy": (4.4, 46.0)}


def load_observations(root: Path, station: str) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in
              sorted((root / "data" / "raw" / "knmi_multi").glob(f"{station}_*.csv"))]
    if not frames:
        raise SystemExit(f"no multi-variable KNMI data for station {station}")
    obs = pd.concat(frames, ignore_index=True)
    obs["valid_time"] = pd.to_datetime(obs["interval_end"], utc=True)
    cols = ["valid_time", "FX_ms", "FH_ms", "T_degC", "RH_amount_mm", "RH_trace"]
    for c in cols:
        if c not in obs.columns:
            obs[c] = np.nan
    obs = obs[cols].drop_duplicates("valid_time").set_index("valid_time").sort_index()
    return obs


def station_eligibility(obs: pd.DataFrame) -> dict:
    """Which variables this station actually reports over the study window.

    A station that never reports FX must not be scored as if every hour were
    calm, so eligibility is checked before any label is written.
    """
    frac = {c: float(obs[c].notna().mean()) for c in ("FX_ms", "T_degC", "RH_amount_mm")}
    return {"fx_complete": frac["FX_ms"] > 0.95,
            "t_complete": frac["T_degC"] > 0.95,
            "rh_complete": frac["RH_amount_mm"] > 0.95,
            "coverage": {k: round(v, 4) for k, v in frac.items()}}


DEFAULT_FORECAST_DIRS = ("gfs_gust_multi", "gfs_gust_multi00")


def load_forecasts(root: Path, station: str,
                   folders: tuple[str, ...] = DEFAULT_FORECAST_DIRS) -> dict[pd.Timestamp, dict[pd.Timestamp, tuple[float, int]]]:
    """issue time -> {valid time: (gust, lead)} for the multi-station collection."""
    frames = []
    # every archived cycle is loaded together so the availability rule can choose
    # the freshest run at every decision epoch
    for folder in folders:
        frames += [pd.read_csv(p) for p in
                   sorted((root / "data" / "raw" / folder).glob(f"{station}_*_gust.csv"))]
    if not frames:
        raise SystemExit(f"no multi-station GFS tables for station {station}")
    fc = pd.concat(frames, ignore_index=True)
    fc["valid_time"] = pd.to_datetime(fc["valid_time"], utc=True)
    fc["issue_time"] = pd.to_datetime(fc["issue_time"], utc=True)
    fc = fc.drop_duplicates(subset=["valid_time", "issue_time", "lead_hours"])
    out: dict[pd.Timestamp, dict[pd.Timestamp, tuple[float, int]]] = {}
    for issue, block in fc.groupby("issue_time", sort=False):
        out[issue] = {ts: (float(g), int(l)) for ts, g, l in
                      zip(block["valid_time"], block["GUST_ms"], block["lead_hours"])}
    return out


def build_station(root: Path, station: str, *, horizons: list[int], publication_latency: float,
                  study_start: str, study_end: str, allow_joint: bool = False,
                  forecast_dirs: tuple[str, ...] = DEFAULT_FORECAST_DIRS) -> tuple[pd.DataFrame, dict]:
    obs = load_observations(root, station)
    elig = station_eligibility(obs)
    if not elig["fx_complete"]:
        return pd.DataFrame(), {"INELIGIBLE": "fx_coverage", **elig}
    runs = load_forecasts(root, station, forecast_dirs)
    issues = sorted(runs)
    start = pd.Timestamp(study_start, tz="UTC")
    end = pd.Timestamp(study_end, tz="UTC") + pd.Timedelta(days=1)
    rows, skips = [], {"run_missing": 0, "window_not_covered": 0, "observation_incomplete": 0,
                       "wind_window_unresolved": 0}
    epoch = start.ceil("6h")
    # two-pointer scan: issues are sorted and epochs increase, so one pass replaces
    # the per-epoch scan over every archived run
    pointer = 0
    while epoch < end:
        while (pointer + 1 < len(issues)
               and issues[pointer + 1] + timedelta(hours=publication_latency) <= epoch):
            pointer += 1
        if issues[pointer] + timedelta(hours=publication_latency) > epoch:
            skips["run_missing"] += 1
            epoch += timedelta(hours=6)
            continue
        issue = issues[pointer]
        series = runs[issue]
        record = {"station_id": station, "epoch": epoch, "run_issue": issue,
                  "decision_margin_hours": (epoch - issue).total_seconds() / 3600.0}
        usable = True
        for horizon in horizons:
            window = {ts: v for ts, v in series.items() if epoch < ts <= epoch + timedelta(hours=horizon)}
            if not window:
                skips["window_not_covered"] += 1
                usable = False
                break
            gusts = [v[0] for v in window.values()]
            leads = [v[1] for v in window.values()]
            record[f"block_max_L{horizon}"] = float(max(gusts))
            record[f"lead_L{horizon}"] = int(min(leads))
            observed = obs.loc[(obs.index > epoch) & (obs.index <= epoch + timedelta(hours=horizon))]
            if len(observed) != horizon:
                skips["observation_incomplete"] += 1
                usable = False
                break
            fx = observed["FX_ms"].to_numpy(dtype=float)
            temp = observed["T_degC"].to_numpy(dtype=float)
            # A window containing a missing value is UNRESOLVED, never "no exceedance":
            # scoring a gap as calm would manufacture safe hours that were never observed.
            fx_complete = bool(np.isfinite(fx).all())
            temp_complete = bool(np.isfinite(temp).all())
            if not fx_complete:
                skips["wind_window_unresolved"] += 1
                usable = False
                break
            record[f"obs_max_gust_L{horizon}"] = float(np.max(fx))
            for limit in WIND_LIMITS:
                record[f"L{horizon}_thr{limit}"] = int(bool((fx > limit).any()))
            # Joint wind/rain/temperature labels are OFF by default. The archived
            # `R` column is a 0/1 occurrence flag, not an amount, so any earlier
            # `R/10` millimetre total was miscomputed; and the 5-35 C band in the
            # standards is a concrete *mixture* temperature, not the 1.5 m air
            # temperature that this archive reports. Both would need their own
            # verified contract before they can carry a label, so they are written
            # only behind an explicit opt-in and are never used in the paper.
            if not allow_joint:
                continue
            if temp_complete:
                record[f"obs_temp_min_L{horizon}"] = float(np.min(temp))
                record[f"obs_temp_max_L{horizon}"] = float(np.max(temp))
                for name, (lo, hi) in TEMP_WINDOWS.items():
                    in_range = (temp >= lo) & (temp <= hi)
                    record[f"L{horizon}_tempok_{name}"] = int(bool(in_range.all()))
                    joint_wt = (~(fx > 12.0)) & in_range
                    record[f"L{horizon}_joint12wt_{name}"] = int(bool(joint_wt.all()))
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
    parser.add_argument("--stations-file", default="configs/knmi_stations_multi.json")
    parser.add_argument("--horizons", default="6,12,24")
    parser.add_argument("--publication-latency-hours", type=float, default=4.0)
    parser.add_argument("--study-start", default="2021-06-01")
    parser.add_argument("--study-end", default="2025-09-30")
    parser.add_argument("--out", default="outputs/epochs_multi.csv")
    parser.add_argument("--allow-joint-hazard", action="store_true",
                        help="write joint wind/rain/temperature labels (NOT publication-ready; "
                             "see the opt-in note in build_station)")
    parser.add_argument("--forecast-dirs", default=",".join(DEFAULT_FORECAST_DIRS),
                        help="comma-separated forecast folders under data/raw, so an extended "
                             "or hold-out collection can be built without touching the frozen one")
    args = parser.parse_args()

    root: Path = args.root
    cfg = json.loads((root / args.stations_file).read_text(encoding="utf-8"))
    stations = [s["station_id"] for s in cfg["stations"]]
    meta = {s["station_id"]: s for s in cfg["stations"]}
    horizons = [int(x) for x in args.horizons.split(",")]

    frames, skips_all = [], {}
    for i, station in enumerate(stations, 1):
        frame, skips = build_station(root, station, horizons=horizons,
                                     publication_latency=args.publication_latency_hours,
                                     study_start=args.study_start, study_end=args.study_end,
                                     allow_joint=args.allow_joint_hazard,
                                     forecast_dirs=tuple(args.forecast_dirs.split(",")))
        if not frame.empty:
            frame["latitude"] = meta[station]["latitude"]
            frame["longitude"] = meta[station]["longitude"]
            frames.append(frame)
        skips_all[station] = skips
        if i % 10 == 0 or i == len(stations):
            print(f"  stations {i}/{len(stations)}; rows so far {sum(len(f) for f in frames)}", flush=True)

    table = pd.concat(frames, ignore_index=True)
    out = root / args.out
    table.to_csv(out, index=False)
    audit = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "stations": len(stations), "rows": int(len(table)),
        "horizons": horizons,
        "wind_limits": list(WIND_LIMITS),
        "temperature_windows": TEMP_WINDOWS,
        "rows_per_split": {k: int(v) for k, v in table.groupby("split").size().items()},
        "rows_per_station": {k: int(v) for k, v in table.groupby("station_id").size().items()},
        "lead_used_L12": {str(k): int(v) for k, v in
                          table.groupby(table["lead_L12"]).size().items()},
        "positive_rates": {
            col: {"all": float(table[col].mean()),
                  "test": float(table.loc[table["split"] == "TEST", col].mean()),
                  "test_positives": int(table.loc[table["split"] == "TEST", col].sum())}
            for col in table.columns if col.startswith(("L12_thr", "L12_joint", "L12_dry", "L12_tempok"))},
        "skips": skips_all,
        "eligibility": {k: v for k, v in skips_all.items() if "fx_complete" in v or "INELIGIBLE" in v},
        "note": ("Joint windows require wind <= 12 m/s AND no rain AND temperature inside the "
                 "documented placing/jointing range over the whole block."),
    }
    (out.with_suffix(".audit.json")).write_text(json.dumps(audit, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    print(json.dumps({"rows": audit["rows"], "rows_per_split": audit["rows_per_split"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
