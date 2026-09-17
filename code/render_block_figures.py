"""Render the result figures for the block-decision analysis.

Outputs SVG + PNG (and PDF for LaTeX) for:
1. Reliability diagram of the binned calibrator (CAL and TEST) for the 12 m/s limit.
2. Relative economic value: the calibrated rule against a raw threshold tuned on
   the same calibration split, and against the fixed documented limit.
3. The risk-efficiency replay: unsafe blocks vs missed safe blocks per policy.

All figures are data-derived; no value is hand-edited. The REV panel plots the
cost-loss ratio on the decision-relevant 0 < C/L < 1 range, because for C/L >= 1
"always act" is optimal and relative value degenerates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RULE_STYLE = (
    ("calibrated", "calibrated: protect when $\\hat P \\geq C/L$", "#1f77b4", "-"),
    ("tuned_raw", "tuned: protect above a calibrated-split threshold", "#d62728", "--"),
    ("fixed_raw", "operating limit used unchanged as the trigger", "#7f7f7f", ":"),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--prefix", default="g5_block_2cyc")
    parser.add_argument("--primary", type=float, default=12.0)
    parser.add_argument("--secondary", type=float, default=9.0)
    args = parser.parse_args()
    root: Path = args.root
    outdir = root / "paper_figures" / "output"
    outdir.mkdir(parents=True, exist_ok=True)

    calibration = json.loads((root / "outputs" / f"{args.prefix}_calibration.json").read_text())
    rev = json.loads((root / "outputs" / f"{args.prefix}_economic_value.json").read_text())
    replay = json.loads((root / "outputs" / f"{args.prefix.replace('block', 'replay')}.json").read_text())

    # --- 1. reliability diagram for the primary limit ----------------------
    row = next(r for r in calibration if abs(r["threshold"] - args.primary) < 1e-9)
    fig, ax = plt.subplots(figsize=(5.2, 4.0))
    for label, color, marker in (("cal", "#1f77b4", "o"), ("test", "#d62728", "s")):
        rel = row["models"]["binned"][label]["reliability"]
        ax.plot([r["p_mean"] for r in rel], [r["obs_freq"] for r in rel],
                marker=marker, ms=5, ls="--", color=color, label=label.upper())
    ax.plot([0, 1], [0, 1], ls=":", color="0.4", lw=1)
    ax.set_xlabel("Forecast probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title(f"Reliability of block-window calibration ({args.primary:g} m/s)")
    ax.legend(frameon=False)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    for ext in ("svg", "png", "pdf"):
        fig.savefig(outdir / f"fig_reliability_{args.primary:g}ms.{ext}")
    plt.close(fig)

    # --- 2. economic value: calibrated vs tuned raw vs documented limit ----
    panels = [args.primary, args.secondary]
    fig, axes = plt.subplots(1, len(panels), figsize=(9.4, 3.9), sharey=True)
    for ax, limit in zip(axes, panels):
        entry = next(r for r in rev if abs(r["threshold"] - limit) < 1e-9)
        curve = entry["curve"]
        xs = [c["cost_loss_ratio"] for c in curve]
        for rule, label, color, ls in RULE_STYLE:
            ys = [c["rules"][rule]["relative_economic_value"] for c in curve]
            ax.plot(xs, ys, color=color, ls=ls, lw=1.7, label=label)
        ax.axhline(0, color="0.6", lw=0.8)
        ax.set_xscale("log")
        ax.set_xlabel("Cost-loss ratio $C/L$")
        ax.set_title(f"{limit:g} m/s limit", fontsize=10)
        # the full range is shown because the operating-limit rule falls below the
        # axis at low ratios; clipping it would hide the largest effect in the panel
        ax.set_ylim(-1.0, 1.0)
    axes[0].set_ylabel("Relative economic value")
    axes[0].legend(frameon=False, fontsize=7.5, loc="upper left")
    fig.suptitle("Relative value of the planning trigger on the held-out split", fontsize=11)
    fig.tight_layout()
    for ext in ("svg", "png", "pdf"):
        fig.savefig(outdir / f"fig_economic_value.{ext}")
    plt.close(fig)

    # --- 3. per-station decision replay, reconciled with Table 1 -------------
    # x = exceedance epochs left unprotected ("missed"), y = event-free epochs
    # protected ("unnecessary protection"). Every held-out epoch is counted once
    # and no target truncates the replay, so the never-protect series sums to the
    # Table 1 positive count.
    ratio = 0.2
    cal_key = f"calibrated_r{ratio:g}"
    tuned_key = f"tuned_raw_r{ratio:g}"
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    series = (
        ("blind_work", "never protect (always work)", "#2ca02c", "o"),
        ("fixed_limit", f"protect when forecast > {args.primary:g} m/s", "#7f7f7f", "^"),
        (tuned_key, "protect above the tuned threshold", "#d62728", "s"),
        (cal_key, r"protect when $\hat P \geq C/L$", "#1f77b4", "D"),
    )
    for key, name, color, marker in series:
        pol = replay["policies"].get(key)
        if not pol:
            continue
        xs = [v["n_unprotected_positive"] for v in pol["per_station"].values()]
        ys = [v["n_protected_negative"] for v in pol["per_station"].values()]
        ax.scatter(xs, ys, color=color, marker=marker, s=38, label=name, alpha=0.85,
                   edgecolors="white", linewidths=0.4)
    missed_total = replay["policies"]["blind_work"]["n_unprotected_positive"]
    ax.set_xlabel("Exceedance epochs left unprotected (count)")
    ax.set_ylabel("Event-free epochs protected (count)")
    ax.set_title(f"Per-station decision replay, all {replay['test_epochs']:,} test epochs "
                 f"({args.primary:g} m/s)", fontsize=10)
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    fig.tight_layout()
    for ext in ("svg", "png", "pdf"):
        fig.savefig(outdir / f"fig_replay_{args.primary:g}ms.{ext}")
    plt.close(fig)
    print(f"replay: {replay['stations']} stations, {replay['test_epochs']:,} epochs, "
          f"{replay['test_positives']:,} positives; never-protect misses {missed_total:,}")

    print("figures written to", outdir)


if __name__ == "__main__":
    main()
