"""Rebuild the full figure system with the engineering-mechanism grammar.

Grammar chain (workflow-config/prompts/10-figure-engineering-domain.md):
    object -> external driver -> internal mechanism -> response/failure state
    -> method intervention -> evidence -> contribution.

Fig. 1 is a mechanism board: the six grammar stages on top, with the real
detector-failure and calibration-recovery numbers embedded as data insets below,
so the figure is an evidence diagram rather than a flowchart.
Figs. 2-4 upgrade the three result figures with the same colour semantics and
annotated take-aways.  Outputs are SVG + PDF + PNG.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_figures" / "output"

C = {
    "object": "#1d4ed8",   # blue: the operation object
    "driver": "#64748b",   # slate: external information driver
    "mismatch": "#d97706", # amber: the mechanism failure site
    "fail": "#c53030",     # red: failure state
    "fix": "#2f855a",      # green: intervention / repair
    "contribution": "#6b46c1",  # purple: contribution
    "ink": "#1e293b",
    "grid": "#cbd5e1",
}
FONT = "DejaVu Sans"


def save(fig, name):
    for ext in ("svg", "pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def detector_table():
    frame = pd.read_csv(ROOT / "outputs" / "decision_epochs_age12_fx.csv")
    frame["epoch"] = pd.to_datetime(frame["epoch"], utc=True)
    test = frame[(frame["epoch"] >= pd.Timestamp("2025-01-01", tz="UTC"))
                 & (frame["epoch"] < pd.Timestamp("2025-10-01", tz="UTC"))]
    rows = []
    for thr in (9.0, 12.0, 13.0, 16.5, 20.0):
        lab = f"L12_thr{thr}"
        y = test[lab].to_numpy()
        claim = (test["block_max_L12"] > thr).to_numpy()
        miss = 100 * ((~claim) & (y == 1)).sum() / max((y == 1).sum(), 1)
        fa = 100 * (claim & (y == 0)).sum() / max((y == 0).sum(), 1)
        rows.append((thr, miss, fa))
    return rows


def fig1_mechanism_board():
    rows = detector_table()
    limits = [r[0] for r in rows]
    miss = [r[1] for r in rows]
    fa = [r[2] for r in rows]

    cal = json.loads((ROOT / "outputs" / "g5_block_calibration.json").read_text())
    thr_map = {r["threshold"]: r for r in cal}
    skill_clim = [thr_map[t]["models"]["binned"]["test"]["skill_vs_climatology"] for t in limits]
    skill_raw = [thr_map[t]["models"]["binned"]["test"]["skill_vs_raw_threshold"] for t in limits]

    rev = json.loads((ROOT / "outputs" / "g5_block_economic_value.json").read_text())
    rev_map = {r["threshold"]: r for r in rev}
    rev_peak = [max((c["relative_economic_value"] for c in rev_map[t]["curve"]
                     if c["relative_economic_value"] == c["relative_economic_value"]),
                    default=np.nan) for t in limits]

    fig = plt.figure(figsize=(13.0, 7.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1.0],
                          left=0.02, right=0.98, top=0.97, bottom=0.06,
                          hspace=0.42, wspace=0.16)
    ax_top = fig.add_subplot(gs[0, :])
    ax_top.axis("off")
    ax_top.set_xlim(0, 100)
    ax_top.set_ylim(0, 10)

    def box(x, w, text, title, color, edge=None):
        y0, y1 = 4.2, 8.6
        ax_top.add_patch(plt.Rectangle((x, y0), w, y1 - y0, transform=ax_top.transData,
                                       facecolor=color, alpha=0.14,
                                       edgecolor=color, lw=1.6,
                                       clip_on=False))
        ax_top.text(x + w / 2, y1 + 0.42, title, ha="center", va="bottom",
                    fontsize=10.5, fontweight="bold", color=color, clip_on=False)
        ax_top.text(x + w / 2, (y0 + y1) / 2, text, ha="center", va="center",
                    fontsize=9.0, color=C["ink"], linespacing=1.5, clip_on=False)

    stages = [
        ("OPERATION OBJECT", "Tower-crane lift\nin-service limit b\n(9.0–20.0 m/s, sourced)", C["object"]),
        ("EXTERNAL DRIVER", "Archived as-issued\ngust forecast\n(4 h publication latency, audited)", C["driver"]),
        ("INTERNAL MECHANISM", "instantaneous grid gust\nread as\n\"window exceeded?\"", C["mismatch"]),
        ("FAILURE STATE", "Raw threshold rule\nmisses 45–63%\nfalse alarms 6.9%", C["fail"]),
        ("METHOD INTERVENTION", "Decision-level calibration\nP(window exceeded | forecast)\nbinned / logistic", C["fix"]),
        ("CONTRIBUTION", "One probability table\nper site and limit\n= a tunable risk dial", C["contribution"]),
    ]
    xs = [0, 17.5, 35.0, 52.5, 70.0, 87.5]
    w = 12.5
    for (title, text, color), x in zip(stages, xs):
        box(x, w, text, title, color)

    arrows = [
        (xs[0] + w, xs[1], "feeds the decision", C["driver"]),
        (xs[1] + w, xs[2], "compared as equals", C["mismatch"]),
        (xs[2] + w, xs[3], "misreads the event", C["fail"]),
        (xs[3] + w, xs[4], "re-estimates the event", C["fix"]),
        (xs[4] + w, xs[5], "tunable risk dial", C["contribution"]),
    ]
    for x0, x1, label, color in arrows:
        ax_top.annotate("", xy=(x1, 6.4), xytext=(x0, 6.4),
                        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.8))
        ax_top.text((x0 + x1) / 2, 7.2, label, ha="center", va="bottom",
                    fontsize=8.5, color=color)

    # evidence insets
    ax1 = fig.add_subplot(gs[1, 0])
    x = np.arange(len(limits))
    ax1.bar(x - 0.2, miss, 0.4, color=C["fail"], label="漏报")
    ax1.bar(x + 0.2, fa, 0.4, color=C["driver"], label="安全块误报")
    ax1.set_xticks(x, [f"{t:g}" for t in limits])
    ax1.set_xlabel("In-service limit (m/s)")
    ax1.set_ylabel("Raw-rule failure rate (%)")
    ax1.set_title("a. Detector failure (held-out 2025)", fontsize=10)
    ax1.legend(["Missed events", "False alarms on safe blocks"], fontsize=8, frameon=False)
    ax1.set_ylim(0, 80)
    ax1.grid(axis="y", color=C["grid"], lw=0.6)

    ax2 = fig.add_subplot(gs[1, 1])
    ax2.bar(x - 0.2, skill_clim, 0.4, color=C["contribution"], label="对气候态")
    ax2.bar(x + 0.2, skill_raw, 0.4, color=C["fix"], label="对原始阈值")
    ax2.axhline(0, color=C["ink"], lw=0.8)
    ax2.set_xticks(x, [f"{t:g}" for t in limits])
    ax2.set_xlabel("In-service limit (m/s)")
    ax2.set_ylabel("Held-out Brier skill")
    ax2.set_title("b. Calibration repair (same window, same data)", fontsize=10)
    ax2.legend(["vs climatology", "vs raw threshold"], fontsize=8, frameon=False)
    ax2.set_ylim(-0.05, 0.5)
    ax2.grid(axis="y", color=C["grid"], lw=0.6)

    ax3 = fig.add_subplot(gs[1, 2])
    ax3.plot(limits, rev_peak, "-o", color=C["object"], lw=2, ms=6)
    for t, v in zip(limits, rev_peak):
        if np.isfinite(v):
            ax3.annotate(f"{v:.2f}", (t, v), textcoords="offset points",
                         xytext=(0, 7), ha="center", fontsize=8.5, color=C["object"])
    ax3.set_xlabel("In-service limit (m/s)")
    ax3.set_ylabel("Peak REV")
    ax3.set_title("c. Economic value of the calibrated rule", fontsize=10)
    ax3.set_ylim(-0.05, 0.5)
    ax3.grid(color=C["grid"], lw=0.6)

    save(fig, "fig1_forecast_decision_mechanism")


def fig2_reliability():
    cal = json.loads((ROOT / "outputs" / "g5_block_calibration.json").read_text())
    row = next(r for r in cal if abs(r["threshold"] - 12.0) < 1e-9)
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    for label, color, marker in (("cal", C["driver"], "o"), ("test", C["object"], "s")):
        rel = row["models"]["binned"][label]["reliability"]
        ax.plot([r["p_mean"] for r in rel], [r["obs_freq"] for r in rel],
                marker=marker, ms=6, ls="--", color=color, lw=1.4,
                label="calibration split" if label == "cal" else "held-out test split")
    base = row["base_rate"]
    ax.axhline(base, color=C["fix"], ls=":", lw=1.4,
               label=f"climatology baseline {base:.3f}")
    ax.plot([0, 1], [0, 1], ls="-", color=C["ink"], lw=0.8, alpha=0.5)
    ax.set_xlabel("Calibrated forecast probability")
    ax.set_ylabel("Observed event frequency")
    ax.set_title("12 m/s: calibration turns the forecast into a usable event probability")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    save(fig, "fig_reliability_12ms")


def fig3_frontier():
    campaign = json.loads((ROOT / "outputs" / "g5_block_campaign.json").read_text())
    row = next(r for r in campaign if abs(r["threshold"] - 12.0) < 1e-9)
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    pts = {"blind": [], "raw": [], "calibrated": []}
    for station, policies in row["stations"].items():
        for name, v in policies.items():
            if name == "blind":
                pts["blind"].append((v["unsafe_blocks"], v["missed_safe_blocks"]))
            elif name == "raw":
                pts["raw"].append((v["unsafe_blocks"], v["missed_safe_blocks"]))
            elif name.startswith("calibrated"):
                pts["calibrated"].append((v["unsafe_blocks"], v["missed_safe_blocks"]))
    blind = np.array(pts["blind"])
    raw = np.array(pts["raw"])
    cal = np.array(pts["calibrated"])
    if len(cal):
        order = np.argsort(cal[:, 0])
        ax.plot(cal[order, 0], cal[order, 1], "-", color=C["fix"], lw=1.6,
                label="calibrated frontier (risk dial)")
    ax.scatter(*blind.mean(axis=0), s=150, marker="o", color=C["fail"],
               label="blind (fastest, most exposure)", zorder=5)
    ax.scatter(*raw.mean(axis=0), s=120, marker="X", color=C["driver"],
               label="raw threshold (fixed point, no dial)", zorder=5)
    ax.scatter(cal[:, 0], cal[:, 1], s=45, marker="D", color=C["object"],
               label="calibrated rule (p* sweep)", zorder=4)
    ax.set_xlabel("Unsafe-exposure blocks")
    ax.set_ylabel("Missed safe blocks")
    ax.set_title("12 m/s: calibration turns a fixed rule into a tunable frontier")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(color=C["grid"], lw=0.5)
    fig.tight_layout()
    save(fig, "fig_risk_efficiency_12ms")


def fig4_rev():
    rev = json.loads((ROOT / "outputs" / "g5_block_economic_value.json").read_text())
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    for r in rev:
        curve = r["curve"]
        lw = 2.0 if r["threshold"] in (9.0, 12.0) else 1.2
        alpha = 1.0 if r["threshold"] in (9.0, 12.0) else 0.55
        ax.plot([c["cost_loss_ratio"] for c in curve],
                [c["relative_economic_value"] for c in curve],
                lw=lw, alpha=alpha, label=f"{r['threshold']:g} m/s")
        peak = max((c["relative_economic_value"] for c in curve
                    if c["relative_economic_value"] == c["relative_economic_value"]),
                   default=np.nan)
        if np.isfinite(peak) and r["threshold"] in (9.0, 12.0):
            arg = max(curve, key=lambda c: c["relative_economic_value"]
                      if c["relative_economic_value"] == c["relative_economic_value"] else -1)
            ax.plot(arg["cost_loss_ratio"], arg["relative_economic_value"], "v",
                    color=C["object"], ms=8)
    ax.axvline(1.0, color=C["ink"], ls=":", lw=1.0, alpha=0.6)
    ax.text(1.02, 0.02, "C/L = 1", fontsize=8, color=C["ink"], rotation=90, va="bottom")
    ax.set_xscale("log")
    ax.axhline(0, color=C["ink"], lw=0.8)
    ax.set_xlabel("Cost-loss ratio C/L")
    ax.set_ylabel("Relative economic value")
    ax.set_title("Value of the calibrated rule decays as events get rarer")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    save(fig, "fig_economic_value")


if __name__ == "__main__":
    fig1_mechanism_board()
    fig2_reliability()
    fig3_frontier()
    fig4_rev()
    print("figure system rebuilt ->", OUT)
