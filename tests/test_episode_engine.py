import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from episode_engine import (
    Activity,
    ForecastRun,
    run_episode,
    verify_episode_trace,
)


class EpisodeEngineTests(unittest.TestCase):
    def run_basic(self, *, truth, policy="window", state_mode="asymmetric",
                  run=None, tasks=None, capacity=(1,), cutoff=None):
        if tasks is None:
            tasks = [Activity("lift", 2, (), (1,), sensitive=True)]
        result = run_episode(tasks, capacity, truth, [] if run is None else [run],
                             policy=policy, state_mode=state_mode,
                             cutoff=cutoff)
        verify_episode_trace(tasks, capacity, result)
        return result

    def test_resource_capacity_is_reserved_across_active_tasks(self):
        tasks = [
            Activity("a", 2, (), (1,), sensitive=False),
            Activity("b", 1, (), (1,), sensitive=False),
        ]
        result = self.run_basic(truth=[8, 8, 8], policy="blind", tasks=tasks)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["starts"], {"a": 0, "b": 2})
        self.assertTrue(all(e["resource_use"] == [1] for e in result["events"]))

    def test_asymmetric_continuation_rule_differs_from_symmetric_planning(self):
        run = ForecastRun("r0", 0, 0, 0, np.array([[11.0, 15.0]]))
        asym = self.run_basic(truth=[11.0, 15.0], run=run,
                              state_mode="asymmetric")
        sym = self.run_basic(truth=[11.0, 15.0], run=run,
                             state_mode="symmetric")
        self.assertEqual(asym["starts"], {"lift": 0})
        self.assertEqual(sym["starts"], {})
        self.assertEqual(asym["status"], "complete")
        self.assertEqual(sym["status"], "censored")

    def test_forecast_is_unavailable_until_available_hour(self):
        run = ForecastRun("late", 0, 1, 0, np.full((2, 3), 8.0))
        result = self.run_basic(truth=[8, 8, 8], run=run)
        self.assertEqual(result["starts"], {"lift": 1})
        self.assertIsNone(result["events"][0]["forecast_run_id"])
        self.assertEqual(result["events"][1]["forecast_run_id"], "late")

    def test_breach_stops_episode_and_retains_cutoff_loss(self):
        run = ForecastRun("r0", 0, 0, 0, np.full((2, 3), 8.0))
        result = self.run_basic(truth=[8, 21, 8], run=run, cutoff=3)
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["window_breach_count"], 1)
        self.assertEqual(result["restricted_completion_hours"], 3)
        self.assertEqual(result["admin_cutoff_hours"], 3)
        self.assertEqual(result["unresolved_reason"], "window_breach")
        self.assertEqual(result["remaining_tasks"], ["lift"])

    def test_missing_active_weather_is_unresolved(self):
        run = ForecastRun("r0", 0, 0, 0, np.full((2, 2), 8.0))
        result = self.run_basic(truth=[8, np.nan], run=run)
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["unresolved_reason"], "missing_active_weather")

    def test_hidden_future_truth_cannot_change_first_decision(self):
        run = ForecastRun("r0", 0, 0, 0, np.full((2, 3), 8.0))
        good = self.run_basic(truth=[8, 8, 8], run=run)
        bad = self.run_basic(truth=[8, 25, 8], run=run)
        self.assertEqual(good["events"][0], bad["events"][0])
        self.assertEqual(good["starts"], {"lift": 0})
        self.assertEqual(bad["starts"], {"lift": 0})
        self.assertEqual(bad["status"], "unresolved")

    def test_operational_replay_rejects_constructed_forecasts(self):
        run = ForecastRun("r0", 0, 0, 0, np.full((1, 2), 8.0))
        with self.assertRaises(ValueError):
            run_episode([Activity("lift", 1, (), (1,), sensitive=True)],
                        (1,), [8], [run], source_type="operational_archive_replay")


if __name__ == "__main__":
    unittest.main()
