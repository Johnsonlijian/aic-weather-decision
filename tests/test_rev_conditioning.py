"""Regression test for the relative-value normalisation's conditioning.

Relative economic value is

    REV = (E_clim - E) / (E_clim - E_perfect),  E_clim = min(r, s),  E_perfect = r*s

so the denominator is ``min(r, s) - r*s``. Once ``r > s`` that equals ``s*(1 - r)``, which
vanishes as ``r -> 1``; at the bottom of the grid it is bounded by ``r`` itself.

The artifact swept over 40 log-spaced ratios from 0.01 to 0.99 contains a fixed-limit
relative value of about -30.85 at ``r = 0.99`` and -8.63 at ``r = 0.01``. Those are the
denominator collapsing, not economic findings, and an earlier draft of the manuscript
quoted -0.913 without saying which of the 40 ratios produced it - which led a reviewer to
read the whole grid as reported. This test pins both halves of the fix: the five reported
ratios are well conditioned, and the grid extremes demonstrably are not.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "outputs" / "g5_block_v3_economic_value.json"
REPLAY = ROOT / "outputs" / "g5_replay_v3.json"
MANUSCRIPT = ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md"
REPORTED = (0.05, 0.1, 0.2, 0.4, 0.6)
FLOOR = 0.02


def denominator(r: float, s: float) -> float:
    return min(r, s) - r * s


class RevConditioning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rev = json.loads(REV.read_text(encoding="utf-8"))
        replay = json.loads(REPLAY.read_text(encoding="utf-8"))
        cls.s = replay["test_positives"] / replay["test_epochs"]
        cls.grid = sorted({c["cost_loss_ratio"] for row in cls.rev for c in row["curve"]})

    def test_denominator_identity_holds_on_the_grid(self):
        """min(r,s) - r*s is s*(1-r) above the event rate and r*(1-s) below it."""
        for r in self.grid:
            if r > self.s:
                self.assertAlmostEqual(denominator(r, self.s), self.s * (1 - r), places=12)
            else:
                self.assertAlmostEqual(denominator(r, self.s), r * (1 - self.s), places=12)

    def test_grid_is_forty_points_from_001_to_099(self):
        self.assertEqual(len(self.grid), 40)
        self.assertAlmostEqual(self.grid[0], 0.01, places=9)
        self.assertAlmostEqual(self.grid[-1], 0.99, places=9)

    def test_reported_ratios_are_well_conditioned(self):
        for r in REPORTED:
            self.assertGreater(denominator(r, self.s), FLOOR,
                               f"r={r} is too close to the vanishing end to report")

    def test_both_ends_of_the_grid_are_ill_conditioned(self):
        """The excursion is at both ends, which is why the figure leaves the panel twice."""
        self.assertLess(denominator(self.grid[-1], self.s), FLOOR)
        self.assertLess(denominator(self.grid[0], self.s), FLOOR)

    def test_extreme_relative_values_are_the_expected_artefact(self):
        """The -30.85 the reviewer found is reproduced here, so it is not a stale number."""
        row = next(r for r in self.rev if abs(r["threshold"] - 12.0) < 1e-9)
        top = next(c for c in row["curve"]
                   if abs(c["cost_loss_ratio"] - 0.99) < 1e-9)
        self.assertLess(top["rules"]["fixed_raw"]["relative_economic_value"], -20.0)

    # The manuscript is deliberately not redistributed while it is under submission, so
    # the release archive ships these tests without it. The numeric tests above still run
    # there; only the two that read the prose are skipped.
    @unittest.skipUnless(MANUSCRIPT.exists(), "manuscript not redistributed")
    def test_manuscript_does_not_quote_the_ill_conditioned_extremes(self):
        text = MANUSCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("-30.85", text)
        self.assertNotIn("-8.63", text)

    @unittest.skipUnless(MANUSCRIPT.exists(), "manuscript not redistributed")
    def test_manuscript_discloses_the_grid_and_the_conditioning(self):
        text = MANUSCRIPT.read_text(encoding="utf-8")
        self.assertIn("40-point log-spaced grid", text)
        self.assertIn("vanishes", text)
        for r in REPORTED:
            self.assertIn(f"{r:g}", text)


if __name__ == "__main__":
    unittest.main()
