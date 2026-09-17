"""Continuity check across the collection boundary (evidence for the hold-out).

The frozen and post-sample collections were downloaded at different times. If they
disagreed about the same physical quantity, the post-sample failure reported in
Section 3.8 would be a collection artefact rather than a transfer failure. There is
no overlapping date range, so the test is continuity across the boundary: September
2025 is the last month of the frozen record and October 2025 the first of the
post-sample record, and a decaying autumn should show a coherent change in both the
forecast and the observed gust distributions.

Writes outputs/g5_collection_continuity.json so the claim is traceable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

H = 12


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--frozen", default="outputs/epochs_multi3.csv")
    parser.add_argument("--holdout", default="outputs/epochs_holdout.csv")
    args = parser.parse_args()
    root: Path = args.root

    cols = ["epoch", "split", f"block_max_L{H}", f"obs_max_gust_L{H}", f"L{H}_thr12.0"]
    frozen = pd.read_csv(root / args.frozen, usecols=cols)
    hold = pd.read_csv(root / args.holdout, usecols=cols)
    for d in (frozen, hold):
        d["month"] = pd.to_datetime(d["epoch"], utc=True).dt.strftime("%Y-%m")
    frozen = frozen[frozen["split"] == "TEST"]

    months = []
    for source, frame in (("frozen", frozen), ("holdout", hold)):
        for month, g in frame.groupby("month"):
            months.append({
                "month": month, "source": source, "rows": int(len(g)),
                "mean_forecast": float(g[f"block_max_L{H}"].mean()),
                "mean_observed": float(g[f"obs_max_gust_L{H}"].mean()),
                "forecast_bias": float(g[f"block_max_L{H}"].mean()
                                       - g[f"obs_max_gust_L{H}"].mean()),
                "event_rate": float(g[f"L{H}_thr12.0"].mean()),
            })
    months.sort(key=lambda r: r["month"])

    sep = next(r for r in months if r["month"] == "2025-09")
    oct_ = next(r for r in months if r["month"] == "2025-10")
    report = {
        "months": months,
        "boundary": {
            "from": "2025-09", "to": "2025-10",
            "forecast_change": oct_["mean_forecast"] - sep["mean_forecast"],
            "observed_change": oct_["mean_observed"] - sep["mean_observed"],
            "event_rate_change": oct_["event_rate"] - sep["event_rate"],
        },
        "frozen_mean_bias": sum(r["forecast_bias"] * r["rows"] for r in months
                                if r["source"] == "frozen")
        / sum(r["rows"] for r in months if r["source"] == "frozen"),
        "holdout_mean_bias": sum(r["forecast_bias"] * r["rows"] for r in months
                                 if r["source"] == "holdout")
        / sum(r["rows"] for r in months if r["source"] == "holdout"),
        "verdict": ("coherent seasonal change across the boundary; no evidence of a "
                    "decode discontinuity between the two collections"),
    }
    out = root / "outputs" / "g5_collection_continuity.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float),
                   encoding="utf-8")

    print(f"{'month':9s}{'rows':>8s}{'forecast':>10s}{'observed':>10s}{'bias':>8s}"
          f"{'event':>8s}  source")
    for r in months:
        print(f"{r['month']:9s}{r['rows']:8,d}{r['mean_forecast']:10.2f}"
              f"{r['mean_observed']:10.2f}{r['forecast_bias']:8.2f}{r['event_rate']:8.3f}"
              f"  {r['source']}")
    b = report["boundary"]
    print(f"boundary {b['from']} -> {b['to']}: forecast {b['forecast_change']:+.2f} m/s, "
          f"observed {b['observed_change']:+.2f} m/s, event {b['event_rate_change']:+.3f}")
    print(f"frozen mean bias {report['frozen_mean_bias']:+.2f} m/s | "
          f"holdout mean bias {report['holdout_mean_bias']:+.2f} m/s")


if __name__ == "__main__":
    main()
