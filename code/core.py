"""Auditable research primitives, NOT a field-operation or safety-control system.

This v1 implements window labels, information-availability checks and an exact
small-instance deterministic scheduling model. It is NOT the full proposed
forecast-calibration / online recourse system. All time units in the toy solver
are abstract slots unless a separate, sourced mapping is provided.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence
import math
import numpy as np

UNKNOWN = -1
INADMISSIBLE = 0
ADMISSIBLE = 1


def _validate_rule(duration: int, start_limit: float, continuation_limit: float) -> None:
    if not isinstance(duration, (int, np.integer)) or duration < 1:
        raise ValueError('duration must be a positive integer')
    if not (math.isfinite(start_limit) and math.isfinite(continuation_limit)):
        raise ValueError('thresholds must be finite')
    if not 0 <= start_limit <= continuation_limit:
        raise ValueError('require 0 <= start_limit <= continuation_limit')


def window_status(values: Sequence[float], duration: int,
                  start_limit: float, continuation_limit: float) -> np.ndarray:
    """Three-valued label for each COMPLETE candidate start window.

    -1: unresolved due to a missing value and no observed contradiction;
     0: at least one observed threshold violation;
     1: all required values observed and admissible.
    There are max(T-duration+1, 0) labels, not T padded pseudo-observations.
    Equality is admissible by the declared mathematical convention. This is a
    modelling convention, not an interpretation of an equipment safety rule.
    """
    _validate_rule(duration, start_limit, continuation_limit)
    g = np.asarray(values, dtype=float)
    if g.ndim != 1:
        raise ValueError('values must be one-dimensional')
    n = max(0, len(g) - duration + 1)
    if n == 0:
        return np.empty(0, dtype=np.int8)
    finite = np.isfinite(g)
    fail_cont = finite & (g > continuation_limit)
    missing = ~finite
    pf = np.r_[0, np.cumsum(fail_cont, dtype=int)]
    pm = np.r_[0, np.cumsum(missing, dtype=int)]
    t = np.arange(n)
    # Continuation includes slots t+1 ... t+d-1; start has its own threshold.
    fail = (finite[:n] & (g[:n] > start_limit)) | ((pf[t + duration] - pf[t + 1]) > 0)
    unknown = (pm[t + duration] - pm[t]) > 0
    out = np.full(n, ADMISSIBLE, dtype=np.int8)
    out[unknown] = UNKNOWN
    out[fail] = INADMISSIBLE  # A known contradiction dominates unknown entries.
    return out


def reference_window_status(values: Sequence[float], duration: int,
                            start_limit: float, continuation_limit: float) -> np.ndarray:
    """Independent, intentionally slow reference evaluator for verification."""
    _validate_rule(duration, start_limit, continuation_limit)
    labels = []
    for t in range(max(0, len(values) - duration + 1)):
        unknown, failed = False, False
        for h in range(duration):
            v = float(values[t + h])
            if not math.isfinite(v):
                unknown = True
            elif v > (start_limit if h == 0 else continuation_limit):
                failed = True
        labels.append(0 if failed else (-1 if unknown else 1))
    return np.asarray(labels, dtype=np.int8)


def scenario_window_probability(scenarios: Sequence[Sequence[float]], duration: int,
                                start_limit: float, continuation_limit: float) -> np.ndarray:
    s = np.asarray(scenarios, dtype=float)
    if s.ndim != 2 or s.shape[0] == 0:
        raise ValueError('scenarios must be nonempty [scenario, time]')
    if not np.isfinite(s).all():
        raise ValueError('missing scenario members must not be silently discarded')
    return np.mean([window_status(x, duration, start_limit, continuation_limit) for x in s], axis=0)


def parse_utc(value: str) -> datetime:
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('timezone-aware timestamp required')
    return d.astimezone(timezone.utc)


def select_available_run(records: list[dict], decision_time: str) -> dict:
    """Select by availability, never by initialisation time alone.

    Caller MUST establish available_at from archival evidence or explicitly
    labelled conservative latency assumptions before invoking this function.
    """
    decision = parse_utc(decision_time)
    candidates = []
    for r in records:
        issue = parse_utc(r['issue_time'])
        available = parse_utc(r['available_at'])
        if available < issue:
            raise ValueError('available_at predates issue_time')
        if r.get('record_type') != 'operational_archive':
            continue
        if available <= decision:
            candidates.append(r)
    if not candidates:
        raise ValueError('no operational forecast available at decision time')
    return max(candidates, key=lambda x: parse_utc(x['issue_time']))


def assert_feature_availability(available_times: Sequence[str], decision_time: str) -> None:
    decision = parse_utc(decision_time)
    if any(parse_utc(x) > decision for x in available_times):
        raise ValueError('future information detected')


@dataclass(frozen=True)
class Task:
    name: str
    duration: int
    predecessors: tuple[str, ...]
    demand: tuple[int, ...]
    legal_starts: tuple[int, ...]


def validate_problem(tasks: Sequence[Task], capacity: Sequence[int], horizon: int) -> None:
    if horizon < 1 or not tasks or not capacity or min(capacity) < 1:
        raise ValueError('invalid problem size/capacity/horizon')
    names = {t.name for t in tasks}
    if len(names) != len(tasks):
        raise ValueError('duplicate task names')
    remaining, done = list(tasks), set()
    while remaining:
        ready = [t for t in remaining if set(t.predecessors) <= done]
        if not ready:
            raise ValueError('cyclic graph or unknown predecessor')
        done.update(t.name for t in ready)
        remaining = [t for t in remaining if t not in ready]
    for t in tasks:
        if t.duration < 1 or len(t.demand) != len(capacity):
            raise ValueError('invalid duration/resource vector')
        if any(d < 0 or d > c for d, c in zip(t.demand, capacity)):
            raise ValueError('task demand exceeds capacity or is negative')
        if len(set(t.legal_starts)) != len(t.legal_starts):
            raise ValueError('duplicate candidate starts')
        if any(s < 0 or s + t.duration > horizon for s in t.legal_starts):
            raise ValueError('candidate outside horizon')


def solve_deterministic(tasks: Sequence[Task], capacity: Sequence[int], horizon: int,
                        time_limit: float = 30.0) -> dict:
    """Time-indexed MILP with HiGHS through SciPy; no commercial solver.

    Each task chooses one candidate start. This is a deterministic planning
    kernel, not evidence of operational forecast performance or a full
    stochastic optimal policy. 'Optimal' is returned only for solver status 0.
    """
    from scipy.optimize import milp, Bounds, LinearConstraint
    from scipy.sparse import coo_array
    validate_problem(tasks, capacity, horizon)
    if any(not t.legal_starts for t in tasks):
        return {'status': 'infeasible', 'reason': 'at least one task has no accepted candidate window'}
    keys = [(t.name, s) for t in tasks for s in t.legal_starts]
    index = {k: j for j, k in enumerate(keys)}
    by_name = {t.name: t for t in tasks}
    C = len(keys)
    rr, cc, vv, lower, upper = [], [], [], [], []
    def row(terms: dict[int, float], lb: float, ub: float) -> None:
        r = len(lower)
        for col, val in terms.items():
            if val:
                rr.append(r); cc.append(col); vv.append(float(val))
        lower.append(lb); upper.append(ub)
    for t in tasks:
        row({index[(t.name, s)]: 1 for s in t.legal_starts}, 1, 1)
        terms = {index[(t.name, s)]: s+t.duration for s in t.legal_starts}
        terms[C] = -1
        row(terms, -np.inf, 0)
        for pred in t.predecessors:
            p = by_name[pred]
            terms = {index[(pred, s)]: s+p.duration for s in p.legal_starts}
            terms.update({index[(t.name, s)]: -s for s in t.legal_starts})
            row(terms, -np.inf, 0)
    for tau in range(horizon):
        for k, cap in enumerate(capacity):
            terms = {index[(t.name, s)]: t.demand[k]
                     for t in tasks for s in t.legal_starts
                     if s <= tau < s+t.duration and t.demand[k]}
            if terms:
                row(terms, -np.inf, cap)
    mat = coo_array((vv, (rr, cc)), shape=(len(lower), C+1)).tocsc()
    objective = np.zeros(C+1); objective[C] = 1
    res = milp(objective, integrality=np.r_[np.ones(C), 0],
               bounds=Bounds(np.zeros(C+1), np.r_[np.ones(C), horizon]),
               constraints=LinearConstraint(mat, lower, upper),
               options={'time_limit': time_limit, 'mip_rel_gap': 0.0})
    status = {0:'optimal', 1:'limit', 2:'infeasible', 3:'unbounded', 4:'error'}.get(res.status,'error')
    out = {'status': status, 'message': res.message, 'solver': 'SciPy-HiGHS'}
    if res.x is not None:
        starts = {name:s for (name,s), j in index.items() if res.x[j] > .5}
        verify_schedule(tasks, capacity, horizon, starts)
        out.update(starts=starts, makespan=max(starts[t.name]+t.duration for t in tasks),
                   mip_gap=float(getattr(res, 'mip_gap', float('nan'))))
    return out


def verify_schedule(tasks: Sequence[Task], capacity: Sequence[int], horizon: int,
                    starts: dict[str, int]) -> None:
    """Independent verifier: no reuse of solver constraint matrix."""
    if set(starts) != {t.name for t in tasks}:
        raise ValueError('missing/extra scheduled tasks')
    by_name = {t.name:t for t in tasks}
    for t in tasks:
        s = starts[t.name]
        if not isinstance(s, (int, np.integer)) or s not in t.legal_starts:
            raise ValueError('illegal start')
        if any(starts[p] + by_name[p].duration > s for p in t.predecessors):
            raise ValueError('precedence violation')
    for tau in range(horizon):
        for k, cap in enumerate(capacity):
            used = sum(t.demand[k] for t in tasks if starts[t.name] <= tau < starts[t.name]+t.duration)
            if used > cap:
                raise ValueError('resource violation')
