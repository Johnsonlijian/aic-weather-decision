"""Hourly non-preemptive project replay with a truth-blind dispatch interface.

Completed intervals determine outcomes after decisions. A breach or an unknown
active-operation interval terminates an episode as unresolved; no invented
recovery is allowed. All unfinished episodes retain the common cutoff loss.
"""
from dataclasses import dataclass
from typing import Sequence
import math

import numpy as np

from core import scenario_window_probability


@dataclass(frozen=True)
class Activity:
    name: str
    duration: int
    predecessors: tuple[str, ...]
    demand: tuple[int, ...]
    sensitive: bool = False
    start_limit: float = 11.1
    continuation_limit: float = 20.0


@dataclass(frozen=True)
class ForecastRun:
    run_id: str
    issue_hour: int
    available_hour: int
    first_interval_hour: int
    scenarios: np.ndarray
    record_type: str = 'constructed_forecast'

    def __post_init__(self):
        values = np.array(self.scenarios, dtype=float, copy=True)
        if values.ndim != 2 or min(values.shape) < 1 or not np.isfinite(values).all():
            raise ValueError('forecast scenarios must be a finite nonempty matrix')
        if self.available_hour < self.issue_hour:
            raise ValueError('availability predates initialisation')
        values.setflags(write=False)
        object.__setattr__(self, 'scenarios', values)


def validate_network(tasks: Sequence[Activity], capacity: Sequence[int]) -> tuple[str, ...]:
    if not tasks or not capacity or any(type(c) is not int or c <= 0 for c in capacity):
        raise ValueError('nonempty network and positive integer capacities required')
    by_name = {t.name: t for t in tasks}
    if len(by_name) != len(tasks):
        raise ValueError('duplicate activity names')
    for t in tasks:
        if type(t.duration) is not int or t.duration < 0 or len(t.demand) != len(capacity):
            raise ValueError('invalid activity duration or resource dimensions')
        if any(type(x) is not int or x < 0 or x > c for x, c in zip(t.demand, capacity)):
            raise ValueError('invalid or infeasible resource demand')
        if t.duration == 0 and (any(t.demand) or t.sensitive):
            raise ValueError('zero-duration activities must be resource-free insensitive milestones')
        if len(t.predecessors) != len(set(t.predecessors)):
            raise ValueError('duplicate predecessor')
        if not all(p in by_name for p in t.predecessors):
            raise ValueError('unknown predecessor')
        if not (math.isfinite(t.start_limit) and math.isfinite(t.continuation_limit)
                and 0 <= t.start_limit <= t.continuation_limit):
            raise ValueError('invalid operation thresholds')
    order, remaining = [], set(by_name)
    while remaining:
        ready = sorted(n for n in remaining if set(by_name[n].predecessors) <= set(order))
        if not ready:
            raise ValueError('cyclic project network')
        order.extend(ready); remaining.difference_update(ready)
    return tuple(order)


def downstream_priorities(tasks: Sequence[Activity], order: Sequence[str]) -> dict[str, int]:
    by_name = {t.name: t for t in tasks}
    successors = {t.name: [] for t in tasks}
    for t in tasks:
        for pred in t.predecessors:
            successors[pred].append(t.name)
    score = {}
    for name in reversed(order):
        score[name] = by_name[name].duration + max((score[s] for s in successors[name]), default=0)
    return score


def latest_available(runs: Sequence[ForecastRun], now: int) -> ForecastRun | None:
    eligible = [r for r in runs if r.available_hour <= now
                and r.first_interval_hour <= now < r.first_interval_hour + r.scenarios.shape[1]]
    return max(eligible, key=lambda r: (r.issue_hour, r.available_hour, r.run_id), default=None)


def choose_starts(tasks: Sequence[Activity], completed: frozenset[str],
                  active_names: frozenset[str], free_capacity: tuple[int, ...],
                  now: int, run: ForecastRun | None, priorities: dict[str, int],
                  policy: str, tolerance: float, state_mode: str = 'asymmetric') -> tuple[str, ...]:
    """Choose immediate starts. No realised current/future weather is an input.

    ``blind`` and ``window`` share priorities, capacities and permitted actions.
    Forecast treatment is supplied by ``run``; state_mode changes planning only.
    The evaluator always retains the actual declared start/continuation rules.
    """
    if policy not in ('blind', 'window') or state_mode not in ('asymmetric', 'symmetric'):
        raise ValueError('unknown policy or state mode')
    if not 0 <= tolerance <= 1:
        raise ValueError('invalid planning tolerance')
    free = list(free_capacity)
    chosen = []
    for t in sorted(tasks, key=lambda t: (-priorities[t.name], t.name)):
        if (t.duration == 0 or t.name in completed or t.name in active_names
                or not set(t.predecessors) <= completed):
            continue
        if any(d > c for d, c in zip(t.demand, free)):
            continue
        if t.sensitive and policy == 'window':
            if run is None:
                continue
            offset = now - run.first_interval_hour
            if offset < 0 or offset + t.duration > run.scenarios.shape[1]:
                continue
            continuation = t.continuation_limit if state_mode == 'asymmetric' else t.start_limit
            q = float(scenario_window_probability(
                run.scenarios[:, offset:offset + t.duration], t.duration,
                t.start_limit, continuation)[0])
            if q + 1e-12 < 1 - tolerance:
                continue
        chosen.append(t.name)
        free = [c - d for c, d in zip(free, t.demand)]
    return tuple(chosen)


def run_episode(tasks: Sequence[Activity], capacity: Sequence[int],
                truth: Sequence[float], runs: Sequence[ForecastRun], *,
                policy: str = 'window', tolerance: float = .1,
                state_mode: str = 'asymmetric', cutoff: int | None = None,
                source_type: str = 'constructed_verification') -> dict:
    order = validate_network(tasks, capacity)
    priority = downstream_priorities(tasks, order)
    by_name = {t.name: t for t in tasks}
    g = np.asarray(truth, dtype=float)
    if g.ndim != 1:
        raise ValueError('truth must be one-dimensional')
    horizon = len(g) if cutoff is None else cutoff
    if type(horizon) is not int or horizon < 1 or horizon > len(g):
        raise ValueError('cutoff must be covered by supplied truth')
    if source_type == 'operational_archive_replay' and any(
            r.record_type != 'operational_archive' for r in runs):
        raise ValueError('non-operational forecast in operational archive replay')
    completed, active, started, events = {}, {}, {}, []

    def settle(now):
        for name in list(active):
            if active[name]['end'] <= now:
                completed[name] = active[name]['end']
                del active[name]
        for name in order:
            t = by_name[name]
            if (t.duration == 0 and name not in completed
                    and set(t.predecessors) <= set(completed)):
                completed[name] = now

    def result(status, now, breach=0, unresolved_reason=None):
        complete = status == 'complete'
        return {'source_type': source_type, 'policy_id': policy, 'state_mode': state_mode,
                'risk_setting': tolerance, 'status': status, 'completed': complete,
                'completion_time_hours': now if complete else None,
                'restricted_completion_hours': now if complete else horizon,
                'admin_cutoff_hours': horizon, 'window_breach_count': breach,
                'unresolved': status == 'unresolved', 'unresolved_reason': unresolved_reason,
                'task_count': len(tasks), 'completed_tasks': len(completed),
                'remaining_tasks': sorted(set(by_name) - set(completed)),
                'starts': started, 'completion_times': completed, 'events': events}

    for now in range(horizon):
        settle(now)
        if len(completed) == len(tasks):
            return result('complete', now)
        free = tuple(cap - sum(by_name[n].demand[k] for n in active)
                     for k, cap in enumerate(capacity))
        run = latest_available(runs, now)
        starts = choose_starts(tasks, frozenset(completed), frozenset(active), free,
                               now, run, priority, policy, tolerance, state_mode)
        for name in starts:
            started[name] = now
            active[name] = {'start': now, 'end': now + by_name[name].duration}
        event = {'hour': now, 'forecast_run_id': run.run_id if run else None,
                 'forecast_available_hour': run.available_hour if run else None,
                 'starts': list(starts), 'active': sorted(active),
                 'resource_use': [sum(by_name[n].demand[k] for n in active)
                                  for k in range(len(capacity))]}
        if any(u > c for u, c in zip(event['resource_use'], capacity)):
            raise AssertionError('resource overflow in executor')
        # Truth is accessed only after the dispatch has been irrevocably logged.
        events.append(event)
        missing, breaches = [], []
        for name, state in active.items():
            task = by_name[name]
            if not task.sensitive:
                continue
            if not np.isfinite(g[now]):
                missing.append(name)
            elif g[now] > (task.start_limit if state['start'] == now else task.continuation_limit):
                breaches.append(name)
        if missing or breaches:
            event.update(missing_active=missing, breached_tasks=breaches)
            return result('unresolved', now + 1, len(breaches),
                          'window_breach' if breaches else 'missing_active_weather')
    settle(horizon)
    return result('complete' if len(completed) == len(tasks) else 'censored', horizon)


def verify_episode_trace(tasks: Sequence[Activity], capacity: Sequence[int], result: dict) -> None:
    """Independent conservation and ordering checks from the released event log."""
    by_name = {t.name: t for t in tasks}
    starts = result['starts']
    for name, start in starts.items():
        for pred in by_name[name].predecessors:
            if result['completion_times'].get(pred, math.inf) > start:
                raise AssertionError('trace precedence violation')
    for event in result['events']:
        if event['forecast_available_hour'] is not None and event['forecast_available_hour'] > event['hour']:
            raise AssertionError('future forecast in trace')
        reconstructed = [sum(t.demand[k] for t in tasks if t.name in starts
                             and starts[t.name] <= event['hour'] < starts[t.name] + t.duration)
                         for k in range(len(capacity))]
        if reconstructed != event['resource_use'] or any(x > c for x, c in zip(reconstructed, capacity)):
            raise AssertionError('trace resource violation')
    if not result['completed'] and result['restricted_completion_hours'] != result['admin_cutoff_hours']:
        raise AssertionError('failed or censored episode omitted from cutoff loss')
