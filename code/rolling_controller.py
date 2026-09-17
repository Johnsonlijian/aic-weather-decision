"""Minimal non-anticipative rolling controller for the AiC research prototype.

The controller receives only a forecast snapshot and observed project state. It
never receives the evaluator's hidden truth trajectory. The module is a
transparent research component, not a field safety or lifting-control system.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from core import ADMISSIBLE, Task, scenario_window_probability, window_status


@dataclass(frozen=True)
class OperationContract:
    """Weather rule for one operation under the declared slot convention."""

    start_limit: float
    continuation_limit: float


@dataclass(frozen=True)
class ControllerContext:
    """Information visible to the controller at one decision epoch.

    ``forecast_scenarios`` is a forecast snapshot available at the epoch. It is
    not an observed or hidden future truth path. Rows are scenario members and
    columns start at ``decision_time``.
    """

    decision_time: int
    forecast_scenarios: np.ndarray
    completed: frozenset[str] = frozenset()
    active: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        s = np.asarray(self.forecast_scenarios, dtype=float)
        if s.ndim != 2 or s.shape[0] == 0 or s.shape[1] == 0:
            raise ValueError("forecast_scenarios must be nonempty [scenario, time]")
        if not np.isfinite(s).all():
            raise ValueError("forecast snapshot cannot contain missing members")
        if self.decision_time < 0:
            raise ValueError("decision_time must be nonnegative")
        object.__setattr__(self, "forecast_scenarios", s)


@dataclass(frozen=True)
class Action:
    task_name: str
    start: int
    window_probability: float
    policy_id: str


def _validate_contracts(tasks: Sequence[Task],
                        contracts: Mapping[str, OperationContract]) -> None:
    names = {t.name for t in tasks}
    missing = names - set(contracts)
    if missing:
        raise ValueError(f"missing operation contracts: {sorted(missing)}")
    extra = set(contracts) - names
    if extra:
        raise ValueError(f"contracts for unknown tasks: {sorted(extra)}")


def _ready_tasks(tasks: Sequence[Task], context: ControllerContext) -> list[Task]:
    done = set(context.completed)
    active = set(context.active)
    unknown = (done | active) - {t.name for t in tasks}
    if unknown:
        raise ValueError(f"unknown completed/active task: {sorted(unknown)}")
    return [t for t in tasks
            if t.name not in done and t.name not in active
            and set(t.predecessors) <= done]


def _candidate_probability(task: Task, contract: OperationContract,
                           start: int, context: ControllerContext) -> float | None:
    offset = start - context.decision_time
    if offset < 0 or offset + task.duration > context.forecast_scenarios.shape[1]:
        return None
    probs = scenario_window_probability(
        context.forecast_scenarios[:, offset:offset + task.duration],
        task.duration, contract.start_limit, contract.continuation_limit,
    )
    # The sliced matrix has exactly one candidate start, so this is scalar.
    return float(probs[0])


def choose_action(tasks: Sequence[Task],
                  contracts: Mapping[str, OperationContract],
                  context: ControllerContext,
                  policy_id: str = "risk_aware") -> Action | None:
    """Choose one action from visible information only.

    Policies:
    ``earliest`` and ``forecast_agnostic`` choose the earliest visible legal
    start. ``risk_aware`` maximises the forecast complete-window probability,
    then chooses the earliest start and lexical task name as deterministic
    tie-breaks. Candidates outside the visible forecast snapshot are ignored.
    """
    if policy_id not in {"earliest", "forecast_agnostic", "risk_aware"}:
        raise ValueError("unknown policy_id")
    _validate_contracts(tasks, contracts)
    candidates: list[tuple[float, int, str]] = []
    for task in _ready_tasks(tasks, context):
        for start in sorted(task.legal_starts):
            if start < context.decision_time:
                continue
            q = _candidate_probability(task, contracts[task.name], start, context)
            if q is None:
                continue
            score = q if policy_id == "risk_aware" else 0.0
            candidates.append((score, start, task.name))
    if not candidates:
        return None
    if policy_id == "risk_aware":
        # Maximise q; ties choose earliest start, then stable task name.
        score, start, name = sorted(candidates,
                                    key=lambda x: (-x[0], x[1], x[2]))[0]
    else:
        score, start, name = sorted(candidates,
                                    key=lambda x: (x[1], x[2]))[0]
    return Action(name, start, float(score if policy_id == "risk_aware" else
                                     _candidate_probability(
                                         next(t for t in tasks if t.name == name),
                                         contracts[name], start, context)),
                  policy_id)


def evaluate_action(weather_truth: Sequence[float], action: Action,
                    task: Task, contract: OperationContract) -> int:
    """Evaluate a chosen action against hidden truth held by the evaluator."""
    values = np.asarray(weather_truth, dtype=float)
    if action.start < 0 or action.start + task.duration > len(values):
        raise ValueError("truth path does not cover action window")
    label = window_status(values[action.start:action.start + task.duration],
                          task.duration, contract.start_limit,
                          contract.continuation_limit)
    return int(label[0]) if len(label) else -1


def assert_same_action_for_hidden_futures(tasks: Sequence[Task],
                                          contracts: Mapping[str, OperationContract],
                                          context_a: ControllerContext,
                                          context_b: ControllerContext) -> None:
    """Fail unless two contexts with the same visible information act alike.

    This helper is intentionally strict: callers must construct the two
    contexts with identical visible fields and vary only evaluator-side hidden
    truth outside this module. A mismatch indicates that a future path has
    leaked into the controller interface or that tie-breaking is unstable.
    """
    if context_a.decision_time != context_b.decision_time:
        raise ValueError("visible decision times differ")
    if not np.array_equal(context_a.forecast_scenarios,
                          context_b.forecast_scenarios):
        raise ValueError("visible forecast snapshots differ")
    if context_a.completed != context_b.completed or context_a.active != context_b.active:
        raise ValueError("visible project states differ")
    a = choose_action(tasks, contracts, context_a, "risk_aware")
    b = choose_action(tasks, contracts, context_b, "risk_aware")
    if a != b:
        raise AssertionError(f"non-anticipativity violation: {a!r} != {b!r}")
