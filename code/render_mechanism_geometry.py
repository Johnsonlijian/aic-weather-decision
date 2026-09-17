"""Decision-geometry mechanism figure (replaces the box-arrow version).

The mechanism is drawn, not written:

Panel A -- what the raw rule compares.  A 12 h decision window with the
in-service limit as a horizontal line, the observed hourly maxima as bars, the
true block event as a shaded exceedance, and the forecast block maximum as a
single point.  The point sits below the line while the event occurs: the miss is
visible in the geometry.

Panel B -- what calibration estimates.  The real fitted binned calibration curve
P(event | forecast block max) for the 12 m/s limit, with the raw rule's 0/1 step
at the limit for contrast, and one risk setting p* separating work from stop.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from calibration import BinnedCalibrator

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_figures" / "output"

BLUE = "#1d4ed8"
SLATE = "#52606d"
AMBER = "#b45309"
RED = "#c53030"
GREEN = "#2f855a"
PURPLE = "#6b46c1"
INK = "#1e293b"
GRID = "#cbd5e1"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": SLATE,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
})

LIMIT = 12.0
P_STAR = 0.20


def panel_a(ax):
    hours = np.arange(1, 13)
    # schematic-but-typical trajectory; the spike is the decision event
    obs = np.array([6.5, 7.0, 6.0, 7.5, 8.0, 7.0, 13.2, 8.5, 7.0, 6.5, 6.0, 5.5])
    spike = obs > LIMIT
    ax.bar(hours, obs, color=[RED if s else BLUE for s in spike], alpha=0.85, width=0.72)
    ax.axhline(LIMIT, color=INK, ls="--", lw=1.6)
    ax.text(0.2, LIMIT + 0.5, f"in-service limit  b = {LIMIT:g} m/s",
            fontsize=11, color=INK, va="bottom")
    ax.annotate("block event:\nany hour > b",
                xy=(7, 13.2), xytext=(9.2, 14.6),
                fontsize=10.5, color=RED, ha="center",
                arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.4))
    # forecast block maximum: what the raw rule reads
    m = 10.8
    ax.scatter([11.5], [m], marker="*", s=320, color=AMBER, zorder=6)
    ax.annotate("forecast block max  m\n(the only thing the\nraw rule reads)",
                xy=(11.5, m), xytext=(9.3, 4.6),
                fontsize=10.5, color=AMBER, ha="center",
                arrowprops=dict(arrowstyle="-|>", color=AMBER, lw=1.4))
    ax.annotate("m < b  ⇒  \"safe\"", xy=(11.5, m), xytext=(11.5, 8.2),
                fontsize=10.5, color=AMBER, ha="center")
    ax.set_xlabel("Hours of the 12 h decision window")
    ax.set_ylabel("Wind (m/s)")
    ax.set_ylim(0, 16.5)
    ax.set_xticks([2, 4, 6, 8, 10, 12])
    ax.set_title("a.  What the raw rule compares", fontsize=12, color=INK, loc="left")
    ax.text(1.02, 1.0, "schematic trajectory", transform=ax.transAxes, fontsize=9,
            color=SLATE, ha="right", va="top", style="italic")
    ax.text(0.02, 0.05, "MISS: the rule says safe while the event occurs",
            transform=ax.transAxes, fontsize=11.5, color=RED, fontweight="bold")


def panel_b(ax):
    frame = pd.read_csv(ROOT / "outputs" / "decision_epochs_age12_fx.csv")
    # the curve is the real fitted model on the 2021-2023 fit split only
    fit = frame[frame["split"] == "FIT"]
    label = f"L12_thr{LIMIT}"
    model = BinnedCalibrator().fit(fit["block_max_L12"].to_numpy(float),
                                   fit[label].to_numpy(float))
    m = np.linspace(4, 22, 120)
    p = model.predict(m)
    ax.plot(m, p, color=GREEN, lw=2.6, label="calibrated  P(event | m)")
    ax.step([4, LIMIT, LIMIT, 22], [0, 0, 1, 1], where="post",
            color=RED, ls="--", lw=2.0, label="raw rule: 0/1 step at b")
    ax.axhline(P_STAR, color=PURPLE, ls=":", lw=1.6)
    ax.text(22.2, P_STAR + 0.015, f"risk setting  p* = {P_STAR:g}", fontsize=10,
            color=PURPLE, ha="right")
    ax.fill_between(m, 0, 1, where=(p <= P_STAR), color=GREEN, alpha=0.08)
    ax.annotate("work", xy=(7.5, 0.05), fontsize=12, color=GREEN, ha="center", fontweight="bold")
    ax.annotate("stop", xy=(16.5, 0.86), fontsize=12, color=RED, ha="center", fontweight="bold")
    ax.axvline(LIMIT, color=INK, ls="--", lw=1.0, alpha=0.5)
    ax.text(LIMIT + 0.15, 0.42, "b", fontsize=11, color=INK)
    ax.set_xlabel("Forecast block maximum  m  (m/s)")
    ax.set_ylabel("Probability the block event occurs")
    ax.set_xlim(4, 24)
    ax.set_ylim(0, 1.04)
    ax.set_title("b.  What calibration estimates", fontsize=12, color=INK, loc="left")
    ax.legend(fontsize=9.5, frameon=False, loc="upper left")
    ax.text(0.02, 0.05, "REPAIR: the step becomes the true event rate",
            transform=ax.transAxes, fontsize=11.5, color=GREEN, fontweight="bold")


fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.9))
panel_a(axes[0])
panel_b(axes[1])
fig.suptitle("", fontsize=1)
fig.tight_layout(w_pad=2.2)
for ext in ("svg", "pdf", "png"):
    fig.savefig(OUT / f"fig1_forecast_decision_mechanism.{ext}", dpi=220,
                bbox_inches="tight", facecolor="white")
print("decision-geometry mechanism figure written")
