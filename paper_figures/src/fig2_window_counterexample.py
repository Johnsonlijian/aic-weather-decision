from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper_figures" / "output"
for d in (OUT / "svg", OUT / "pdf", OUT / "png"):
    d.mkdir(parents=True, exist_ok=True)

paths = {
    "A  contiguous calm slots": [8, 8, 8, 8, 8, 8, 25, 25],
    "B  fragmented calm slots": [8, 8, 25, 8, 8, 25, 8, 8],
}
start_limit, continuation_limit, duration = 11.1, 20.0, 3
rows = []
for label, values in paths.items():
    valid = []
    for t in range(len(values) - duration + 1):
        ok = values[t] <= start_limit and all(v <= continuation_limit for v in values[t + 1:t + duration])
        valid.append(int(ok))
    for h, v in enumerate(values):
        rows.append({"path": label, "slot": h, "weather_mps": v,
                     "valid_start": valid[h] if h < len(valid) else ""})
with (OUT / "window_counterexample.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.titleweight": "bold", "axes.spines.top": False,
                     "axes.spines.right": False})
fig, axes = plt.subplots(2, 1, figsize=(8.4, 5.1), sharex=True,
                         gridspec_kw={"hspace": 0.42})
fig.subplots_adjust(left=0.09, right=0.99, bottom=0.18, top=0.88)
for ax, (label, values) in zip(axes, paths.items()):
    x = np.arange(len(values))
    colors = ["#0F766E" if v <= start_limit else "#E76F51" for v in values]
    ax.bar(x, values, width=0.78, color=colors, edgecolor="white", linewidth=0.7)
    ax.axhline(start_limit, color="#0F766E", linestyle="--", linewidth=1.1,
               label="start limit 11.1 m/s")
    ax.axhline(continuation_limit, color="#E76F51", linestyle=":", linewidth=1.2,
               label="continuation limit 20 m/s")
    ax.set_ylim(-3.3, 28); ax.set_yticks([0, 10, 20]); ax.set_ylabel("gust (m/s)")
    ax.set_title(label, loc="left", fontsize=11, pad=6)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.7)
    valid = [values[t] <= start_limit and all(v <= continuation_limit for v in values[t+1:t+duration])
             for t in range(len(values)-duration+1)]
    for t, ok in enumerate(valid):
        ax.add_patch(plt.Rectangle((t-0.34, -2.4), 0.68, 1.35,
                                   facecolor="#0F766E" if ok else "#CBD5E1",
                                   edgecolor="none"))
    ax.text(1, 1.04, f"Admissible starts: {sum(valid)}", ha="right", va="bottom",
            transform=ax.transAxes, fontsize=9, color="#334155")
axes[-1].set_xticks(np.arange(8), [f"t={i}" for i in range(8)])
axes[-1].set_xlabel("candidate start slot", labelpad=7)
fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center",
           bbox_to_anchor=(0.55, 0.99), frameon=False, ncol=2, fontsize=9)
fig.text(0.09, 0.025, "Constructed paths. Start markers: green = admissible; gray = inadmissible.",
         ha="left", fontsize=8.5, color="#475569")
fig.savefig(OUT / "svg" / "fig2_window_counterexample.svg", bbox_inches="tight")
fig.savefig(OUT / "pdf" / "fig2_window_counterexample.pdf", bbox_inches="tight")
fig.savefig(OUT / "png" / "fig2_window_counterexample.png", dpi=220, bbox_inches="tight")
plt.close(fig)
print("wrote fig2 outputs")
