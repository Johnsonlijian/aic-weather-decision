"""Pre-registered fair comparison of weather-informed scheduling policies.

One *episode* is one project start date at one station under one forecast-latency
regime and one operation contract.  Every policy is executed on the identical
episode: same project, same precedence network, same crane capacity, same realised
observations, same archived forecast runs.  No policy receives information another
policy lacks except through its own pre-registered definition.

Forecast latency regime
-----------------------
A regime is a forecast age ``A`` (hours).  Every 6-hour decision epoch of the
project uses the run issued at ``epoch - A``, and that run's own forecast
timestamps supply the values the policy sees.  A requested age of 12 h therefore
needs the f018 message of the t-12 run to describe the hour six hours after the
decision: a longer latency necessarily implies a longer forecast lead for the same
physical hour, which is a property of the forecast system rather than a choice.

Split discipline: calibrators are fitted on FIT, inspected on CAL, and the TEST
split is evaluated once.  Nothing in this file selects a model on TEST.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from calibration import (BinnedCalibrator, LogisticCalibrator, brier,
                         brier_skill_score, reliability_table)
from operation_engine import OperationContract, Project, run_execution, verify_execution_trace
from policies import (BlindPolicy, CalibratedPolicy, ClimatologyPolicy, RiskAwarePolicy,
                      ThresholdPolicy, critical_path_priority, make_project)

EPOCH = datetime(2021, 1, 1, tzinfo=timezone.utc)
# Declared publication latency of an archive object relative to its issue time.
# The audited Last-Modified values sit between 3.52 and 3.97 h after the cycle
# (outputs/gates/G3_forecast_availability_audit.json), so 4 h is the empirical
# upper bound rather than an assumption in the planner's favour.
PUBLICATION_LATENCY_HOURS = 4
SPLITS = {
    "FIT": ("2021-06-01", "2023-12-31"),
    "CAL": ("2024-01-01", "2024-12-31"),
    "TEST": ("2025-01-01", "2025-09-30"),
}
# Documented in-service wind limits for tower-crane lifting, from
# outputs/gates/G2_operation_contract_evidence_2026-09-15.md.
WIND_LIMIT_SPREAD_MS = (9.0, 12.0, 13.0, 16.5, 20.0)
LIFT_DURATION_SPREAD_H = (1, 2, 4, 7, 8)
DEFAULT_LIFT_DURATION_H = 7
SECTIONS = 8


def hours_since_epoch(ts) -> int:
    return int((pd.Timestamp(ts) - pd.Timestamp(EPOCH)).total_seconds() // 3600)


@dataclass(frozen=True)
class ForecastRunView:
    run_id: str
    issue_hour: int
    available_hour: int
    first_interval_hour: int
    scenarios: np.ndarray


def build_project(project_id: str = "deck-erection", *, wind_limit_ms: float = 20.0,
                  lift_duration_h: int = DEFAULT_LIFT_DURATION_H,
                  sections: int = SECTIONS) -> Project:
    """The continuous-operation network used by every policy.

    Each section needs a crane-free preparation before its crane lift and a
    crane-free bolting after it; sections do not wait for each other, so the crane
    is the binding resource.  The wind limit and the lift duration decide how often
    the contract bites, and both are swept rather than fixed: the limit across the
    documented cross-jurisdiction spread, and the duration because no published
    value for one segmental lift cycle was obtained.
    """
    restricted, unrestricted = [], []
    for i in range(1, sections + 1):
        unrestricted.append((f"prep_{i}", 3, ()))
        restricted.append((f"erect_{i}", lift_duration_h, (f"prep_{i}",), lift_duration_h))
        unrestricted.append((f"bolt_{i}", 3, (f"erect_{i}",)))
    contract = OperationContract(
        contract_id=f"crane_in_service_{wind_limit_ms:g}ms",
        start_limit=wind_limit_ms,
        continuation_limit=wind_limit_ms,
        required_consecutive_hours=lift_duration_h,
        resumable=True,
        evidence={
            "wind_limit": "DOCUMENTED; see G2_operation_contract_evidence_2026-09-15.md",
            "lift_duration": "ASSUMED and swept; no published lift-cycle duration obtained",
            "temporal_support": ("KNMI FX is a preceding-hour maximum gust; the archived GFS "
                                 "field is an instantaneous gust. The crane limit's own "
                                 "averaging interval was not documented by any source, so the "
                                 "mismatch is reported rather than resolved."),
        },
    )
    return make_project(project_id, contract, restricted_plan=restricted,
                        unrestricted_plan=unrestricted)


@dataclass
class StationData:
    station_id: str
    observations: pd.DataFrame
    forecasts: dict[tuple[str, int], pd.DataFrame]


def load_station_data(root: Path, station_id: str) -> StationData:
    obs_frames = [pd.read_csv(p) for p in
                  sorted((root / "data" / "raw" / "knmi").glob(f"{station_id}_*.csv"))]
    obs = pd.concat(obs_frames, ignore_index=True)
    obs["valid_time"] = pd.to_datetime(obs["interval_end"], utc=True)
    obs = (obs[["valid_time", "FX_ms"]].drop_duplicates("valid_time")
           .set_index("valid_time").sort_index())
    fc_frames = [pd.read_csv(p) for p in
                 sorted((root / "data" / "raw" / "gfs_gust").glob(f"{station_id}_*_gust.csv"))]
    fc = pd.concat(fc_frames, ignore_index=True)
    fc["valid_time"] = pd.to_datetime(fc["valid_time"], utc=True)
    fc["issue_time"] = pd.to_datetime(fc["issue_time"], utc=True)
    fc = fc.drop_duplicates(subset=["valid_time", "issue_time", "lead_hours"])
    forecasts: dict[tuple[str, int], pd.DataFrame] = {}
    for (issue, lead), block in fc.groupby(["issue_time", "lead_hours"], sort=False):
        forecasts[(issue.isoformat(), int(lead))] = (
            block.sort_values("valid_time").set_index("valid_time")[["GUST_ms"]])
    return StationData(station_id=station_id, observations=obs, forecasts=forecasts)


def build_runs(data: StationData, start: pd.Timestamp, end: pd.Timestamp,
               age_hours: int) -> list[ForecastRunView]:
    """Forecast runs a planner could hold inside [start, end) under latency ``age_hours``."""
    lookup: dict[pd.Timestamp, dict[pd.Timestamp, float]] = {}
    for (issue_iso, _lead), block in data.forecasts.items():
        issue = pd.Timestamp(issue_iso)
        target = lookup.setdefault(issue, {})
        for ts, value in block["GUST_ms"].items():
            target[ts] = float(value)
    runs: list[ForecastRunView] = []
    day = start.normalize()
    while day < end:
        for epoch_hour in (0, 6, 12, 18):
            decision = day + timedelta(hours=epoch_hour)
            if decision < start or decision >= end:
                continue
            issue = decision - timedelta(hours=age_hours)
            series = lookup.get(issue)
            if not series:
                continue
            times = sorted(series)
            first, last = times[0], times[-1]
            n_hours = int((last - first).total_seconds() // 3600) + 1
            arr = np.full((1, n_hours), np.nan)
            for ts in times:
                arr[0, int((ts - first).total_seconds() // 3600)] = series[ts]
            if np.isnan(arr).any():
                continue
            runs.append(ForecastRunView(
                run_id=issue.isoformat(), issue_hour=hours_since_epoch(issue),
                available_hour=hours_since_epoch(issue) + PUBLICATION_LATENCY_HOURS,
                first_interval_hour=hours_since_epoch(first), scenarios=arr))
        day += timedelta(days=1)
    return runs


def make_predictor(model, horizon: int):
    """Policy-side predictor: the block maximum of one archived run, calibrated.

    ``horizon`` is the span the contract needs to look safe.  The window contains
    the run's 6-hourly timestamps that fall inside it, which is exactly the set the
    calibrator was fitted on, so calibrator and policy read one quantity.
    """
    def predict(run, hour: int, length: int) -> float:
        offset = hour - run.first_interval_hour
        window = run.scenarios[0, offset:offset + max(length, horizon)]
        if window.size == 0:
            return float("nan")
        return float(model.predict(np.array([float(window.max())]))[0])
    return predict


def add_block_predictor(frame: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Attach the block-maximum forecast predictor the policies will read.

    For a decision at hour ``h`` the archived run supplies values on its own
    6-hourly timestamps, so a window of ``horizon`` hours contains the leads
    ``6, 12, ..., <= horizon``.  The predictor is the maximum GFS gust over those
    leads of the *same* issue cycle.
    """
    out = frame.copy()
    # A row belongs to the block maximum when its valid time lies inside
    # (issue_time, issue_time + horizon]; the smallest lead that satisfies this is
    # the first 6-hourly forecast point after the decision, which is what the
    # planner actually reads.  Where the shortest leads are absent from the archive
    # the next available lead is used, and the diagnostics record that fact.
    delta_hours = (out["valid_time"] - out["issue_time"]).dt.total_seconds() / 3600.0
    subset = out[(delta_hours > 0) & (delta_hours <= horizon)]
    # The key must include the issue cycle: two different cycles can share a valid
    # time, and mixing them into one block maximum would silently invent a
    # predictor that no single forecast run contains.
    block = (subset.groupby(["station_id", "valid_time", "issue_time"])["GUST_ms"].max()
             .rename("block_max_gust").reset_index())
    merged = out.merge(block, on=["station_id", "valid_time", "issue_time"], how="left")
    if merged["block_max_gust"].isna().any():
        raise ValueError("block predictor contains missing values")
    return merged


def fit_block_models(frame: pd.DataFrame, split: str, horizon: int, threshold: float):
    subset = frame[frame["split"] == split]
    label = f"L{horizon}_thr{threshold}"
    x = subset["block_max_gust"].to_numpy(dtype=float)
    y = subset[label].to_numpy(dtype=float)
    if y.sum() == 0:
        raise ValueError(f"no positives in {split} for {label}; calibration is not estimable")
    models = {"binned": BinnedCalibrator().fit(x, y),
              "logistic": LogisticCalibrator().fit(x, y)}
    return models, {"fit_n": int(len(y)), "fit_positives": int(y.sum())}


def calibration_diagnostics(frame: pd.DataFrame, horizon: int, threshold: float) -> dict:
    fit = frame[frame["split"] == "FIT"]
    cal = frame[frame["split"] == "CAL"]
    models, info = fit_block_models(frame, "FIT", horizon, threshold)
    label = f"L{horizon}_thr{threshold}"
    x = cal["block_max_gust"].to_numpy(dtype=float)
    y = cal[label].to_numpy(dtype=float)
    out = {"horizon": horizon, "threshold": threshold, "fit": info,
           "cal_n": int(len(y)), "cal_positives": int(y.sum()), "models": {}}
    for key, model in models.items():
        p = model.predict(x)
        raw = (x > threshold).astype(float)
        base = np.full_like(y, fit[label].mean())
        out["models"][key] = {
            "brier": brier(p, y),
            "skill_vs_climatology": brier_skill_score(p, y, base),
            "skill_vs_raw_threshold": brier_skill_score(p, y, raw),
            "reliability": reliability_table(p, y),
            "clipped_low": int(getattr(model, "clipped_low", 0)),
            "clipped_high": int(getattr(model, "clipped_high", 0)),
        }
    return out


@dataclass
class EpisodeMetrics:
    station_id: str
    start: str
    age_hours: int
    wind_limit_ms: float
    lift_duration_h: int
    policy_id: str
    critical_p: float
    status: str
    makespan_hours: int | None
    restricted_finished: int
    restricted_total: int
    exceedance_work_hours: int
    unsafe_start_hours: int
    false_stop_hours: int
    missed_safe_hours: int
    stopped_hours: int
    crane_idle_hours: int
    work_hours: int
    horizon_hours: int


def crane_idle(project: Project, result) -> int:
    tasks = project.by_name()
    idle = 0
    for event in result.events:
        hour = event["hour"]
        if not (project.work_day_start <= hour % 24 < project.work_day_end):
            continue
        used = sum(tasks[n].crane_demand for n in event["active"])
        idle += max(project.crane_capacity - used, 0)
    return idle


def run_episode(project: Project, data: StationData, start: pd.Timestamp, age_hours: int,
                policy, horizon_hours: int, *, verify: bool = True) -> EpisodeMetrics:
    end = start + timedelta(hours=horizon_hours)
    obs = data.observations.loc[(data.observations.index >= start)
                                & (data.observations.index < end), "FX_ms"]
    if len(obs) != horizon_hours:
        raise ValueError(f"incomplete observation series at {start} (+{horizon_hours} h)")
    truth = obs.to_numpy(dtype=float)
    runs = build_runs(data, start, end, age_hours)
    if hasattr(policy, "reset"):
        policy.reset()
    result = run_execution(project, truth, runs, policy, horizon=horizon_hours)
    if verify:
        verify_execution_trace(project, result, truth)
    return EpisodeMetrics(
        station_id=data.station_id, start=start.isoformat(), age_hours=age_hours,
        wind_limit_ms=project.contract.continuation_limit,
        lift_duration_h=project.contract.required_consecutive_hours,
        policy_id=policy.policy_id,
        critical_p=float(getattr(policy, "critical_p", float("nan"))),
        status=result.status, makespan_hours=result.makespan_hours,
        restricted_finished=result.restricted_finished,
        restricted_total=result.restricted_total,
        exceedance_work_hours=result.exceedance_work_hours,
        unsafe_start_hours=result.unsafe_start_hours,
        false_stop_hours=result.false_stop_hours,
        missed_safe_hours=result.missed_safe_hours,
        stopped_hours=result.stopped_hours,
        crane_idle_hours=crane_idle(project, result),
        work_hours=result.work_hours, horizon_hours=horizon_hours)


def load_decision_frame(root: Path, horizon: int) -> pd.DataFrame:
    frame = pd.read_csv(root / "outputs" / "decision_dataset.csv")
    frame["valid_time"] = pd.to_datetime(frame["valid_time"], utc=True)
    for column in ("issue_time", "decision_time"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], utc=True, format="mixed")
    frame["split"] = "OTHER"
    for name, (lo, hi) in SPLITS.items():
        lo_ts = pd.Timestamp(lo, tz="UTC")
        hi_ts = pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1)
        frame.loc[(frame["valid_time"] >= lo_ts) & (frame["valid_time"] < hi_ts), "split"] = name
    return add_block_predictor(frame, horizon)


def policy_ladder(predict, criticals: list[float], base_rate: float, project: Project):
    ladder = [BlindPolicy(), ThresholdPolicy(),
              ClimatologyPolicy(base_rate=base_rate, critical_p=0.10)]
    ladder += [CalibratedPolicy(predict=predict, critical_p=c) for c in criticals]
    ladder += [RiskAwarePolicy(predict=predict, critical_p=c, priority=critical_path_priority(project),
                               float_slack=1.0, critical_priority_bound=SECTIONS // 2)
               for c in criticals]
    return ladder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stations", default="240,260,344")
    parser.add_argument("--mode",
                        choices=("smoke", "main", "latency", "duration", "diagnostics"),
                        default="smoke")
    parser.add_argument("--horizon-days", type=int, default=70)
    parser.add_argument("--stride-days", type=int, default=3)
    parser.add_argument("--criticals", default="0.05,0.10,0.20,0.40")
    parser.add_argument("--ages", default="12")
    parser.add_argument("--limits", default=",".join(str(x) for x in WIND_LIMIT_SPREAD_MS))
    parser.add_argument("--durations", default=str(DEFAULT_LIFT_DURATION_H))
    parser.add_argument("--out-prefix", default="g5")
    args = parser.parse_args()

    root: Path = args.root
    horizon_hours = args.horizon_days * 24
    stations = [s for s in args.stations.split(",") if s]
    ages = [int(a) for a in args.ages.split(",")]
    limits = [float(x) for x in args.limits.split(",")]
    durations = [int(x) for x in args.durations.split(",")]
    criticals = [float(c) for c in args.criticals.split(",")]
    if args.mode == "smoke":
        stations, ages, limits, durations = stations[:1], ages[:1], limits[:1], durations[:1]
        criticals = criticals[:2]
        horizon_hours = min(horizon_hours, 30 * 24)
        args.stride_days = max(args.stride_days, 15)

    data_cache = {s: load_station_data(root, s) for s in stations}
    rows: list[EpisodeMetrics] = []
    diagnostics: list[dict] = []
    for limit in limits:
        for duration in durations:
            frame = load_decision_frame(root, duration)
            label = f"L{duration}_thr{limit}"
            if label not in frame.columns:
                print(f"  skip limit={limit} duration={duration}: no label {label}")
                continue
            try:
                models, _ = fit_block_models(frame, "FIT", duration, limit)
            except ValueError as exc:
                print(f"  skip limit={limit} duration={duration}: {exc}")
                continue
            base_rate = float(frame.loc[frame["split"] == "FIT", label].mean())
            project = build_project(wind_limit_ms=limit, lift_duration_h=duration)
            predict = make_predictor(models["binned"], duration)
            diagnostics.append(calibration_diagnostics(frame, duration, limit))
            for station, data in data_cache.items():
                obs_start, obs_end = data.observations.index.min(), data.observations.index.max()
                lo = max(pd.Timestamp(SPLITS["TEST"][0], tz="UTC"),
                         obs_start + pd.Timedelta(days=1))
                hi = min(pd.Timestamp(SPLITS["TEST"][1], tz="UTC"),
                         obs_end - pd.Timedelta(hours=horizon_hours))
                if hi <= lo:
                    print(f"  skip station {station}: empty test window")
                    continue
                starts = pd.date_range(lo, hi, freq=f"{args.stride_days}D")
                for age in ages:
                    for start in starts:
                        for policy in policy_ladder(predict, criticals, base_rate, project):
                            rows.append(run_episode(project, data, start, age, policy,
                                                    horizon_hours, verify=True))
            print(f"  limit={limit} duration={duration}: {len(rows)} episodes", flush=True)

    table = pd.DataFrame([r.__dict__ for r in rows])
    out = root / "outputs" / f"{args.out_prefix}_policy_comparison.csv"
    table.to_csv(out, index=False)
    summary = (table.groupby(["wind_limit_ms", "lift_duration_h", "policy_id", "critical_p"],
                             dropna=False)
               .agg(episodes=("status", "size"),
                    complete=("status", lambda s: int((s == "complete").sum())),
                    makespan_mean=("makespan_hours", "mean"),
                    exceedance_work_mean=("exceedance_work_hours", "mean"),
                    unsafe_start_mean=("unsafe_start_hours", "mean"),
                    false_stop_mean=("false_stop_hours", "mean"),
                    missed_safe_mean=("missed_safe_hours", "mean"),
                    idle_mean=("crane_idle_hours", "mean"))
               .reset_index())
    summary.to_csv(root / "outputs" / f"{args.out_prefix}_policy_summary.csv", index=False)
    (root / "outputs" / f"{args.out_prefix}_calibration_diagnostics.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
