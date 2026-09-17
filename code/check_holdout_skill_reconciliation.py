"""Reconcile the pooled post-sample skill with the per-month skills.

The pooled number is -0.381 while all eleven monthly numbers are positive. A Brier
score is a mean over rows, so pooling months must give a weighted average of the
monthly Brier scores; the skill is a ratio of two such averages, which can fall
outside the range of the monthly ratios, but the gap has to be explained by the
numbers rather than asserted. This computes both decompositions explicitly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from calibration import BinnedCalibrator, brier, brier_skill_score

ROOT = Path(__file__).resolve().parents[1]
H = 12
LABEL = f"L{H}_thr12.0"
PRED = f"block_max_L{H}"
LIMIT = 12.0

cols = ["station_id", "epoch", "split", PRED, LABEL]
frozen = pd.read_csv(ROOT / "outputs" / "epochs_multi3.csv", usecols=cols)
hold = pd.read_csv(ROOT / "outputs" / "epochs_holdout.csv", usecols=cols)
for d in (frozen, hold):
    d["epoch"] = pd.to_datetime(d["epoch"], utc=True)

fit = frozen[frozen["split"] == "FIT"]
model = BinnedCalibrator().fit(fit[PRED].to_numpy(float), fit[LABEL].to_numpy(float))
frozen_base = float(fit[LABEL].mean())

hold = hold.sort_values("epoch").reset_index(drop=True)
x = hold[PRED].to_numpy(float)
y = hold[LABEL].to_numpy(float)
p = model.predict(x)
base = np.full_like(y, frozen_base)
hold["bs_model"] = (p - y) ** 2
hold["bs_clim"] = (base - y) ** 2
hold["month"] = hold["epoch"].dt.strftime("%Y-%m")

bs_model = float(hold["bs_model"].mean())
bs_clim = float(hold["bs_clim"].mean())
print(f"pooled rows {len(hold):,}")
print(f"pooled Brier(model) {bs_model:.5f} | Brier(frozen climatology) {bs_clim:.5f}")
print(f"pooled skill = 1 - {bs_model:.5f}/{bs_clim:.5f} = {1 - bs_model / bs_clim:+.4f}")
print(f"library call  = {brier_skill_score(p, y, base):+.4f}   (must match)")
print()

g = hold.groupby("month")
m_model = g["bs_model"].mean()
m_clim = g["bs_clim"].mean()
m_skill = 1 - m_model / m_clim
n = g.size()
print(f"{'month':9s}{'n':>7s}{'BS_model':>10s}{'BS_clim':>10s}{'skill':>9s}")
for m in m_skill.index:
    print(f"{m:9s}{n[m]:7,d}{m_model[m]:10.5f}{m_clim[m]:10.5f}{m_skill[m]:+9.3f}")

w_model = float((m_model * n).sum() / n.sum())
w_clim = float((m_clim * n).sum() / n.sum())
print(f"\nweighted average of monthly BS_model {w_model:.5f} (pooled {bs_model:.5f})")
print(f"weighted average of monthly BS_clim  {w_clim:.5f} (pooled {bs_clim:.5f})")
print(f"skill from weighted averages = {1 - w_model / w_clim:+.4f}")
print()
print("reference spread across months: BS_clim ranges "
      f"{m_clim.min():.4f} to {m_clim.max():.4f} "
      f"(the frozen climatology is a poorer reference in months whose event rate "
      f"differs most from {frozen_base:.4f})")
print("model spread across months: BS_model ranges "
      f"{m_model.min():.4f} to {m_model.max():.4f}")
