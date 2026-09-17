"""Non-anticipative hourly execution of weather-restricted construction operations.

This engine is deliberately separated from ``episode_engine`` (the constructed
verification kernel).  Its job is the empirical contract replay:

* A project is a set of tasks with precedence constraints and an hourly resource
  (crane) demand.
* A *weather-restricted* task may only accumulate progress during hours that
  satisfy the declared operation contract.  The contract gives a start limit, a
  continuation limit, a required consecutive safe duration ``L``, and the
  consequence of an interruption (resume from accumulated progress, or restart).
* A policy never sees the realised weather.  For every hour it may read only
  forecast runs whose ``available_hour <= now``.  The engine fetches the run
  itself and hands the policy that run, so a policy cannot widen its own
  information set.
* Realised weather is read only *after* the hour's decisions are appended to the
  event log, which is what makes the trace auditable by ``verify_execution_trace``.

Separated accounting (all three enter the reported denominator):
    exceedance_work_hours   worked on a restricted task during an observed exceedance
    stopped_hours           withheld a restricted task because the decision rule said stop
    false_stop_hours        a subset of stopped_hours where the observation did NOT exceed
"""
from __future__ import annotations

DEBUG_HOURS: tuple[int, ...] = ()  # set by tests only; empty in production runs

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


class RunView(Protocol):
    """Read-only view of one archived forecast run as seen by a policy."""

    run_id: str
    issue_hour: int
    available_hour: int
    first_interval_hour: int
    scenarios: np.ndarray


@dataclass(frozen=True)
class OperationContract:
    """Declared weather contract for restricted work.

    ``quality`` records the evidence grade of each numeric field so that the
    manuscript can never present an assumed value as a documented one.
    """

    contract_id: str
    start_limit: float
    continuation_limit: float
    required_consecutive_hours: int
    resumable: bool
    gust_measure: str = "preceding_hour_max_gust"
    evidence: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (np.isfinite(self.start_limit) and np.isfinite(self.continuation_limit)):
            raise ValueError("contract limits must be finite")
        if not 0 < self.start_limit <= self.continuation_limit:
            raise ValueError("require 0 < start_limit <= continuation_limit")
        if type(self.required_consecutive_hours) is not int or self.required_consecutive_hours < 1:
            raise ValueError("required_consecutive_hours must be a positive integer")


@dataclass(frozen=True)
class ProjectTask:
    name: str
    duration: int
    predecessors: tuple[str, ...] = ()
    crane_demand: int = 1
    restricted: bool = False
    required_consecutive_hours: int = 1


@dataclass(frozen=True)
class Project:
    project_id: str
    tasks: tuple[ProjectTask, ...]
    crane_capacity: int = 1
    work_day_start: int = 7
    work_day_end: int = 19
    contract: OperationContract | None = None

    def __post_init__(self) -> None:
        if not self.tasks:
            raise ValueError("project needs at least one task")
        names = [t.name for t in self.tasks]
        if len(set(names)) != len(names):
            raise ValueError("duplicate task names")
        if self.crane_capacity < 1:
            raise ValueError("crane capacity must be positive")
        if not 0 <= self.work_day_start < self.work_day_end <= 24:
            raise ValueError("invalid working day window")
        if any(t.restricted for t in self.tasks) and self.contract is None:
            raise ValueError("restricted tasks require an operation contract")
        known = set(names)
        for task in self.tasks:
            if task.duration < 1 or task.crane_demand < 0:
                raise ValueError("invalid duration or crane demand")
            if task.crane_demand > self.crane_capacity:
                raise ValueError("task crane demand exceeds capacity")
            if any(p not in known for p in task.predecessors):
                raise ValueError(f"unknown predecessor in {task.name}")
            if task.restricted and self.contract is not None:
                if task.required_consecutive_hours > max(task.duration,
                                                          self.contract.required_consecutive_hours):
                    raise ValueError("required consecutive hours exceed possible work")
        self._check_acyclic()

    def _check_acyclic(self) -> None:
        remaining = {t.name: set(t.predecessors) for t in self.tasks}
        resolved: set[str] = set()
        while remaining:
            ready = [n for n, p in remaining.items() if p <= resolved]
            if not ready:
                raise ValueError("cyclic project network")
            for name in ready:
                resolved.add(name)
                del remaining[name]

    def by_name(self) -> dict[str, ProjectTask]:
        return {t.name: t for t in self.tasks}


@dataclass(frozen=True)
class HourDecision:
    hour: int
    starts: tuple[str, ...]
    stops: tuple[str, ...]
    resumes: tuple[str, ...]
    run_id: str | None
    run_available_hour: int | None


@dataclass
class ExecutionResult:
    project_id: str
    policy_id: str
    contract_id: str | None
    status: str
    makespan_hours: int | None
    horizon_hours: int
    finished_tasks: tuple[str, ...]
    unfinished_tasks: tuple[str, ...]
    restricted_finished: int
    restricted_total: int
    exceedance_work_hours: int
    unsafe_start_hours: int
    stopped_hours: int
    false_stop_hours: int
    missed_safe_hours: int
    work_hours: int
    decisions: list[HourDecision]
    events: list[dict]

    def as_dict(self) -> dict:
        payload = dict(self.__dict__)
        payload["decisions"] = [d.__dict__ for d in self.decisions]
        return payload


def work_windows(project: Project, horizon: int) -> np.ndarray:
    """Boolean mask of hours inside the declared working day."""
    mask = np.zeros(horizon, dtype=bool)
    for hour in range(horizon):
        if project.work_day_start <= hour % 24 < project.work_day_end:
            mask[hour] = True
    return mask


def required_run_window(contract: OperationContract, task: ProjectTask) -> int:
    """Consecutive forecast hours the contract requires to look safe."""
    return max(contract.required_consecutive_hours, task.required_consecutive_hours)


def window_exceedance_probability(scenarios: np.ndarray, offset: int, length: int,
                                  limit: float) -> float:
    """Empirical P(any hour in the window exceeds ``limit``) from forecast scenarios.

    ``scenarios`` is (n_members, n_hours) of forecast gust in m/s.  When a single
    deterministic member is supplied the result is 0 or 1, which is exactly the
    raw deterministic-threshold behaviour, so calibrated and raw rules share one
    code path.
    """
    if scenarios.ndim != 2:
        raise ValueError("scenarios must be 2-D (members, hours)")
    if offset < 0 or offset + length > scenarios.shape[1]:
        return float("nan")
    block = scenarios[:, offset:offset + length]
    return float(np.mean(np.any(block > limit, axis=1)))


class Policy(Protocol):
    """A decision rule.  ``p`` maps a required window to exceedance probability."""

    policy_id: str

    def decide(self, *, project: Project, contract: OperationContract, hour: int,
               run: RunView | None, progress: dict[str, int],
               active: dict[str, int], completed: frozenset[str],
               free_cranes: int, window_mask: np.ndarray) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Return (tasks to start this hour, tasks to stop now)."""


def run_execution(project: Project, truth: Sequence[float], runs: Sequence[RunView],
                  policy: Policy, *, horizon: int | None = None,
                  truth_available_at: int = 0) -> ExecutionResult:
    """Execute the project hour by hour without anticipative information.

    ``truth`` is the realised hourly gust (m/s) at the site; ``truth[i]`` is the
    observation for hour ``i``.  A restricted task may only accumulate progress
    in an hour whose observation is within the continuation limit.  If the
    observation exceeds the limit while work is in progress, the hour does not
    count as progress: the contract's interruption rule applies (resume with
    accumulated progress, or restart from zero).
    """
    horizon = len(truth) if horizon is None else horizon
    if horizon < 1 or horizon > len(truth):
        raise ValueError("horizon must be covered by the truth series")
    contract = project.contract
    tasks = project.by_name()
    restrict_progress = {t.name: 0 for t in project.tasks if t.restricted}
    completed: set[str] = set()
    completion_hour: dict[str, int] = {}
    active: dict[str, int] = {}
    started_at: dict[str, int] = {}
    decisions: list[HourDecision] = []
    events: list[dict] = []
    exceedance_work = unsafe_starts = stopped_hours = false_stop = missed_safe = work_hours = 0
    mask = work_windows(project, horizon)
    held: set[str] = set()
    last_observed: float | None = None

    def eligible_run(hour: int) -> RunView | None:
        candidates = [r for r in runs if r.available_hour <= hour
                      and r.first_interval_hour <= hour
                      and r.first_interval_hour + r.scenarios.shape[1] > hour]
        if not candidates:
            return None
        return max(candidates, key=lambda r: (r.issue_hour, r.available_hour, r.run_id))

    def crane_use() -> int:
        return sum(tasks[n].crane_demand for n in active)

    for hour in range(horizon):
        # ---- settlement (truth-free bookkeeping) -------------------------
        for name in list(active):
            if active[name] <= 0:
                del active[name]
                completed.add(name)
                completion_hour[name] = hour
        if len(completed) == len(project.tasks):
            break

        run = eligible_run(hour)
        free = project.crane_capacity - crane_use()
        stops: tuple[str, ...] = ()
        starts: tuple[str, ...] = ()
        # The realised gust for hour ``hour`` is not observable at decision time.
        # Every policy therefore sees the same last-observation stay signal; a
        # policy with forecast information may add its own, stricter stop rule.
        stay_allowed = {n: (last_observed is not None
                            and last_observed <= contract.continuation_limit)
                        for n in active if tasks[n].restricted}
        if mask[hour]:
            starts, stops = policy.decide(
                project=project, contract=contract, hour=hour, run=run,
                progress=restrict_progress, active=active,
                completed=frozenset(completed), free_cranes=free, window_mask=mask,
                stay_allowed=stay_allowed)

        # ---- apply stop decisions before any progress --------------------
        for name in stops:
            if name not in active:
                continue
            task = tasks[name]
            del active[name]
            if not contract.resumable:
                restrict_progress[name] = 0

        # ---- apply starts -------------------------------------------------
        # The policy returns an ordered wish list; the engine applies it under the
        # real resource constraint and logs only what was actually applied, so the
        # released trace can be re-derived independently.  A policy that wants to
        # control *which* candidate wins a scarce resource expresses that in the
        # order of its list, which is precisely the dispatcher's decision.
        free = project.crane_capacity - crane_use()
        applied: list[str] = []
        for name in starts:
            task = tasks[name]
            if task.name in active or task.name in completed:
                continue
            if not set(task.predecessors) <= completed:
                continue
            if task.crane_demand > free:
                continue
            active[name] = task.duration
            started_at[name] = hour
            free -= task.crane_demand
            applied.append(name)
        if hour in DEBUG_HOURS:
            print(f"[debug] hour={hour} offered={starts} applied={tuple(applied)} "
                  f"stops={stops} active_after_starts={sorted(active)} "
                  f"completed={sorted(completed)}")

        decisions.append(HourDecision(
            hour=hour, starts=tuple(sorted(applied)), stops=tuple(sorted(stops)),
            resumes=tuple(sorted(n for n in active if started_at.get(n, hour) < hour)),
            run_id=run.run_id if run else None,
            run_available_hour=run.available_hour if run else None))

        # ---- realised weather is read only now ---------------------------
        observed = float(truth[hour])
        last_observed = observed
        # ``active_at_start`` is captured before any hourly decrement so that the
        # independent trace check can reproduce the crane loading of this hour.
        active_at_start = sorted(active)
        event = {
            "hour": hour,
            "observed_gust": observed,
            "active": active_at_start,
            "starts": sorted(applied),
            "stops": sorted(stops),
            "forecast_run_id": run.run_id if run else None,
            "forecast_run_available_hour": run.available_hour if run else None,
            "forecast_run_window_offset": (hour - run.first_interval_hour) if run else None,
        }
        breaching: list[str] = []
        for name in list(active):
            task = tasks[name]
            if not task.restricted:
                active[name] -= 1
            elif observed > contract.continuation_limit:
                breaching.append(name)
                exceedance_work += 1
                work_hours += 1
                if not contract.resumable:
                    restrict_progress[name] = 0
                del active[name]
                continue
            else:
                active[name] -= 1
                restrict_progress[name] += 1
                work_hours += 1
            if active[name] <= 0:
                del active[name]
                completed.add(name)
                completion_hour[name] = hour + 1
        event["breaching_tasks"] = sorted(breaching)

        # A start is unsafe when the block the contract requires for a new start
        # (the start limit, not the continuation limit) was exceeded -- judged from
        # the forecast the policy actually held at that hour, with the observation
        # as a fallback when no forecast was available.  This is the exposure the
        # start limit exists to prevent, and no policy can be credited for avoiding
        # it by accident.
        for name in applied:
            task = tasks[name]
            if not task.restricted:
                continue
            forecast_block = None
            if run is not None:
                lo = (hour - run.first_interval_hour)
                hi = lo + max(contract.required_consecutive_hours, task.required_consecutive_hours)
                if 0 <= lo and hi <= run.scenarios.shape[1]:
                    forecast_block = run.scenarios[:, lo:hi]
            judged_high = False
            if forecast_block is not None:
                judged_high = bool(np.any(forecast_block > contract.start_limit))
            if judged_high or observed > contract.start_limit:
                unsafe_starts += 1

        # Opportunity accounting.  ``missed_safe_hours`` counts hours in which a
        # restricted, precedence-ready task existed, the contract permitted work
        # (observation inside the continuation limit), and the forecast did not
        # claim a breach -- but the policy still held the crane.  Those are the
        # hours a false alarm actually costs, and they are counted separately from
        # hours in which the policy was responding to a real or forecast breach.
        if mask[hour] and observed <= contract.continuation_limit:
            busy = crane_use()
            forecast_clean = True
            if run is not None:
                block = run.scenarios[:, (hour - run.first_interval_hour):(hour - run.first_interval_hour) + 1]
                forecast_clean = block is not None and not bool(
                    np.any(block > contract.continuation_limit))
            for task in project.tasks:
                if not task.restricted or task.name in completed or task.name in active:
                    continue
                if not set(task.predecessors) <= completed:
                    continue
                if task.crane_demand > project.crane_capacity - busy:
                    continue
                # A restricted task was ready, the contract permitted work and the
                # crane was free: this is available weather-time the policy chose not
                # to use, i.e. its opportunity cost, however the decision arose.
                missed_safe += 1
                if forecast_clean:
                    false_stop += 1
                held.add(task.name)
                break
        if mask[hour] and stops:
            stopped_hours += 1
        events.append(event)

    limited = [t.name for t in project.tasks if t.restricted]
    finished = [name for name in limited if name in completed]
    status = "complete" if len(completed) == len(project.tasks) else "incomplete"
    makespan = None
    if status == "complete":
        makespan = max(completion_hour.values())
    return ExecutionResult(
        project_id=project.project_id, policy_id=policy.policy_id,
        contract_id=contract.contract_id if contract else None,
        status=status, makespan_hours=makespan, horizon_hours=horizon,
        finished_tasks=tuple(sorted(completed)),
        unfinished_tasks=tuple(sorted(set(tasks) - completed)),
        restricted_finished=len(finished), restricted_total=len(limited),
        exceedance_work_hours=exceedance_work, unsafe_start_hours=unsafe_starts,
        stopped_hours=stopped_hours,
        false_stop_hours=false_stop, missed_safe_hours=missed_safe,
        work_hours=work_hours,
        decisions=decisions, events=events)


def verify_execution_trace(project: Project, result: ExecutionResult,
                           truth: Sequence[float]) -> None:
    """Independent audit of a released trace: precedence, capacity, information, contract."""
    tasks = project.by_name()
    contract = project.contract
    started: dict[str, int] = {}
    active: dict[str, int] = {}
    progress = {t.name: 0 for t in project.tasks if t.restricted}
    completed: set[str] = set()
    for event in result.events:
        hour = event["hour"]
        if event["forecast_run_available_hour"] is not None and \
                event["forecast_run_available_hour"] > hour:
            raise AssertionError("trace used a forecast run that was not yet available")
        if event["observed_gust"] is not None and not np.isfinite(event["observed_gust"]):
            raise AssertionError("non-finite observation inside trace")
        for name in event["starts"]:
            if not set(tasks[name].predecessors) <= completed:
                raise AssertionError(f"precedence violation starting {name} at hour {hour}")
            if name in active:
                raise AssertionError(f"task {name} started while already active")
            active[name] = tasks[name].duration
            started[name] = hour
        if sum(tasks[n].crane_demand for n in active) > project.crane_capacity:
            raise AssertionError("crane capacity exceeded in trace")
        if sorted(active) != list(event["active"]):
            raise AssertionError(
                f"trace active set at hour {hour} does not match the reconstructed state: "
                f"reconstructed={sorted(active)} logged={list(event['active'])} "
                f"starts={event['starts']} stops={event['stops']}")
        for name in list(active):
            task = tasks[name]
            if not task.restricted:
                active[name] -= 1
            elif event["observed_gust"] > contract.continuation_limit:
                if not contract.resumable:
                    progress[name] = 0
                del active[name]
                continue
            else:
                active[name] -= 1
                progress[name] += 1
            if active.get(name) == 0:
                del active[name]
                completed.add(name)
    if result.status == "complete" and len(completed) != len(project.tasks):
        raise AssertionError("trace claims completion but tasks remain")
    for name, hours in progress.items():
        required = max(tasks[name].required_consecutive_hours,
                       contract.required_consecutive_hours)
        if name in completed and hours < required:
            raise AssertionError(
                f"task {name} completed with {hours} safe hours, contract requires {required}")

