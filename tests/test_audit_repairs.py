"""Regression tests for the independent-audit repairs (2026-09-16).

Each test corresponds to a defect that was found in review and fixed:

* the cost-loss decision threshold was the safety-margin fractile 1/(1+r)
  instead of the expense-optimal C/L = r;
* reliability bins were closed on both ends, so every bin boundary was counted
  twice and the bin counts exceeded the sample size;
* the KNMI hourly `R` field was decoded as an amount in tenths of a millimetre
  although it is a 0/1 occurrence flag (and `DR` was renamed as a degree value);
* the calibrated rule was compared against an arbitrarily fixed physical
  threshold instead of a raw threshold tuned on the same calibration split.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import numpy as np
import pandas as pd

from analyze_block_decisions import (COST_LOSS_RATIOS, RELIABILITY_EDGES, _expense,
                                     _reliability, economic_value, tuned_raw_threshold)
from calibration import BinnedCalibrator, reliability_table
from download_inputs import parse_knmi


class CostLossTests(unittest.TestCase):
    """Act iff P(event) >= C/L, with C = r and L = 1."""

    def test_threshold_is_cost_loss_ratio_not_margin(self):
        self.assertTrue(np.all(COST_LOSS_RATIOS > 0) and np.all(COST_LOSS_RATIOS < 1),
                        "the standardised REV requires 0 < C/L < 1")
        self.assertAlmostEqual(float(COST_LOSS_RATIOS[0]), 0.01, places=6)
        self.assertAlmostEqual(float(COST_LOSS_RATIOS[-1]), 0.99, places=6)

    def test_expense_matches_definition(self):
        y = np.array([1.0, 0.0, 1.0, 0.0])
        act = np.array([True, True, False, False])
        # C = 0.4 per action, L = 1 per missed event
        self.assertAlmostEqual(_expense(act, y, float(y.mean()), 0.4),
                               0.4 * 0.5 + 1.0 * 0.25, places=12)

    def test_optimal_action_set_uses_p_ge_r(self):
        # A perfectly reliable predictor: acting iff p >= r must be optimal, and
        # the safety-margin rule p >= 1/(1+r) must act on a strictly smaller set.
        r = 0.3
        p = np.array([0.05, 0.2, 0.3, 0.5, 0.8])
        y = (p >= r).astype(float)
        optimal = p >= r
        margin = p >= 1.0 / (1.0 + r)
        self.assertLess(_expense(optimal, y, float(y.mean()), r),
                        _expense(margin, y, float(y.mean()), r))

    def test_economic_value_reports_both_rules(self):
        rows = []
        start = pd.Timestamp("2021-07-01", tz="UTC")
        for i in range(6000):
            x, y = [(5, 0), (11, 0), (13, 1), (21, 1)][i % 4]
            epoch = start + pd.Timedelta(hours=6 * i)
            if epoch < pd.Timestamp("2024-01-01", tz="UTC"):
                split = "FIT"
            elif epoch < pd.Timestamp("2025-01-01", tz="UTC"):
                split = "CAL"
            else:
                split = "TEST"
            rows.append({"station_id": "s1", "epoch": epoch, "split": split,
                         "block_max_L12": float(x), "L12_thr12.0": y})
        frame = pd.DataFrame(rows)
        self.assertTrue({"FIT", "CAL", "TEST"} <= set(frame["split"]))
        out = economic_value(frame, 12, 12.0)
        self.assertEqual(out["cost_loss_semantics"][:21], "act iff P(event) >= C")
        for row in out["curve"]:
            self.assertAlmostEqual(row["critical_prob"], row["cost_loss_ratio"], places=12)
            self.assertIn("tuned_raw", row["rules"])
            # the modelled action is protection, and the superseded safety-margin
            # rule is no longer part of the reported comparison
            self.assertIn("protect", row["action_name"])
            self.assertNotIn("calibrated_margin", row["rules"])
            for rule in row["rules"].values():
                self.assertIn("protection_rate", rule)
                self.assertIn("n_protected", rule)


class TunedRawTests(unittest.TestCase):
    def test_tuned_threshold_minimises_calibration_expense(self):
        rng = np.random.default_rng(0)
        x = rng.gamma(2.0, 4.0, size=4000) + 5.0
        y = (x > 14.0).astype(float)
        r = 0.25
        t = tuned_raw_threshold(x, y, r)
        cand = np.unique(np.quantile(x, np.linspace(0.0, 1.0, 201)))
        s = float(y.mean())
        best = min(_expense(x >= c, y, s, r) for c in cand)
        self.assertAlmostEqual(_expense(x >= t, y, s, r), best, places=12)

    def test_monotone_calibration_cannot_add_action_sets(self):
        # The property that makes the tuned-raw control the right comparison:
        # for a monotone map every probability threshold induces the same action
        # set as *some* raw threshold, so calibration cannot reach action sets
        # that a tuned raw threshold could not also reach.
        rng = np.random.default_rng(1)
        x = rng.normal(12.0, 3.0, size=3000)
        y = (x + rng.normal(0, 1.0, size=3000) > 12.5).astype(float)
        p = BinnedCalibrator().fit(x, y).predict(x)
        self.assertTrue(np.all(np.diff(p[np.argsort(x)]) >= -1e-12),
                        "the binned calibrator must be monotone in the forecast")
        for r in (0.05, 0.2, 0.5, 0.8):
            act_p = p >= r
            if not act_p.any():
                self.assertFalse((p >= r).any())
                continue
            x0 = float(np.min(x[act_p]))
            self.assertTrue(np.array_equal(act_p, x >= x0),
                            f"action set at r={r} is not expressible as a raw threshold")


class ReliabilityTests(unittest.TestCase):
    def test_bins_are_disjoint_and_complete(self):
        p = np.array([0.0, 0.0, 0.05, 0.1, 0.1, 0.5, 0.999, 1.0, 1.0])
        y = np.array([0, 0, 0, 1, 1, 1, 1, 1, 0], dtype=float)
        rows = reliability_table(p, y, edges=RELIABILITY_EDGES)
        self.assertEqual(sum(r["n"] for r in rows), p.size)

    def test_no_double_counting_at_edges(self):
        # Values that fall exactly on a bin edge are the defect case: the old
        # closed-interval form counted each of them in two bins.
        p = np.tile(np.linspace(0.0, 1.0, 10), 5)
        y = (p > 0.5).astype(float)
        for edges in (None, RELIABILITY_EDGES):
            rows = reliability_table(p, y, bins=10, edges=edges)
            self.assertEqual(sum(r["n"] for r in rows), p.size,
                             f"boundary values counted twice with edges={edges}")

    def test_module_local_reliability_sums_to_sample(self):
        p = np.linspace(0.0, 1.0, 101)
        y = (p > 0.5).astype(float)
        rows = _reliability(p, y)
        self.assertEqual(sum(r["n"] for r in rows), p.size)


class KnmiFieldTests(unittest.TestCase):
    HEADER = "# STN,YYYYMMDD,HH,FH,FX,T,R,RH,DR\n"

    def _parse(self, row: str):
        return parse_knmi(self.HEADER + row + "\n")[0]

    def test_r_is_an_occurrence_flag_not_an_amount(self):
        item = self._parse("  260,20250101,  1,  30,  85,  45,1,  53,  10")
        self.assertEqual(item["R_occurrence"], 1)
        self.assertNotIn("R_mm", item, "R must never be decoded as a millimetre amount")
        self.assertNotIn("DR_deg", item, "DR is a duration, not an angle")

    def test_rh_amount_in_millimetres(self):
        item = self._parse("  260,20250101,  1,  30,  85,  45,1,  53,  10")
        self.assertAlmostEqual(item["RH_amount_mm"], 5.3, places=12)
        self.assertFalse(item["RH_trace"])
        self.assertAlmostEqual(item["DR_hours"], 1.0, places=12)

    def test_trace_is_censored_not_dry(self):
        item = self._parse("  260,20250101,  2,  30,  85,  45,1,  -1,   3")
        self.assertTrue(item["RH_trace"])
        self.assertIsNone(item["RH_amount_mm"])
        self.assertEqual(item["RH_lower_mm"], 0.0)
        self.assertEqual(item["RH_upper_mm_exclusive"], 0.05)

    def test_rejects_non_binary_occurrence_flag(self):
        with self.assertRaises(ValueError):
            self._parse("  260,20250101,  3,  30,  85,  45,2,  53,  10")

    def test_temperature_scale_unchanged(self):
        item = self._parse("  260,20250101,  4,  30,  85, -25,0,   0,   0")
        self.assertAlmostEqual(item["T_degC"], -2.5, places=12)


class WithdrawnAnalysisTests(unittest.TestCase):
    def test_multihazard_refuses_to_rerun_by_default(self):
        import analyze_multihazard as mh
        argv = sys.argv
        try:
            sys.argv = ["analyze_multihazard.py"]
            with self.assertRaises(SystemExit) as ctx:
                mh.main()
            self.assertIn("WITHDRAWN", str(ctx.exception))
        finally:
            sys.argv = argv


if __name__ == "__main__":
    unittest.main(verbosity=2)
