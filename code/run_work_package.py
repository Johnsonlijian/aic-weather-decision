"""Gate 4 experiment: tuned-on-calibration comparison of triggers inside a scheduler.

Every controller that has a parameter is tuned on the calibration split for the
**scheduling objective** and then evaluated once on the held-out split. This is the
fair version of the comparison: the earlier draft fixed the calibrated rule's ratio
at a planner belief while leaving other rules free, which flatters whatever happens
to suit that belief.

Two comparison lines, so the source of any benefit can be attributed:

* **Line 1 - same scheduler, different weather input.** Planning fixed at
  ``rolling_commit``; the trigger varies across the operating limit used unchanged,
  a raw threshold tuned on calibration, the calibrated probability with its ratio
  tuned on calibration, the same with lead-stratified calibration, and a
  no-weather baseline.
* **Line 2 - same weather input, different planning method.** Weather input fixed at
  the calibrated rule; planning varies across never revising, revising freely, and
  revising while paying to cancel.

The decision unit is the 12 h block, the granularity the admissible forecast
resolves, and the controller sees only the run published before that block begins.
Deadlines come from the no-weather baseline schedule of the same package times a
slack factor, so the comparison measures weather handling rather than a calendar.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from calibration import BinnedCalibrator
from work_package import (BLOCK_HOURS, Scenario, reference_deadlines,
                          rule_always_work, rule_calibrated, rule_calibrated_lead,
                          rule_fixed_limit, rule_tuned, simulate, standard_package,
                          verify_availability, verify_no_observed_leakage)

PACKAGE_BLOCKS = 60          # 60 x 12 h = 30 days
PROB_GRID = (0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70)      # for probability rules
GUST_GRID = (7.0, 9.0, 11.0, 12.0, 13.0, 15.0, 18.0, 21.0)  # for raw-threshold rules
PARAM_GRID = PROB_GRID


def scenarios(trigger_ratio: float = 0.2) -> list[Scenario]:
    """The four settings. ``trigger_ratio`` is only a placeholder for the tuned rules."""
    common = dict(blocks=PACKAGE_BLOCKS, trigger_ratio=trigger_ratio)
    return [
        Scenario(name="base", n_cranes=1, idle_cost=0.02, cancel_cost=0.5,
                 tardiness_cost=0.3, mismatch_cost=1.0, restart_cost=0.25,
                 description="one crane, balanced costs", **common),
        Scenario(name="slack_resources", n_cranes=2, idle_cost=0.01, cancel_cost=0.5,
                 tardiness_cost=0.1, mismatch_cost=1.0, restart_cost=0.25,
                 description="two cranes, cheap delay: resources loose", **common),
        Scenario(name="high_adjustment_cost", n_cranes=1, idle_cost=0.02, cancel_cost=8.0,
                 tardiness_cost=0.3, mismatch_cost=1.0, restart_cost=0.75,
                 description="changing a commitment is expensive", **common),
        Scenario(name="weak_weather_impact", n_cranes=1, idle_cost=0.02, cancel_cost=0.5,
                 tardiness_cost=0.3, mismatch_cost=0.05, restart_cost=0.01,
                 description="weather barely matters", **common),
    ]


def build_blocks(root: Path, table: str, limit: float) -> tuple[dict, dict]:
    cols = ["station_id", "epoch", "split", "decision_margin_hours",
            f"block_max_L{BLOCK_HOURS}", f"lead_L{BLOCK_HOURS}",
            f"L{BLOCK_HOURS}_thr{limit}"]
    frame = pd.read_csv(root / table, usecols=cols)
    frame["epoch"] = pd.to_datetime(frame["epoch"], utc=True)
    frame = frame.sort_values(["station_id", "epoch"])
    pred, lab = f"block_max_L{BLOCK_HOURS}", f"L{BLOCK_HOURS}_thr{limit}"
    fit = frame[frame["split"] == "FIT"]
    pooled = BinnedCalibrator().fit(fit[pred].to_numpy(float), fit[lab].to_numpy(float))
    by_lead = {}
    for lead, block in fit.groupby(f"lead_L{BLOCK_HOURS}"):
        if block[lab].sum() >= 50:
            by_lead[int(lead)] = BinnedCalibrator().fit(block[pred].to_numpy(float),
                                                        block[lab].to_numpy(float))
    stations: dict[str, dict] = {}
    for station, block in frame.groupby("station_id"):
        x = block[pred].to_numpy(float)
        leads = block[f"lead_L{BLOCK_HOURS}"].to_numpy()
        p_lead = np.full_like(x, np.nan)
        for lead, model in by_lead.items():
            sel = leads == lead
            if sel.any():
                p_lead[sel] = model.predict(x[sel])
        stations[str(station)] = {
            "fx": x, "p": pooled.predict(x), "p_lead": p_lead,
            "obs": block[lab].to_numpy() == 1, "split": block["split"].to_numpy(),
            "margin": block["decision_margin_hours"].to_numpy(float)}
    return stations, {"base_rate_block": float(fit[lab].mean()),
                      "lead_strata": sorted(by_lead)}


def package_windows(data: dict, split: str) -> list[np.ndarray]:
    idx = np.nonzero(data["split"] == split)[0]
    if idx.size < PACKAGE_BLOCKS + 2:
        return []
    return [np.arange(b, b + PACKAGE_BLOCKS)
            for b in range(idx[0], idx[-1] - PACKAGE_BLOCKS, PACKAGE_BLOCKS)]


def ctx_of(data: dict, idx: np.ndarray) -> dict:
    return {"fx": data["fx"][idx], "p": data["p"][idx],
            "p_lead": data["p_lead"][idx], "obs": data["obs"][idx]}


def evaluate(stations: dict, split: str, scen: Scenario, slack: float,
             rule_factory, planning: str, param: float | None) -> pd.DataFrame:
    rows = []
    for station, data in stations.items():
        for b, idx in enumerate(package_windows(data, split)):
            ctx = ctx_of(data, idx)
            tasks = reference_deadlines(ctx, standard_package(), scen, slack=slack)
            rule = rule_factory(param) if param is not None else rule_factory()
            res = simulate(ctx, tasks, scen, rule, planning=planning,
                           station=station, block=b)
            row = asdict(res)
            row.pop("extra", None)
            rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_paired(diff: np.ndarray, draws: int, rng: np.random.Generator) -> dict:
    stats = np.array([diff[rng.integers(0, diff.size, diff.size)].mean()
                      for _ in range(draws)])
    return {"mean": float(diff.mean()), "ci_low": float(np.percentile(stats, 2.5)),
            "ci_high": float(np.percentile(stats, 97.5)), "units": int(diff.size),
            "draws": draws, "share_draws_positive": float((stats > 0).mean())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--table", default="outputs/epochs_multi3.csv")
    parser.add_argument("--limit", type=float, default=12.0)
    parser.add_argument("--deadline-slack", type=float, default=1.5)
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260916)
    args = parser.parse_args()
    root: Path = args.root

    stations, info = build_blocks(root, args.table, args.limit)
    boundary = verify_availability(pd.DataFrame(
        {"decision_margin_hours": np.concatenate([v["margin"] for v in stations.values()])}))
    leakage = verify_no_observed_leakage(stations[sorted(stations)[0]], rule_calibrated(0.2))

    families = {
        "operating_limit": (lambda p=None: rule_fixed_limit(args.limit), "rolling_commit", None),
        "tuned_threshold": (rule_tuned, "rolling_commit", GUST_GRID),
        "calibrated": (rule_calibrated, "rolling_commit", PROB_GRID),
        "calibrated_by_lead": (rule_calibrated_lead, "rolling_commit", PROB_GRID),
        "no_weather": (lambda p=None: rule_always_work(), "rolling_commit", None),
        "calibrated_static": (rule_calibrated, "static", PROB_GRID),
        "calibrated_rolling_free": (rule_calibrated, "rolling_free", PROB_GRID),
    }

    rng = np.random.default_rng(args.seed)
    report: dict = {"limit": args.limit, "package_blocks": PACKAGE_BLOCKS,
                    "block_hours": BLOCK_HOURS, "deadline_slack": args.deadline_slack,
                    "param_grid": list(PARAM_GRID), "block_base_rate": info["base_rate_block"],
                    "lead_strata": info["lead_strata"], "availability": boundary,
                    "leakage_check": leakage, "tuned_parameters": {}, "test": {},
                    "line1_weather_input": {}, "line2_planning_method": {}}
    frames = []
    for scen in scenarios():
        chosen: dict[str, float | None] = {}
        for name, (factory, planning, grid) in families.items():
            if grid is None:
                chosen[name] = None
                continue
            best, best_cost = None, np.inf
            for param in grid:
                cal_cost = evaluate(stations, "CAL", scen, args.deadline_slack,
                                    factory, planning, param)["cost"].mean()
                if cal_cost < best_cost:
                    best, best_cost = float(param), float(cal_cost)
            chosen[name] = best
        report["tuned_parameters"][scen.name] = chosen
        for name, (factory, planning, _grid) in families.items():
            frame = evaluate(stations, "TEST", scen, args.deadline_slack,
                             factory, planning, chosen[name])
            frame["controller"] = name
            frame["scenario"] = scen.name
            frame["tuned_param"] = chosen[name] if chosen[name] is not None else np.nan
            frames.append(frame)

    results = pd.concat(frames, ignore_index=True)
    results.to_csv(root / "outputs" / "g5_work_package_runs.csv", index=False)
    keys = ["station", "block"]
    for scen_name in sorted(results["scenario"].unique()):
        block = results[results["scenario"] == scen_name]
        piv = block.pivot_table(index=keys, columns="controller", values="cost")
        report["test"][scen_name] = {
            "cost": block.groupby("controller")["cost"].mean().round(4).to_dict(),
            "completed": block.groupby("controller")["completed"].mean().round(2).to_dict(),
            "deadline_misses": block.groupby("controller")["deadline_misses"].mean().round(2).to_dict(),
            "idle_blocks": block.groupby("controller")["idle_blocks"].mean().round(1).to_dict(),
            "mismatch_blocks": block.groupby("controller")["mismatch_blocks"].mean().round(2).to_dict(),
            "cancellations": block.groupby("controller")["cancellations"].mean().round(2).to_dict(),
            "makespan": block.groupby("controller")["makespan"].mean().round(1).to_dict(),
            "packages": int(len(piv))}
        for other in ("operating_limit", "tuned_threshold", "no_weather",
                      "calibrated_by_lead"):
            if other in piv.columns and "calibrated" in piv.columns:
                d = (piv[other] - piv["calibrated"]).to_numpy(float)
                d = d[np.isfinite(d)]
                if d.size:
                    report["line1_weather_input"][f"{scen_name}|{other}_minus_calibrated"] = \
                        bootstrap_paired(d, args.draws, rng)
        for other in ("calibrated_static", "calibrated_rolling_free"):
            if other in piv.columns and "calibrated" in piv.columns:
                d = (piv[other] - piv["calibrated"]).to_numpy(float)
                d = d[np.isfinite(d)]
                if d.size:
                    report["line2_planning_method"][
                        f"{scen_name}|{other}_minus_rolling_commit"] = \
                        bootstrap_paired(d, args.draws, rng)

    (root / "outputs" / "g5_work_package.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    print(f"stations {len(stations)} | block base rate {info['base_rate_block']:.4f} | "
          f"lead strata {info['lead_strata']}")
    print(f"availability violations {boundary['violations']} | leakage verdicts changed "
          f"{leakage['verdicts_changed']}")
    for scen_name, s in report["test"].items():
        print(f"\n{scen_name} (TEST, {s['packages']} packages; tuned on CAL: "
              f"{ {k: v for k, v in report['tuned_parameters'][scen_name].items() if v is not None} })")
        for ctrl in sorted(s["cost"]):
            print(f"  {ctrl:24s} cost {s['cost'][ctrl]:7.3f} | done {s['completed'][ctrl]:5.2f} "
                  f"| miss {s['deadline_misses'][ctrl]:5.2f} | idle {s['idle_blocks'][ctrl]:6.1f} "
                  f"| mismatch {s['mismatch_blocks'][ctrl]:5.2f} "
                  f"| cancel {s['cancellations'][ctrl]:5.2f} | span {s['makespan'][ctrl]:5.1f}")
    print("\nline 1 - weather input, paired cost difference vs calibrated")
    for k, v in report["line1_weather_input"].items():
        print(f"  {k:66s} {v['mean']:+8.4f} [{v['ci_low']:+.4f}, {v['ci_high']:+.4f}]")
    print("line 2 - planning method, paired cost difference vs rolling+commit")
    for k, v in report["line2_planning_method"].items():
        print(f"  {k:66s} {v['mean']:+8.4f} [{v['ci_low']:+.4f}, {v['ci_high']:+.4f}]")


if __name__ == "__main__":
    main()
