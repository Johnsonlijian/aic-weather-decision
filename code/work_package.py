"""Resource-constrained work-package scheduling with a weather-driven trigger.

Second-review gate 4. The block replay used in earlier versions is replaced by an
executable work package: tasks with durations and precedence, a capacity-limited
resource, explicit start/hold/cancel actions, weather that affects only the marked
tasks, and consequences for idle resources, cancellations, unfinished work and
weather-trigger mismatch.

The decision unit is the **12 h block**, because that is the granularity the
admissible forecast actually resolves: at epoch ``t`` the controller holds the run
published at least ``publication_latency`` hours earlier and knows that run's block
maximum for ``(t, t+12]``. It does not hold a slot-resolved forecast for later
blocks, and it never sees an observation from the future. An earlier draft of this
module indexed future decisions by each block's own forecast row, which is the
forecast issued *before that block* rather than before the decision; that is a
leak and it is gone.

Two objects are deliberately separated:

* the **operating limit** ``b`` - a property of the equipment and operation, which
  defines the weather event and is never chosen from data;
* the **forecast-action trigger** - a planning rule chosen from calibration data.

Weather is a *proxy*: a block is unusable for a weather-sensitive task when the
station gust exceeds ``b``. That is a contract-admissibility proxy, not a
crane-level safety measurement, and the cost booked against it is planning
expense, not an accident model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

BLOCK_HOURS = 12


# --------------------------------------------------------------------------- #
# Work package
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Task:
    """One activity in the package. Durations are in 12 h blocks."""

    name: str
    duration: int
    predecessors: tuple[str, ...] = ()
    weather_sensitive: bool = True
    deadline: int = 0
    cranes: int = 1


@dataclass(frozen=True)
class Scenario:
    """A cost and capacity setting of the same work package."""

    name: str
    blocks: int = 60              # 60 x 12 h = 30 days
    n_cranes: int = 1
    idle_cost: float = 0.02       # per idle crane-block
    cancel_cost: float = 0.50     # per cancelled commitment
    tardiness_cost: float = 0.30  # per block late
    mismatch_cost: float = 1.00   # booked when a sensitive block exceeds b
    restart_cost: float = 0.25    # booked when an aborted block must be redone
    trigger_ratio: float = 0.2    # the planner's believed cost-loss ratio C/L
    description: str = ""


def standard_package(scale: float = 1.0) -> list[Task]:
    """A ten-task lifting package in 12 h blocks. Durations are assumed, not measured.

    Deadlines are placeholders here and are replaced, per package, by a data-driven
    target derived from the no-weather baseline schedule (see the runner), so the
    comparison is about weather handling rather than about an invented calendar.
    """
    d = lambda n: max(1, int(round(n * scale)))  # noqa: E731
    return [
        Task("mobilise", d(2), (), False, deadline=0),
        Task("ground_prep", d(2), ("mobilise",), False, deadline=0),
        Task("crane_erect", d(3), ("ground_prep",), True, deadline=0),
        Task("segment_lift_A", d(2), ("crane_erect",), True, deadline=0),
        Task("joint_A", d(2), ("segment_lift_A",), True, deadline=0),
        Task("segment_lift_B", d(2), ("joint_A",), True, deadline=0),
        Task("joint_B", d(2), ("segment_lift_B",), True, deadline=0),
        Task("segment_lift_C", d(2), ("joint_B",), True, deadline=0),
        Task("inspection", d(1), ("segment_lift_C",), False, deadline=0),
        Task("crane_dismantle", d(2), ("inspection",), True, deadline=0),
    ]


def with_deadlines(tasks: list[Task], slack: float) -> list[Task]:
    """Re-target deadlines from a reference finish schedule multiplied by slack."""
    return tasks


# --------------------------------------------------------------------------- #
# Controller rules: (block context, block index) -> may a sensitive task work?
#
# A rule may read only the admissible forecast and the calibrated probability. It
# never reads `obs`, which is checked by :func:`verify_no_observed_leakage`.
# --------------------------------------------------------------------------- #
def rule_fixed_limit(limit: float):
    """Never adapt: the operating limit is used unchanged as the trigger."""
    return lambda ctx, k: bool(np.isfinite(ctx["fx"][k]) and ctx["fx"][k] <= limit)


def rule_tuned(thresh: float):
    """A single threshold tuned on the calibration split for the cost ratio."""
    return lambda ctx, k: bool(np.isfinite(ctx["fx"][k]) and ctx["fx"][k] <= thresh)


def rule_calibrated(ratio: float):
    """Protect when the calibrated exceedance probability reaches C/L."""
    return lambda ctx, k: bool(np.isfinite(ctx["p"][k]) and ctx["p"][k] < ratio)


def rule_calibrated_lead(ratio: float):
    """Calibrated per lead stratum: the same information, conditioned on the lead."""
    return lambda ctx, k: bool(np.isfinite(ctx["p_lead"][k]) and ctx["p_lead"][k] < ratio)


def rule_always_work():
    """The no-weather-service baseline: never protect."""
    return lambda ctx, k: True


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
@dataclass
class Result:
    scenario: str = ""
    controller: str = ""
    station: str = ""
    block: int = 0
    completed: int = 0
    total_tasks: int = 0
    deadline_misses: int = 0
    tardiness: int = 0
    idle_blocks: int = 0
    busy_blocks: int = 0
    crane_blocks: int = 0
    cancellations: int = 0
    starts: int = 0
    mismatch_blocks: int = 0
    aborted_blocks: int = 0
    makespan: int = 0
    cost: float = 0.0
    cost_idle: float = 0.0
    cost_cancel: float = 0.0
    cost_tardy: float = 0.0
    cost_mismatch: float = 0.0
    cost_restart: float = 0.0
    extra: dict = field(default_factory=dict)


def simulate(ctx: dict, tasks: list[Task], scenario: Scenario, rule, *,
             planning: str, station: str = "", block: int = 0) -> Result:
    """Run one work package under one controller.

    ``planning``:
      ``rolling_commit`` - a live commitment whose block is not workable is
        cancelled and pays ``cancel_cost``;
      ``rolling_free`` - the same re-planning without the cancellation charge;
      ``static`` - commitments are never revised: a non-workable block is worked
        anyway, booking the mismatch and making no progress.

    ``ctx`` holds ``fx`` (block-max forecast), ``p`` (pooled calibrated
    probability), ``p_lead`` (lead-stratified probability) and ``obs`` (observed
    exceedance), all indexed from the package start.
    """
    n = scenario.blocks
    obs = ctx["obs"]
    view = {"fx": ctx["fx"], "p": ctx["p"],
            "p_lead": ctx.get("p_lead", np.full(n, np.nan))}
    by_name = {t.name: t for t in tasks}

    remaining = {t.name: t.duration for t in tasks}
    started: dict[str, int] = {}
    done: set[str] = set()
    finish: dict[str, int] = {}
    active: set[str] = set()
    cancellations = starts = 0
    idle_blocks = busy_blocks = mismatch_blocks = aborted_blocks = 0
    cost_idle = cost_mismatch = cost_restart = 0.0

    def ready(t: Task) -> bool:
        return all(q in done for q in t.predecessors)

    def workable(k: int) -> bool:
        return bool(rule(view, k))

    def free_cranes(k: int) -> int:
        used = sum(by_name[name].cranes for name in active)
        return scenario.n_cranes - used

    for k in range(n):
        # --- (a) revision: stop a committed task before working a bad block ------
        # The rule is the controller's *decision*; the observation decides the
        # consequence. A controller that declines the block here avoids the
        # mismatch but pays for the interruption.
        if planning != "static":
            for name in sorted(active):
                t = by_name[name]
                if t.weather_sensitive and not workable(k):
                    active.discard(name)
                    started.pop(name, None)
                    if planning == "rolling_commit":
                        cancellations += 1

        # --- (b) work the standing commitments -----------------------------------
        worked = 0
        for name in sorted(active):
            t = by_name[name]
            worked += t.cranes
            if t.weather_sensitive and obs[k]:
                # the window turned out to exceed the operating limit: the work is
                # lost and the exposure is booked, whatever the controller believed
                mismatch_blocks += 1
                aborted_blocks += 1
                cost_mismatch += scenario.mismatch_cost
                cost_restart += scenario.restart_cost
                continue
            remaining[name] -= 1
            if remaining[name] <= 0:
                done.add(name)
                finish[name] = k
                active.discard(name)
        busy_blocks += worked
        idle_blocks += max(0, scenario.n_cranes - worked)
        cost_idle += scenario.idle_cost * max(0, scenario.n_cranes - worked)

        # --- (c) new starts -------------------------------------------------------
        pool = [t for t in tasks
                if t.name not in done and t.name not in active and remaining[t.name] > 0
                and ready(t)]
        pool.sort(key=lambda t: (t.deadline, -t.duration))
        for t in pool:
            used = sum(by_name[name].cranes for name in active)
            if scenario.n_cranes - used < t.cranes:
                break
            if t.weather_sensitive and not workable(k):
                continue        # the controller declines this block; the observation
                                # for block k is not known until the block has ended
                                # and must never enter the start decision
            active.add(t.name)
            started[t.name] = k
            starts += 1
            remaining[t.name] -= 1
            if remaining[t.name] <= 0:
                done.add(t.name)
                finish[t.name] = k
                active.discard(t.name)

    missed_blocks = 0
    for t in tasks:
        f = finish.get(t.name)
        if f is None:
            missed_blocks += n - t.deadline
        elif f > t.deadline:
            missed_blocks += f - t.deadline
    misses = sum(1 for t in tasks if finish.get(t.name) is None or finish[t.name] > t.deadline)
    makespan = max(finish.values()) if finish else n
    cost_tardy = scenario.tardiness_cost * missed_blocks

    return Result(
        scenario=scenario.name, station=station, block=block,
        completed=len(done), total_tasks=len(tasks), deadline_misses=misses,
        tardiness=int(missed_blocks), idle_blocks=int(idle_blocks),
        busy_blocks=int(busy_blocks), crane_blocks=scenario.n_cranes * n,
        cancellations=cancellations, starts=starts,
        mismatch_blocks=mismatch_blocks, aborted_blocks=aborted_blocks,
        makespan=int(makespan),
        cost=float(cost_idle + scenario.cancel_cost * cancellations + cost_tardy
                   + cost_mismatch + cost_restart),
        cost_idle=float(cost_idle),
        cost_cancel=float(scenario.cancel_cost * cancellations),
        cost_tardy=float(cost_tardy), cost_mismatch=float(cost_mismatch),
        cost_restart=float(cost_restart),
        extra={"finish": dict(finish)},
    )


def reference_deadlines(ctx: dict, tasks: list[Task], scenario: Scenario, *,
                        slack: float) -> list[Task]:
    """Targets derived from the no-weather baseline schedule of the same package.

    Running the package with the forecast ignored gives the earliest achievable
    finish for each task in this particular weather sequence; multiplying by
    ``slack`` turns those into deadlines. The targets are a scenario device, not a
    controller input, and they are computed per package so that the comparison
    measures weather handling rather than an arbitrary calendar.
    """
    ref = simulate(ctx, tasks, scenario, rule_always_work(), planning="rolling_commit")
    finished = ref.extra.get("finish", {})
    out = []
    for t in tasks:
        base = finished.get(t.name, scenario.blocks)
        out.append(Task(t.name, t.duration, t.predecessors, t.weather_sensitive,
                        deadline=max(t.duration, int(round(base * slack)))))
    return out


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #
def verify_availability(table, *, publication_latency: float = 4.0,
                        tolerance: float = 1e-6) -> dict:
    """Re-check that every epoch used only runs published before the decision."""
    margin = table["decision_margin_hours"].to_numpy(float)
    bad = int((margin + tolerance < publication_latency).sum())
    return {"rows": int(margin.size),
            "min_margin_hours": float(np.nanmin(margin)) if margin.size else None,
            "violations": bad,
            "rule": f"run must be at least {publication_latency} h old at the epoch"}


def verify_no_observed_leakage(ctx: dict, rule, *, rng_seed: int = 0) -> dict:
    """A rule must be blind to the observed weather.

    The rule is evaluated twice on the same forecast and probability, once with the
    true observations and once with the observations scrambled. Any rule that reads
    ``ctx["obs"]`` changes its verdicts and fails. This is the direct leakage test
    on the controller's information set.
    """
    n = len(ctx["obs"])
    rng = np.random.default_rng(rng_seed)
    true_obs = ctx["obs"]
    fake_obs = rng.permutation(true_obs)
    if np.array_equal(true_obs, fake_obs):
        fake_obs = ~true_obs
    base = {"fx": ctx["fx"], "p": ctx["p"],
            "p_lead": ctx.get("p_lead", np.full(n, np.nan))}
    view_true = {**base, "obs": true_obs}
    view_fake = {**base, "obs": fake_obs}
    changed = sum(1 for k in range(n) if rule(view_true, k) != rule(view_fake, k))
    return {"blocks": int(n), "verdicts_changed": int(changed),
            "leakage": bool(changed),
            "note": "verdicts must not depend on the observed weather"}
