"""Bootstrap intervals for the work-package table.

The review's complaint about Table 6 was that it reported seven controllers x four
scenarios of mean cost with no sample size, no units and no uncertainty, while the text
quoted intervals for two comparisons that did not appear in the table.

This computes, for every scenario and controller, the mean cost per package with a
paired bootstrap interval. Packages are the resampling unit and all controllers are
resampled together, so the intervals reflect between-package variation under a paired
design rather than pretending the 765 packages are independent draws of the weather.

Costs are in units of the exceedance loss L, which the scenarios normalise to 1
(`mismatch_cost` is set to 1.0 in the base scenario).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

SCENARIO_ORDER = ["base", "slack_resources", "high_adjustment_cost", "weak_weather_impact"]
SCENARIO_LABEL = {
    "base": "Base",
    "slack_resources": "Loose resources",
    "high_adjustment_cost": "High adjustment cost",
    "weak_weather_impact": "Weak weather impact",
}
CONTROLLER_ORDER = [
    "operating_limit", "tuned_threshold", "calibrated", "calibrated_by_lead",
    "no_weather", "calibrated_static", "calibrated_rolling_free",
]
CONTROLLER_LABEL = {
    "operating_limit": "Operating limit, unchanged",
    "tuned_threshold": "Raw threshold, tuned",
    "calibrated": "Calibrated probability",
    "calibrated_by_lead": "Calibrated, lead-stratified",
    "no_weather": "No weather service",
    "calibrated_static": "Calibrated, never revise",
    "calibrated_rolling_free": "Calibrated, revise freely",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260916)
    args = parser.parse_args()
    root: Path = args.root
    rng = np.random.default_rng(args.seed)

    runs = pd.read_csv(root / "outputs" / "g5_work_package_runs.csv")
    keys = ["station", "block"]
    n_packages = runs.groupby(keys).ngroups

    table: dict[str, dict] = {}
    for scen in SCENARIO_ORDER:
        block = runs[runs["scenario"] == scen]
        piv = block.pivot_table(index=keys, columns="controller", values="cost")
        # a single set of package indices per draw, reused for every controller
        idx = np.arange(len(piv))
        draws = np.array([piv.to_numpy()[rng.integers(0, len(idx), len(idx))].mean(axis=0)
                          for _ in range(args.draws)])
        entry = {}
        for j, ctrl in enumerate(piv.columns):
            col = piv.to_numpy()[:, j]
            entry[ctrl] = {
                "mean": float(col.mean()),
                "ci_low": float(np.percentile(draws[:, j], 2.5)),
                "ci_high": float(np.percentile(draws[:, j], 97.5)),
            }
        table[scen] = entry

    out = {
        "packages_per_scenario": int(n_packages),
        "stations": int(runs["station"].nunique()),
        "units": "cost in units of the exceedance loss L (mismatch_cost = 1.0 in the base scenario)",
        "bootstrap": {"unit": "package (station x 30-day window)",
                      "paired_across_controllers": True, "draws": args.draws},
        "table": table,
        "package_definition": {
            "tasks": 10, "block_hours": 12, "blocks_per_package": 60,
            "horizon_days": 30, "deadlines": "no-weather baseline schedule x 1.5",
        },
    }
    (root / "outputs" / "g5_work_package_table.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"packages per scenario: {n_packages} | stations: {out['stations']} | "
          f"units: {out['units']}")
    print()
    header = "| Controller | " + " | ".join(SCENARIO_LABEL[s] for s in SCENARIO_ORDER) + " |"
    print(header)
    print("|---|" + "---:|" * len(SCENARIO_ORDER))
    for ctrl in CONTROLLER_ORDER:
        cells = []
        for scen in SCENARIO_ORDER:
            v = table[scen].get(ctrl)
            cells.append(f"{v['mean']:.3f}" if v else "-")
        print(f"| {CONTROLLER_LABEL[ctrl]} | " + " | ".join(cells) + " |")
    print()
    print("with intervals:")
    for ctrl in CONTROLLER_ORDER:
        for scen in SCENARIO_ORDER:
            v = table[scen].get(ctrl)
            if v:
                print(f"  {scen:22s} {ctrl:26s} {v['mean']:.3f} "
                      f"[{v['ci_low']:.3f}, {v['ci_high']:.3f}]")


if __name__ == "__main__":
    main()
