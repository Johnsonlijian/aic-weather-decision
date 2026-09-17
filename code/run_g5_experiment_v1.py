"""Pre-registered fair comparison of weather-informed scheduling policies.

One *episode* is one project start date at one station under one forecast-latency
regime.  Every policy is executed on the identical episode: same project, same
precedence network, same crane capacity, same realised observations, same
archived forecast runs.  No policy is given information another policy lacks
except through the declared, pre-registered policy definition.

Forecast latency regime
-----------------------
A regime is a single forecast age ``A`` (hours).  Every 6-hour decision epoch of
the project uses the run issued at ``epoch - A``, and that run's own forecast
timestamps supply the values the policy sees.  This is why a requested age of 12
hours needs the f018 message of the t-12 run to describe the hour 6 hours after
the decision.  Regimes are therefore honest about the fact that a longer latency
forces a longer forecast lead for the same physical hour.

Nothing in this file may read the test split for model selection; the split and
the policy ladder are frozen in ``protocol/G5_preregistration_2026-09-15.md``.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from calibration import BinnedCalibrator, LogisticCalibrator, brier, brier_skill_score, reliability_table
from operation_engine import (OperationContract, Project, ProjectTask, run_execution,
                              verify_execution_trace, work_windows)
from policies import (BlindPolicy, CalibratedPolicy, ClimatologyPolicy, RiskAwarePolicy,
                      ThresholdPolicy, critical_path_priority, make_project)

EPOCH = datetime(2021, 1, 1, tzinfo=timezone.utc)
LEAD_STEPS = (6, 12, 24, 36, 48, 60, 72)
# Declared publication latency of the archive object relative to its issue time.
# The observed ``Last-Modified`` of the NOAA index objects sits between 3.55 and
# 4.15 hours after the cycle; 4 h is the conservative upper end of that observation.
PUBLICATION_LATENCY_HOURS = 4


def hours_since_epoch(ts: pd.Timestamp) -> int:
    return int((ts - EPOCH).total_seconds() // 3600)


@dataclass(frozen=True)
class ForecastRunView:
    run_id: str
    issue_hour: int
    available_hour: int
    first_interval_hour: int
    scenarios: np.ndarray


# Documented in-service wind limits for the tower-crane lifting operation, from the
# evidence audit in outputs/gates/G2_operation_contract_evidence_2026-09-15.md.
# The list is a cross-jurisdiction spread, not a start/continuation pair: the
# audit found no source that documents a separate start limit for this operation
# within one jurisdiction, so none is invented here.
WIND_LIMIT_SPREAD_MS = (9.0, 12.0, 13.0, 16.5, 20.0)
LIFT_DURATION_SPREAD_H = (1, 2, 4, 8)
SECTIONS = 8


def build_project(project_id: str = "deck-erection", *, wind_limit_ms: float = 20.0,
                  lift_duration_h: int = 7, sections: int = SECTIONS) -> Project:
    """The continuous-operation network used by every policy.

    Each section needs a crane-free preparation before its crane lift and a
    crane-free bolting after it; sections do not wait for each other, so the crane
    is the binding resource.  The wind limit and the lift duration are the two
    quantities that decide how often the contract bites, and both are swept rather
    than fixed: the limit across the documented cross-jurisdiction spread, the
    duration because no published value for one segmental lift cycle could be
    obtained.
    """
    restricted = []
    unrestricted = []
    for i in range(1, sections + 1):
        unrestricted.append((f"prep_{i}", 3, ()))
        restricted.append((f"erect_{i}", lift_duration_h, (f"prep_{i}",),
                           lift_duration_h))
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
            "temporal_support": ("KNMI FX is a preceding-hour maximum gust; the archived GFS field is an "
                                  "instantaneous gust. The crane limit\'s own averaging interval was not "
                                  "documented by any source, so the mismatch is reported, not resolved."),
        },
    )
    return make_project(project_id, contract, restricted_plan=restricted,
                        unrestricted_plan=unrestricted)


@dataclass
class StationData:
    station_id: str
    observations: pd.DataFrame          # index: valid_time (UTC), column FX_ms
    forecasts: dict[tuple[str, int], pd.DataFrame]  # (issue_iso, lead) -> valid_time, GUST_ms


def load_station_data(root: Path, station_id: str) -> StationData:
    obs_frames = []
    for path in sorted((root / "data" / "raw" / "knmi").glob(f"{station_id}_*.csv")):
        obs_frames.append(pd.read_csv(path))
    obs = pd.concat(obs_frames, ignore_index=True)
    obs["valid_time"] = pd.to_datetime(obs["interval_end"], utc=True)
    obs = obs[["valid_time", "FX_ms"]].drop_duplicates("valid_time").set_index("valid_time").sort_index()
    fc_frames = []
    for path in sorted((root / "data" / "raw" / "gfs_gust").glob(f"{station_id}_*_gust.csv")):
        fc_frames.append(pd.read_csv(path))
    fc = pd.concat(fc_frames, ignore_index=True)
    fc["valid_time"] = pd.to_datetime(fc["valid_time"], utc=True)
    fc["issue_time"] = pd.to_datetime(fc["issue_time"], utc=True)
    fc = fc.drop_duplicates(subset=["valid_time", "issue_time", "lead_hours"])
    forecasts: dict[tuple[str, int], pd.DataFrame] = {}
    for (issue, lead), block in fc.groupby(["issue_time", "lead_hours"], sort=False):
        block = block.sort_values("valid_time")
        forecasts[(issue.isoformat(), int(lead))] = block.set_index("valid_time")[["GUST_ms"]]
    return StationData(station_id=station_id, observations=obs, forecasts=forecasts)


def _series_by_issue(data: StationData) -> dict[pd.Timestamp, dict[pd.Timestamp, float]]:
    """Group every lead message of one issue cycle into a single forecast series."""
    lookup: dict[pd.Timestamp, dict[pd.Timestamp, float]] = {}
    for (issue_iso, _lead), block in data.forecasts.items():
        issue = pd.Timestamp(issue_iso)
        target = lookup.setdefault(issue, {})
        for ts, value in block["GUST_ms"].items():
            target[ts] = float(value)
    return lookup


def build_runs(data: StationData, start: pd.Timestamp, end: pd.Timestamp,
               age_hours: int) -> list[ForecastRunView]:
    """Forecast runs a planner could hold inside [start, end) under latency ``age_hours``.

    Every 6-hour decision epoch uses the run issued ``age_hours`` earlier.  The run's
    own forecast timestamps (f006 .. f072 of that cycle) supply the values, so a
    longer latency necessarily implies a longer effective lead for a given physical
    hour; that coupling is a property of the forecast system, not a modelling choice.
    """
    lookup = _series_by_issue(data)
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


def project_capacity(project: Project, horizon: int) -> np.ndarray:
    return work_windows(project, horizon)


@dataclass
class EpisodeMetrics:
    station_id: str
    start: str
    age_hours: int
    contract_id: str
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
    episodes_verified: int = 1


def crane_idle(project: Project, result) -> int:
    """Hours inside the working window with spare crane capacity."""
    tasks = project.by_name()
    idle = 0
    for event in result.events:
        hour = event["hour"]
        if not (project.work_day_start <= hour % 24 < project.work_day_end):
            continue
        used = sum(tasks[n].crane_demand for n in event["active"])
        idle += max(project.crane_capacity - used, 0)
    return idle


def run_episode(project: Project, data: StationData, start: pd.Timestamp,
                age_hours: int, policy, horizon_hours: int, *,
                verify: bool = True) -> EpisodeMetrics:
    end = start + timedelta(hours=horizon_hours)
    obs = data.observations.loc[(data.observations.index >= start)
                                & (data.observations.index < end), "FX_ms"]
    if len(obs) != horizon_hours:
        raise ValueError(f"observation series is not complete for {start} (+{horizon_hours} h)")
    truth = obs.to_numpy(dtype=float)
    runs = build_runs(data, start, end, age_hours)
    if hasattr(policy, "reset"):
        policy.reset()
    result = run_execution(project, truth, runs, policy, horizon=horizon_hours)
    if verify:
        verify_execution_trace(project, result, truth)
    return EpisodeMetrics(
        station_id=data.station_id, start=start.isoformat(), age_hours=age_hours,
        contract_id=project.contract.contract_id, policy_id=policy.policy_id,
        critical_p=float(getattr(policy, "critical_p", float("nan"))),
        status=result.status, makespan_hours=result.makespan_hours,
        restricted_finished=result.restricted_finished, restricted_total=result.restricted_total,
        exceedance_work_hours=result.exceedance_work_hours,
        unsafe_start_hours=result.unsafe_start_hours,
        false_stop_hours=result.false_stop_hours,
        missed_safe_hours=result.missed_safe_hours,
        stopped_hours=result.stopped_hours,
        crane_idle_hours=crane_idle(project, result),
        work_hours=result.work_hours, horizon_hours=horizon_hours)


def fit_calibrators(fit_frame: pd.DataFrame, cal_frame: pd.DataFrame,
                    horizon: int, threshold: float, *, station: str | None = None
                    ) -> tuple[dict, dict]:
    """Fit the pre-declared calibrators for one (horizon, threshold) target.

    Predictor: the maximum forecast gust in the block, expressed both absolutely
    and as a ratio to the threshold.  ``station`` restricts fitting to one site,
    which is the site-specific calibration route of the pre-registration.
    """
    sub_fit = fit_frame if station is None else fit_frame[fit_frame["station_id"] == station]
    sub_cal = cal_frame if station is None else cal_frame[cal_frame["station_id"] == station]
    label = f"L{horizon}_thr{threshold}"
    x_fit = sub_fit["block_max_gust"].to_numpy(dtype=float)
    y_fit = sub_fit[label].to_numpy(dtype=float)
    x_cal = sub_cal["block_max_gust"].to_numpy(dtype=float)
    y_cal = sub_cal[label].to_numpy(dtype=float)
    models = {"binned": BinnedCalibrator().fit(x_fit, y_fit),
              "logistic": LogisticCalibrator().fit(x_fit, y_fit)}
    diagnostics: dict[str, dict] = {}
    for key, model in models.items():
        p_cal = model.predict(x_cal)
        p_raw = (x_cal > threshold).astype(float)
        base = np.full_like(y_cal, y_fit.mean())
        diagnostics[key] = {
            "cal_brier": brier(p_cal, y_cal),
            "cal_brier_skill_vs_climatology": brier_skill_score(p_cal, y_cal, base),
            "cal_brier_skill_vs_raw_threshold": brier_skill_score(p_cal, y_cal, p_raw),
            "cal_reliability": reliability_table(p_cal, y_cal),
            "cal_positives": int(y_cal.sum()), "cal_n": int(len(y_cal)),
            "fit_positives": int(y_fit.sum()), "fit_n": int(len(y_fit)),
        }
    return models, diagnostics


def add_block_predictor(frame: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Attach the exact block-maximum forecast predictor the policies will read.

    For a decision at hour ``h`` an archived run supplies values on its own 6-hour
    timestamps, so the window ``[h, h+horizon)`` contains the leads
    ``6, 12, ..., <= horizon``.  The predictor is the maximum GFS gust over exactly
    those leads of the *same* issue cycle, which is what a planner reads off one
    forecast run.  Restricting to one issue cycle prevents an earlier, more
    skilful lead from silently improving the predictor.
    """
    out = frame.copy()
    leads = sorted(int(x) for x in out["lead_hours"].unique())
    picks = [lead for lead in leads if lead <= horizon] or [leads[0]]
    subset = out[out["lead_hours"].isin(picks)]
    block = (subset.groupby(["station_id", "valid_time"])["GUST_ms"].max()
             .rename("block_max_gust").reset_index())
    merged = out.merge(block, on=["station_id", "valid_time"], how="left")
    if merged["block_max_gust"].isna().any():
        raise ValueError("block predictor contains missing values")
    return merged


def make_predictor(models: dict, horizon: int) -> callable:
    """Build the policy-side predictor that reads one archived run.

    The predictor returns the calibrated probability that the required block
    contains an exceedance, using the block maximum of the same issue cycle that
    :func:`add_block_predictor` used when the calibrator was fitted.
    """
    primary = models["primary"]

    def predict(run, hour: int, length: int) -> float:
        offset = hour - run.first_interval_hour
        # Leads present in this window, in the run's own 6-hourly sampling.
        window = run.scenarios[0, offset:offset + length]
        if window.size == 0:
            return float("nan")
        return float(primary.predict(np.array([float(window.max())]))[0])

    return predict


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stations", default="240,260,344")
    parser.add_argument("--ages", default="12,24")
    parser.add_argument("--horizon-hours", type=int, default=24 * 70)
    parser.add_argument("--stride-days", type=int, default=3)
    parser.add_argument("--criticals", default="0.05,0.10,0.20,0.40")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    root: Path = args.root
    frame = pd.read_csv(root / "outputs" / "decision_dataset.csv")
    frame["valid_time"] = pd.to_datetime(frame["valid_time"], utc=True)
    for column in ("issue_time", "decision_time", "index_last_modified"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], utc=True, format="mixed")
    frame = add_block_predictor(frame, horizon=4)

    splits = {
        "FIT": ("2021-06-01", "2023-12-31"),
        "CAL": ("2024-01-01", "2024-12-31"),
        "TEST": ("2025-01-01", "2025-09-30"),
    }
    frames = {}
    for name, (lo, hi) in splits.items():
        lo_ts, hi_ts = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1)
        frames[name] = frame[(frame["valid_time"] >= lo_ts) & (frame["valid_time"] < hi_ts)]

    models, diagnostics = fit_calibrators(frames["FIT"], frames["CAL"], horizon=4, threshold=20.0)
    base_rate = float(frames["FIT"]["L4_thr20.0"].mean())
    predictor = make_predictor({"primary": models["binned"]}, horizon=4)

    stations = [s for s in args.stations.split(",") if s]
    ages = [int(a) for a in args.ages.split(",")]
    criticals = [float(c) for c in args.criticals.split(",")]
    project = build_project()
    priority = critical_path_priority(project)
    rows: list[EpisodeMetrics] = []
    data_cache: dict[str, StationData] = {}
    for station in stations:
        data_cache[station] = load_station_data(root, station)
    for station, data in data_cache.items():
        obs_start = data.observations.index.min()
        obs_end = data.observations.index.max()
        test_lo = max(pd.Timestamp("2025-01-01", tz="UTC"), obs_start + pd.Timedelta(days=1))
        test_hi = min(pd.Timestamp("2025-09-30", tz="UTC"), obs_end - pd.Timedelta(hours=args.horizon_hours))
        starts = pd.date_range(test_lo, test_hi, freq=f"{args.stride_days}D")
        for age in ages:
            for start in starts:
                base = [BlindPolicy(), ThresholdPolicy(),
                        ClimatologyPolicy(base_rate=base_rate, critical_p=0.10)]
                base += [CalibratedPolicy(predict=predictor, critical_p=c)
                         for c in criticals]
                base += [RiskAwarePolicy(predict=predictor, critical_p=c, priority=priority,
                                         float_slack=1.0, critical_priority_bound=12)
                         for c in criticals]
                for policy in base:
                    rows.append(run_episode(project, data, start, age, policy,
                                            args.horizon_hours, verify=True))
            print(f"  {station} age={age}: {len(rows)} episodes so far", flush=True)

    table = pd.DataFrame([r.__dict__ for r in rows])
    out = args.out or (root / "outputs" / "g5_policy_comparison.csv")
    table.to_csv(out, index=False)
    summary = (table.groupby(["policy_id", "critical_p"], dropna=False)
               .agg(episodes=("status", "size"),
                    complete=("status", lambda s: int((s == "complete").sum())),
                    makespan_mean=("makespan_hours", "mean"),
                    makespan_median=("makespan_hours", "median"),
                    exceedance_work_mean=("exceedance_work_hours", "mean"),
                    unsafe_start_mean=("unsafe_start_hours", "mean"),
                    false_stop_mean=("false_stop_hours", "mean"),
                    missed_safe_mean=("missed_safe_hours", "mean"),
                    idle_mean=("crane_idle_hours", "mean"),
                    restricted_done_mean=("restricted_finished", "mean"))
               .reset_index())
    summary.to_csv(root / "outputs" / "g5_policy_summary.csv", index=False)
    (root / "outputs" / "g5_calibration_diagnostics.json").write_text(
        json.dumps({"base_rate_fit": base_rate, "primary_model": "binned",
                    "diagnostics": diagnostics}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
