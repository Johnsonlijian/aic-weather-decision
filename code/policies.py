"""Decision policies for weather-restricted construction operations.

Every policy in this module sees exactly the same interface: the project, the
contract, the current hour, and the single archived forecast run the engine
declares eligible at that hour.  None of them can reach the realised weather.
That is what makes the policy comparison fair and the replay non-anticipative.

The policies form the pre-registered ladder:

    blind        ignore weather entirely
    raw          deterministic threshold on the uncalibrated forecast
    clim         constant climatological exceedance probability (weather knowledge
                 without forecast information)
    calibrated   decision-aligned P(exceedance in the block) from the fitted
                 calibrator, compared against a critical probability
    riskaware    adds precedence/criticality ordering on top of the calibrated
                 risk rule

``critical_p`` is the maximum acceptable probability of a contract exceedance
during the block.  It is the single tuning parameter and the whole sweep is
reported; a policy is never credited with its best value only.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from operation_engine import (
    OperationContract,
    Project,
    ProjectTask,
    RunView,
    required_run_window,
)


def _forecast_block(run: RunView, hour: int, length: int) -> np.ndarray | None:
    offset = hour - run.first_interval_hour
    if offset < 0 or offset + length > run.scenarios.shape[1]:
        return None
    return run.scenarios[:, offset:offset + length]


def _candidates(project: Project, completed: frozenset[str],
                active: dict[str, int], free_cranes: int) -> list[ProjectTask]:
    ready = [t for t in project.tasks
             if t.name not in completed and t.name not in active
             and set(t.predecessors) <= completed and t.crane_demand <= free_cranes]
    return sorted(ready, key=lambda t: (-t.duration, t.name))


@dataclass
class BlindPolicy:
    """Ignores weather.  The contract's own stay rule still applies.

    At hour ``h`` the realised observation of hour ``h`` does not exist yet, so
    even a weather-blind planner must use the most recent *observation* as the
    stay signal.  Doing otherwise would hand the blind baseline an information
    advantage that no real site has.
    """

    policy_id: str = "blind"

    def decide(self, **kw) -> tuple[tuple[str, ...], tuple[str, ...]]:
        project: Project = kw["project"]
        contract: OperationContract = kw["contract"]
        active: dict[str, int] = kw["active"]
        stays = kw.get("stay_allowed", {})
        stops = tuple(n for n in active
                      if project.by_name()[n].restricted and not stays.get(n, True))
        starts, free = [], kw["free_cranes"]
        for task in _candidates(project, kw["completed"], active, free):
            if task.restricted and not stays.get(task.name, True):
                continue
            starts.append(task.name)
            free -= task.crane_demand
        return tuple(starts), stops


@dataclass
class ThresholdPolicy:
    """Raw deterministic rule: work only if the whole required block looks safe.

    No calibration is applied, so this is exactly what a site does when it reads
    a gust forecast and compares it with the crane limit.  The start decision
    uses the start limit; the stay decision uses the continuation limit.
    """

    policy_id: str = "raw"

    def decide(self, **kw) -> tuple[tuple[str, ...], tuple[str, ...]]:
        project: Project = kw["project"]
        contract: OperationContract = kw["contract"]
        hour: int = kw["hour"]
        run = kw["run"]
        active: dict[str, int] = kw["active"]
        if run is None:
            return (), tuple(n for n in active if project.by_name()[n].restricted)
        current = _forecast_block(run, hour, 1)
        stay_ok = current is not None and not bool(np.any(current > contract.continuation_limit))
        stops = tuple(n for n in active
                      if project.by_name()[n].restricted and not stay_ok)
        if not stay_ok:
            return (), stops
        starts, free = [], kw["free_cranes"]
        for task in _candidates(project, kw["completed"], active, free):
            if not task.restricted:
                starts.append(task.name)
                free -= task.crane_demand
                continue
            length = required_run_window(contract, task)
            block = _forecast_block(run, hour, length)
            if block is None:
                continue
            if bool(np.any(block > contract.continuation_limit)):
                continue
            lookahead = _forecast_block(run, hour, min(length, contract.required_consecutive_hours))
            if lookahead is not None and bool(np.any(lookahead > contract.start_limit)):
                continue
            starts.append(task.name)
            free -= task.crane_demand
        return tuple(starts), stops


@dataclass
class ClimatologyPolicy:
    """Uses only the unconditional exceedance rate: no forecast information."""

    base_rate: float = 0.0
    critical_p: float = 0.1
    policy_id: str = "clim"
    _gate: bool | None = None
    _gate_day: int | None = None

    def reset(self) -> None:
        self._gate = None
        self._gate_day = None

    def decide(self, **kw) -> tuple[tuple[str, ...], tuple[str, ...]]:
        project: Project = kw["project"]
        hour: int = kw["hour"]
        active: dict[str, int] = kw["active"]
        stays = kw.get("stay_allowed", {})
        day = hour // 24
        if self._gate_day != day:
            self._gate = bool(self.base_rate <= self.critical_p)
            self._gate_day = day
        stops = tuple(n for n in active if project.by_name()[n].restricted
                      and not (self._gate and stays.get(n, False)))
        starts, free = [], kw["free_cranes"]
        if self._gate:
            for task in _candidates(project, kw["completed"], active, free):
                if task.restricted and not stays.get(task.name, True):
                    continue
                starts.append(task.name)
                free -= task.crane_demand
        return tuple(starts), stops


@dataclass
class CalibratedPolicy:
    """Decision-aligned calibrated risk rule.

    ``predict`` receives the block of forecast gust values covering the required
    consecutive window and returns the calibrated probability that the block
    contains a contract exceedance.  The day-level gate is taken once per day;
    the hour-level stop rule re-checks the *current* hour forecast.

    Task ordering is the shared neutral rule (longest first) so that the
    comparison against the other policies isolates the risk rule itself rather
    than a dispatching side effect.
    """

    predict: object = None
    critical_p: float = 0.1
    policy_id: str = "calibrated"
    base_rate: float | None = None
    _gate: bool | None = None
    _gate_day: int | None = None
    _gate_p: float = float("nan")

    def reset(self) -> None:
        self._gate = None
        self._gate_day = None
        self._gate_p = float("nan")

    def _p_any(self, contract: OperationContract, hour: int, run, length: int) -> float:
        """Calibrated probability that the required block contains an exceedance.

        ``predict`` is called as ``predict(run, hour, length)`` so that the caller
        controls exactly which archived lead supplies the predictor.  Keeping that
        choice outside the policy is what guarantees the calibrator and the policy
        read the same forecast quantity.
        """
        if run is None:
            return float("nan")
        offset = hour - run.first_interval_hour
        if offset < 0 or offset + length > run.scenarios.shape[1]:
            return float("nan")
        return float(self.predict(run, hour, length))

    def decide(self, **kw) -> tuple[tuple[str, ...], tuple[str, ...]]:
        project: Project = kw["project"]
        contract: OperationContract = kw["contract"]
        hour: int = kw["hour"]
        run = kw["run"]
        active: dict[str, int] = kw["active"]
        stays = kw.get("stay_allowed", {})
        day = hour // 24
        if self._gate_day != day:
            self._gate_p = self._p_any(contract, hour, run,
                                       contract.required_consecutive_hours)
            self._gate = bool(np.isfinite(self._gate_p) and self._gate_p <= self.critical_p)
            self._gate_day = day

        # Hour-level stop rule: the forecast for the current hour, plus the
        # calibrated probability of an exceedance inside the next required block.
        # The stay decision looks at a short forward block, independently of the
        # day gate: a task already in progress is stopped as soon as the calibrated
        # risk over the next few hours exceeds the same critical probability.
        block_p = self._p_any(contract, hour, run, 4)
        forecast_breach = False
        if run is not None:
            block = _forecast_block(run, hour, 1)
            forecast_breach = block is not None and bool(np.any(block > contract.continuation_limit))
        stop_risk = forecast_breach or (np.isfinite(block_p) and block_p > self.critical_p)
        stops = tuple(n for n in active if project.by_name()[n].restricted
                      and (stop_risk or not stays.get(n, False)))

        starts, free = [], kw["free_cranes"]
        for task in _candidates(project, kw["completed"], active, free):
            if task.restricted and not (self._gate and stays.get(task.name, True)):
                continue
            starts.append(task.name)
            free -= task.crane_demand
        return tuple(starts), tuple(stops)


@dataclass
class RiskAwarePolicy(CalibratedPolicy):
    """Calibrated risk rule plus criticality-ordered dispatching and float slack.

    ``float_slack`` postpones a restricted task whose calibrated block risk is
    non-zero but still below the hard stop threshold, provided the task is not on
    the critical path.  That is the "use the forecast to reorder, not only to
    stop" behaviour a scheduler would actually apply.
    """

    policy_id: str = "riskaware"
    float_slack: float = 0.0
    priority: dict[str, int] | None = None
    critical_priority_bound: int = 0

    def decide(self, **kw) -> tuple[tuple[str, ...], tuple[str, ...]]:
        project: Project = kw["project"]
        contract: OperationContract = kw["contract"]
        hour: int = kw["hour"]
        run = kw["run"]
        active: dict[str, int] = kw["active"]
        stays = kw.get("stay_allowed", {})
        day = hour // 24
        if self._gate_day != day:
            self._gate_p = self._p_any(contract, hour, run,
                                       contract.required_consecutive_hours)
            self._gate = bool(np.isfinite(self._gate_p) and self._gate_p <= self.critical_p)
            self._gate_day = day
        # The stay decision looks at a short forward block, independently of the
        # day gate: a task already in progress is stopped as soon as the calibrated
        # risk over the next few hours exceeds the same critical probability.
        block_p = self._p_any(contract, hour, run, 4)
        forecast_breach = False
        if run is not None:
            block = _forecast_block(run, hour, 1)
            forecast_breach = block is not None and bool(np.any(block > contract.continuation_limit))
        stop_risk = forecast_breach or (np.isfinite(block_p) and block_p > self.critical_p)
        stops = tuple(n for n in active if project.by_name()[n].restricted
                      and (stop_risk or not stays.get(n, False)))

        starts, free = [], kw["free_cranes"]
        candidates = _candidates(project, kw["completed"], active, free)
        if self.priority:
            candidates = sorted(candidates, key=lambda t: (-self.priority.get(t.name, 0), t.name))
        for task in candidates:
            if task.restricted:
                if not (self._gate and stays.get(task.name, True)):
                    continue
                if (self.float_slack > 0 and self.priority
                        and self.priority.get(task.name, 0) < self.critical_priority_bound
                        and np.isfinite(block_p) and block_p > self.critical_p):
                    continue
            starts.append(task.name)
            free -= task.crane_demand
        return tuple(starts), tuple(stops)


def critical_path_priority(project: Project) -> dict[str, int]:
    """Longest remaining path (in hours) from each task to project end."""
    by_name = project.by_name()
    successors: dict[str, list[str]] = {t.name: [] for t in project.tasks}
    for task in project.tasks:
        for pred in task.predecessors:
            successors[pred].append(task.name)
    order: list[str] = []
    remaining = {t.name: set(t.predecessors) for t in project.tasks}
    while remaining:
        ready = sorted(n for n, p in remaining.items() if p <= set(order))
        if not ready:
            raise ValueError("cyclic network")
        order.extend(ready)
        for name in ready:
            del remaining[name]
    score: dict[str, int] = {}
    for name in reversed(order):
        score[name] = by_name[name].duration + max(
            (score[s] for s in successors[name]), default=0)
    return score


def make_project(project_id: str, contract: OperationContract, *,
                 restricted_plan: list[tuple[str, int, tuple[str, ...], int]],
                 unrestricted_plan: list[tuple[str, int, tuple[str, ...]]] = ()) -> Project:
    """Convenience constructor used by the experiment definition files."""
    tasks = []
    for name, duration, predecessors, consecutive in restricted_plan:
        tasks.append(ProjectTask(name=name, duration=duration, predecessors=tuple(predecessors),
                                 crane_demand=1, restricted=True,
                                 required_consecutive_hours=consecutive))
    for name, duration, predecessors in unrestricted_plan:
        tasks.append(ProjectTask(name=name, duration=duration, predecessors=tuple(predecessors),
                                 crane_demand=0, restricted=False))
    return Project(project_id=project_id, tasks=tuple(tasks), crane_capacity=1, contract=contract)
