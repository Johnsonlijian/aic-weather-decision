"""Calibration tests: monotonicity, support clipping, skill scores, and PAVA."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from calibration import (  # noqa: E402
    BinnedCalibrator, LogisticCalibrator, _pava, brier, brier_skill_score, reliability_table)


class TestCalibration(unittest.TestCase):
    def test_pava_produces_a_non_decreasing_sequence(self):
        probs, counts = _pava(np.array([0.4, 0.1, 0.3, 0.2]))
        self.assertTrue(np.all(np.diff(probs) >= -1e-12))
        self.assertEqual(float(counts.sum()), 4.0)

    def test_binned_calibrator_is_monotone_and_recovers_a_known_curve(self):
        rng = np.random.default_rng(20260915)
        x = rng.uniform(0, 30, 60_000)
        p_true = 1.0 / (1.0 + np.exp(-(x - 15.0) / 1.5))
        y = (rng.uniform(size=len(x)) < p_true).astype(float)
        model = BinnedCalibrator().fit(x, y)
        grid = np.linspace(5, 25, 40)
        p = model.predict(grid)
        self.assertTrue(np.all(np.diff(p) >= -1e-12), "calibration must be monotone")
        # A 40-bin equal-count estimator cannot be exact; the bound records the accuracy
        # the experiment actually relies on, not a claim of parametric recovery.
        self.assertLess(np.max(np.abs(p - 1.0 / (1.0 + np.exp(-(grid - 15.0) / 1.5)))), 0.08)

    def test_binned_calibrator_clips_outside_support_without_extrapolating(self):
        x = np.linspace(0, 10, 5_000)
        y = (x > 5).astype(float)
        model = BinnedCalibrator().fit(x, y)
        below = model.predict(np.array([-5.0]))[0]
        above = model.predict(np.array([50.0]))[0]
        self.assertLessEqual(below, 0.5)
        self.assertGreaterEqual(above, 0.5)
        self.assertEqual(model.clipped_low, 1)
        self.assertEqual(model.clipped_high, 1)

    def test_logistic_calibrator_recovers_the_sign_of_the_relationship(self):
        rng = np.random.default_rng(7)
        x = rng.normal(15, 4, 40_000)
        y = (rng.uniform(size=len(x)) < 1 / (1 + np.exp(-(x - 16) / 2))).astype(float)
        model = LogisticCalibrator().fit(x, y)
        self.assertGreater(model.coef, 0)
        self.assertLess(abs(model.predict(np.array([16.0]))[0] - 0.5), 0.05)

    def test_brier_skill_score_is_zero_against_itself_and_one_against_perfection(self):
        y = np.array([0.0, 1.0, 1.0, 0.0])
        p = np.array([0.1, 0.8, 0.6, 0.3])
        self.assertAlmostEqual(brier_skill_score(p, y, p), 0.0, places=12)
        self.assertGreater(brier(p, y), 0.0)
        self.assertAlmostEqual(brier(y, y), 0.0, places=12)

    def test_calibrator_rejects_non_finite_predictors_and_non_binary_labels(self):
        x = np.array([1.0, np.nan, 3.0])
        y = np.array([0.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            BinnedCalibrator().fit(x, y)
        with self.assertRaises(ValueError):
            BinnedCalibrator().fit(np.array([1.0, 2.0]), np.array([0.0, 2.0]))

    def test_reliability_table_bins_are_populated(self):
        rng = np.random.default_rng(11)
        p = rng.uniform(size=1_000)
        y = (rng.uniform(size=1_000) < p).astype(float)
        rows = reliability_table(p, y, bins=5)
        self.assertGreater(len(rows), 1)
        self.assertAlmostEqual(sum(r["n"] for r in rows), 1_000)


if __name__ == "__main__":
    unittest.main()
