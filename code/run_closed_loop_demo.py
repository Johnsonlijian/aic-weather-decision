"""Run the minimal controller on constructed paths only.

Outputs are a software smoke test and must not be reported as field or
empirical construction results.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from core import Task
from rolling_controller import (ControllerContext, OperationContract,
                                assert_same_action_for_hidden_futures,
                                choose_action, evaluate_action)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


def main() -> None:
    tasks = [
        Task("lift", 3, (), (1,), (0, 1, 2, 3, 4, 5)),
        Task("finish", 1, ("lift",), (1,), (0, 1, 2, 3, 4, 5, 6)),
    ]
    contracts = {
        "lift": OperationContract(11.1, 20.0),
        "finish": OperationContract(30.0, 30.0),
    }
    forecast = np.array([
        [8, 8, 25, 8, 8, 8, 8],
        [8, 8, 8, 8, 8, 8, 8],
    ], dtype=float)
    ctx = ControllerContext(0, forecast)
    ctx_copy = ControllerContext(0, forecast.copy())
    assert_same_action_for_hidden_futures(tasks, contracts, ctx, ctx_copy)

    truth_paths = {
        "hidden_future_good": [8, 8, 8, 8, 8, 8, 8],
        "hidden_future_bad": [8, 25, 8, 25, 25, 25, 8],
    }
    rows = []
    for policy in ("earliest", "risk_aware"):
        action = choose_action(tasks, contracts, ctx, policy)
        if action is None:
            raise RuntimeError(f"no action for {policy}")
        for truth_id, truth in truth_paths.items():
            outcome = evaluate_action(truth, action, tasks[0], contracts["lift"])
            rows.append({
                "source_type": "constructed_not_observed",
                "policy_id": policy,
                "truth_case": truth_id,
                "task_name": action.task_name,
                "action_start": action.start,
                "forecast_window_probability": action.window_probability,
                "observed_window_status": outcome,
            })
    out = OUT / "constructed_controller_demo.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "source_type": "constructed_controller_smoke_only",
        "nonanticipative_visible_snapshot_check": "PASS",
        "rows": len(rows),
        "policies": ["earliest", "risk_aware"],
        "hidden_truth_is_evaluator_only": True,
        "empirical_weather_rows": 0,
        "empirical_project_files": 0,
    }
    (OUT / "constructed_controller_demo.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
