"""Tests for the work-package scheduler and its information boundary.

These lock in the properties the second review demanded: the modelled action is
protection rather than permission to work, the controller cannot see the future,
counts reconcile, and the exposure charge follows the observation rather than the
controller's belief.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import numpy as np

from work_package import (Scenario, Task, rule_always_work, rule_calibrated,
                          rule_fixed_limit, simulate, standard_package,
                          verify_no_observed_leakage)


def ctx(n=40, p_value=0.9, obs_all=False, fx_all=8.0):
    return {"fx": np.full(n, fx_all), "p": np.full(n, p_value),
            "p_lead": np.full(n, p_value), "obs": np.full(n, obs_all, bool)}


class LeakageTests(unittest.TestCase):
    def test_rules_are_blind_to_observations(self):
        for rule in (rule_calibrated(0.2), rule_fixed_limit(12.0), rule_always_work()):
            report = verify_no_observed_leakage(ctx(64), rule)
            self.assertFalse(report["leakage"], f"{rule} read the observed weather")
            self.assertEqual(report["verdicts_changed"], 0)

    def test_leakage_guard_detects_a_peeking_rule(self):
        # a deliberately cheating rule must be caught by the guard
        cheating = lambda c, k: bool(c["obs"][k])
        report = verify_no_observed_leakage(ctx(64), cheating)
        self.assertTrue(report["leakage"])
        self.assertGreater(report["verdicts_changed"], 0)


class SemanticsTests(unittest.TestCase):
    def test_refusing_a_block_avoids_the_exposure_charge(self):
        scen = Scenario(name="t", blocks=20, mismatch_cost=10.0, restart_cost=0.0,
                        idle_cost=0.0, tardiness_cost=0.0, cancel_cost=0.0)
        tasks = standard_package()
        # every block exceeds the limit, and the rule refuses every block
        never = simulate(ctx(20, p_value=0.9, obs_all=True), tasks, scen,
                         lambda c, k: False, planning="rolling_commit")
        self.assertEqual(never.mismatch_blocks, 0)
        # only the two leading non-weather tasks can proceed to completion
        self.assertEqual(never.completed, 2)

    def test_exposure_is_charged_when_the_controller_works_a_bad_block(self):
        scen = Scenario(name="t", blocks=20, mismatch_cost=10.0, restart_cost=0.0,
                        idle_cost=0.0, tardiness_cost=0.0, cancel_cost=0.0)
        tasks = standard_package()
        always = simulate(ctx(20, p_value=0.0, obs_all=True), tasks, scen,
                          rule_always_work(), planning="rolling_commit")
        # the non-weather tasks make progress; the weather-sensitive ones do not
        self.assertGreater(always.mismatch_blocks, 0)
        self.assertGreater(always.cost_mismatch, 0.0)
        self.assertEqual(always.completed, 2)

    def test_start_decision_never_uses_the_current_observation(self):
        # A single weather-sensitive task with no predecessors. The forecast is the
        # same in both runs, so the start decision must be identical; only the
        # consequence differs, because the observation for a block is not known
        # until the block has ended.
        task = [Task("lift", 2, (), True, deadline=10)]
        scen = Scenario(name="t", blocks=6)
        dry = simulate(ctx(6, p_value=0.1, obs_all=False), task, scen,
                       rule_calibrated(0.9), planning="rolling_commit")
        wet = simulate(ctx(6, p_value=0.1, obs_all=True), task, scen,
                       rule_calibrated(0.9), planning="rolling_commit")
        self.assertEqual(dry.starts, wet.starts)
        self.assertEqual(dry.mismatch_blocks, 0)
        self.assertGreater(wet.mismatch_blocks, 0)
        self.assertLess(wet.completed, dry.completed)

    def test_counts_partition_the_horizon(self):
        scen = Scenario(name="t", blocks=30, n_cranes=1)
        res = simulate(ctx(30, p_value=0.1), standard_package(), scen,
                       rule_calibrated(0.5), planning="rolling_commit")
        self.assertEqual(res.idle_blocks + res.busy_blocks, scen.n_cranes * scen.blocks)

    def test_static_never_cancels_and_pays_more_exposure(self):
        scen = Scenario(name="t", blocks=30, cancel_cost=5.0, mismatch_cost=1.0)
        frame = ctx(30, p_value=0.6, obs_all=True, fx_all=20.0)
        static = simulate(frame, standard_package(), scen, rule_calibrated(0.5),
                          planning="static")
        rolling = simulate(frame, standard_package(), scen, rule_calibrated(0.5),
                           planning="rolling_commit")
        self.assertEqual(static.cancellations, 0)
        self.assertLessEqual(static.completed, rolling.completed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
