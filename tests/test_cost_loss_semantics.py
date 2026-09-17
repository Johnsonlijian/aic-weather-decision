"""Cost-loss semantics tests, adapted from the second review's check_semantics.py.

The reviewer supplied 12 constructed tests that pin down the decision semantics
independently of the empirical pipeline. They are reproduced here against this
project's own implementation, so that the semantics the manuscript states, the
semantics the code implements, and the semantics an external reader expects are
all the same object. These tests do not re-run the 45-station results.

Protect = defer or cancel the planned window. It never means permission to work.
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import numpy as np

from analyze_block_decisions import _expense


def protect(probability: float, cost_loss_ratio: float) -> bool:
    """Act iff P(event) >= C/L, ties resolved in favour of protection."""
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError("Probability must be finite and lie in [0, 1].")
    if not math.isfinite(cost_loss_ratio) or not 0.0 < cost_loss_ratio < 1.0:
        raise ValueError("This diagnostic requires 0 < C/L < 1.")
    return probability >= cost_loss_ratio


def realized_expense(event: int, protective_action: bool, cost: float, loss: float) -> float:
    """ell = C*a + L*(1-a)*Y."""
    if event not in (0, 1) or type(protective_action) is not bool:
        raise ValueError("event is binary and protective_action must be bool.")
    if not (math.isfinite(cost) and math.isfinite(loss) and 0 < cost < loss):
        raise ValueError("The simple non-trivial cost-loss model requires 0 < C < L.")
    return cost if protective_action else event * loss


def decision_family(scores) -> set[tuple[bool, ...]]:
    """Finite-sample upper-level sets, including the empty and full sets."""
    if len(scores) == 0 or any(not math.isfinite(v) for v in scores):
        raise ValueError("Scores must be a nonempty finite sequence.")
    cuts = [*sorted(set(scores)), math.inf]
    return {tuple(v >= c for v in scores) for c in cuts}


class SemanticsTests(unittest.TestCase):
    def test_low_probability_does_not_protect(self):
        self.assertFalse(protect(0.1, 0.2))

    def test_high_probability_protects(self):
        self.assertTrue(protect(0.9, 0.2))

    def test_tie_protects(self):
        self.assertTrue(protect(0.2, 0.2))

    def test_figure1_example_is_not_protection(self):
        # Fig. 1: P(exceedance) = 0.49 against C/L = 0.60 - the lift is not deferred
        self.assertFalse(protect(0.49, 0.6))

    def test_loss_matrix(self):
        self.assertEqual(realized_expense(0, False, 2, 10), 0)
        self.assertEqual(realized_expense(1, False, 2, 10), 10)
        self.assertEqual(realized_expense(0, True, 2, 10), 2)
        self.assertEqual(realized_expense(1, True, 2, 10), 2)

    def test_rule_minimizes_declared_expected_cost(self):
        for p in (0, .1, .2, .49, .6, .9, 1):
            for r in (.01, .1, .2, .6, .9):
                chosen = r if protect(p, r) else p
                self.assertAlmostEqual(chosen, min(r, p))

    def test_old_rule_is_not_always_more_protective(self):
        self.assertGreater(1 / (1 + .2), .2)
        self.assertLess(1 / (1 + .8), .8)

    def test_step_calibration_family_can_be_strict_subset(self):
        raw = decision_family([1, 2, 3])
        cal = decision_family([.2, .2, .8])
        self.assertTrue(cal < raw)
        self.assertIn((False, True, True), raw)
        self.assertNotIn((False, True, True), cal)

    def test_strictly_monotone_transform_preserves_finite_family(self):
        self.assertEqual(decision_family([1, 2, 3]), decision_family([.1, .2, .8]))

    def test_equal_count_binning_alone_does_not_ensure_monotonicity(self):
        empirical_bin_rates = [.8, .2]
        self.assertGreater(empirical_bin_rates[0], empirical_bin_rates[1])

    def test_blind_replay_count_bound(self):
        # Table 1's 9,518 positives over 45 stations cannot coexist with a replay
        # whose per-station count peaks near 25.
        self.assertEqual(math.ceil(9518 / 45), 212)
        self.assertLess(45 * 25, 9518)

    def test_invalid_probability_rejected(self):
        for p in (-.1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                protect(p, .2)


class ProjectImplementationTests(unittest.TestCase):
    """The project's own expense function must implement the same matrix."""

    def test_project_expense_matches_the_loss_matrix(self):
        y = np.array([1.0, 0.0, 1.0, 0.0])
        protect_vec = np.array([True, False, False, True])
        r = 0.25
        # rows: (Y=1,a=1) -> r ; (0,0) -> 0 ; (1,0) -> 1 ; (0,1) -> r
        self.assertAlmostEqual(_expense(protect_vec, y, float(y.mean()), r),
                               (r + 0.0 + 1.0 + r) / 4.0, places=12)

    def test_project_expense_is_minimised_at_p_ge_r(self):
        r = 0.3
        p = np.array([0.05, 0.2, 0.3, 0.5, 0.8])
        y = (p >= r).astype(float)
        self.assertLess(_expense(p >= r, y, float(y.mean()), r),
                        _expense(p >= 1.0 / (1.0 + r), y, float(y.mean()), r))


if __name__ == "__main__":
    unittest.main(verbosity=2)
