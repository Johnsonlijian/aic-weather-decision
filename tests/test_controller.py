import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from core import Task  # noqa: E402
from rolling_controller import (  # noqa: E402
    ControllerContext,
    OperationContract,
    assert_same_action_for_hidden_futures,
    choose_action,
    evaluate_action,
)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tasks = [
            Task("lift", 3, (), (1,), (0, 1, 2, 3, 4, 5)),
            Task("finish", 1, ("lift",), (1,), (0, 1, 2, 3, 4, 5, 6)),
        ]
        self.contracts = {"lift": OperationContract(11.1, 20.0),
                          "finish": OperationContract(30.0, 30.0)}

    def test_risk_aware_uses_visible_forecast_snapshot(self):
        # Start 0 has a fragmented member; start 3 is admissible for both.
        scenarios = np.array([
            [8, 8, 25, 8, 8, 8, 8],
            [8, 8, 8, 8, 8, 8, 8],
        ], dtype=float)
        ctx = ControllerContext(0, scenarios)
        action = choose_action(self.tasks, self.contracts, ctx, "risk_aware")
        self.assertEqual(action.task_name, "lift")
        self.assertEqual(action.start, 3)
        self.assertEqual(action.window_probability, 1.0)

    def test_earliest_policy_is_transparent_baseline(self):
        scenarios = np.full((2, 4), 8.0)
        ctx = ControllerContext(0, scenarios)
        action = choose_action(self.tasks, self.contracts, ctx, "earliest")
        self.assertEqual((action.task_name, action.start), ("lift", 0))

    def test_precedence_excludes_successor_until_done(self):
        scenarios = np.full((2, 7), 8.0)
        ctx = ControllerContext(0, scenarios, completed=frozenset({"lift"}))
        action = choose_action(self.tasks, self.contracts, ctx, "earliest")
        self.assertEqual((action.task_name, action.start), ("finish", 0))

    def test_outside_visible_forecast_is_not_used(self):
        scenarios = np.full((2, 2), 8.0)
        ctx = ControllerContext(0, scenarios)
        self.assertIsNone(choose_action(self.tasks, self.contracts, ctx, "risk_aware"))

    def test_hidden_truth_does_not_change_current_action(self):
        scenarios = np.full((2, 7), 8.0)
        ctx_a = ControllerContext(0, scenarios)
        ctx_b = ControllerContext(0, scenarios.copy())
        assert_same_action_for_hidden_futures(self.tasks, self.contracts, ctx_a, ctx_b)
        action = choose_action(self.tasks, self.contracts, ctx_a, "risk_aware")
        truth_good = [8, 8, 8, 8, 8, 8, 8]
        truth_bad = [8, 25, 8, 25, 25, 25, 8]
        self.assertEqual(evaluate_action(truth_good, action, self.tasks[0], self.contracts["lift"]), 1)
        self.assertEqual(evaluate_action(truth_bad, action, self.tasks[0], self.contracts["lift"]), 0)

    def test_missing_forecast_rejected(self):
        with self.assertRaises(ValueError):
            ControllerContext(0, np.array([[8.0, np.nan]]))


if __name__ == "__main__":
    unittest.main()


