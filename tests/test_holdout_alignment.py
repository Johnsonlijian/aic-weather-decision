"""Regression test for the hold-out evaluator's row alignment.

`analyze_holdout.py` sorts the hold-out frame by epoch and then builds the forecast,
label and probability arrays from it. An earlier version wrote

    x, y, p = hold[pred]..., hold[label]..., model.predict(x)

on one line after the sort. Python evaluates the right-hand side before binding, so
`p` was predicted from the *pre-sort* row order while `x` and `y` came from the sorted
frame. Against a scrambled input file that misaligned probabilities with labels and
reported a negative out-of-sample skill for a model that in fact transfers.

This test feeds the evaluator a deliberately out-of-order hold-out file and requires
the pooled skill to agree with an independent computation, so the same class of defect
cannot return silently.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"


def build_fixture(tmp: Path, *, shuffle_holdout: bool) -> None:
    """A synthetic frozen/holdout pair where the model is genuinely informative."""
    rng = np.random.default_rng(7)
    rows = []
    for split, n, offset in (("FIT", 3000, 0), ("CAL", 1000, 4000)):
        for i in range(n):
            epoch = pd.Timestamp("2021-06-01", tz="UTC") + pd.Timedelta(hours=6 * (offset + i))
            x = float(rng.gamma(2.0, 4.0) + 4.0)
            y = int(x > 11.0)
            rows.append({"station_id": "s1", "epoch": epoch, "split": split,
                         "block_max_L12": x, "L12_thr12.0": y})
    pd.DataFrame(rows).to_csv(tmp / "epochs_frozen.csv", index=False)

    hold = []
    for i in range(2000):
        epoch = pd.Timestamp("2025-10-01", tz="UTC") + pd.Timedelta(hours=6 * i)
        x = float(rng.gamma(2.0, 4.0) + 4.0)
        y = int(x > 11.0)
        hold.append({"station_id": "s1", "epoch": epoch, "split": "OTHER",
                     "block_max_L12": x, "L12_thr12.0": y})
    frame = pd.DataFrame(hold)
    if shuffle_holdout:
        frame = frame.sample(frac=1.0, random_state=3).reset_index(drop=True)
    frame.to_csv(tmp / "epochs_holdout.csv", index=False)


def run_evaluator(tmp: Path) -> dict:
    subprocess.run(
        [sys.executable, str(CODE / "analyze_holdout.py"),
         "--frozen-table", str(tmp / "epochs_frozen.csv"),
         "--holdout-table", str(tmp / "epochs_holdout.csv"),
         "--draws", "50", "--out", str(tmp / "holdout_evaluation.json")],
        cwd=str(ROOT), check=True, capture_output=True, text=True)
    # read the redirect target, never the production artefact: an earlier version of
    # this test overwrote outputs/g5_holdout_evaluation.json with synthetic numbers
    return json.loads((tmp / "holdout_evaluation.json").read_text(encoding="utf-8"))


def independent_skill(tmp: Path) -> float:
    """Recompute the pooled skill from the files without the evaluator's code path."""
    sys.path.insert(0, str(CODE))
    from calibration import BinnedCalibrator  # noqa: PLC0415
    frozen = pd.read_csv(tmp / "epochs_frozen.csv")
    hold = pd.read_csv(tmp / "epochs_holdout.csv")
    for d in (frozen, hold):
        d["epoch"] = pd.to_datetime(d["epoch"], utc=True)
    fit = frozen[frozen["split"] == "FIT"]
    model = BinnedCalibrator().fit(fit["block_max_L12"].to_numpy(float),
                                   fit["L12_thr12.0"].to_numpy(float))
    hold = hold.sort_values("epoch").reset_index(drop=True)
    x = hold["block_max_L12"].to_numpy(float)
    y = hold["L12_thr12.0"].to_numpy(float)
    p = model.predict(x)
    base = np.full_like(y, float(fit["L12_thr12.0"].mean()))
    return float(1.0 - np.mean((p - y) ** 2) / np.mean((base - y) ** 2))


class AlignmentTests(unittest.TestCase):
    def test_skill_matches_an_independent_computation_on_a_shuffled_file(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            build_fixture(tmp, shuffle_holdout=True)
            report = run_evaluator(tmp)
            expected = independent_skill(tmp)
            self.assertAlmostEqual(
                report["skill"]["vs_frozen_climatology"]["estimate"], expected, places=6,
                msg="the evaluator's pooled skill disagrees with an independent "
                    "recomputation, which is how a row-misalignment bug shows up")

    def test_pooled_skill_agrees_with_the_monthly_decomposition(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            build_fixture(tmp, shuffle_holdout=True)
            report = run_evaluator(tmp)
            self.assertTrue(report["skill_consistency"]["agree"])
            self.assertLess(abs(report["skill_consistency"]["pooled"]
                                - report["skill_consistency"]["from_monthly"]), 1e-9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
