"""Predeclared threshold calibration pilot for the aligned GFS/KNMI sample.

The split is fixed by valid time before fitting: 2025-01-01--16 train,
2025-01-17--23 validation, and 2025-01-24 through 2025-02-01 00Z test.
A one-feature logistic
calibrator is used only when the training partition contains both classes.
The output is explicitly a pilot because forecast publication latency is not
known and the sample covers one station, one lead, and one month.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

SPLITS = {
    "train": ("2025-01-01", "2025-01-17"),
    "validation": ("2025-01-17", "2025-01-24"),
    # The 2025-01-31 18Z issue has a valid endpoint at 2025-02-01 00Z;
    # retain that last requested issue in the test partition.
    "test": ("2025-01-24", "2025-02-02"),
}
THRESHOLDS = (11.1, 20.0)


def split_frame(df: pd.DataFrame, lo: str, hi: str) -> pd.DataFrame:
    return df[(df["valid_time"] >= lo) & (df["valid_time"] < hi)].copy()


def score_partition(model: LogisticRegression, frame: pd.DataFrame, threshold: float) -> dict:
    y = (frame["KNMI_FX_ms"].to_numpy() > threshold).astype(int)
    p = model.predict_proba(frame[["GUST_ms"]])[:, 1]
    # log_loss accepts a one-class evaluation set only when labels are supplied.
    return {
        "rows": len(frame),
        "positive_observations": int(y.sum()),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "mean_probability": float(p.mean()),
    }


def fit_threshold(df: pd.DataFrame, threshold: float) -> dict:
    counts = {}
    for name, (lo, hi) in SPLITS.items():
        part = split_frame(df, lo, hi)
        y = (part["KNMI_FX_ms"].to_numpy() > threshold).astype(int)
        counts[name] = {"rows": len(part), "positive_observations": int(y.sum())}
    train = split_frame(df, *SPLITS["train"])
    y_train = (train["KNMI_FX_ms"].to_numpy() > threshold).astype(int)
    if len(set(y_train)) < 2:
        return {
            "threshold_ms": threshold,
            "status": "NOT_ESTIMABLE_TRAINING_ONE_CLASS",
            "split_counts": counts,
            "model": "logistic_regression_on_GUST_ms",
        }
    model = LogisticRegression(solver="lbfgs", C=1.0, max_iter=1000)
    model.fit(train[["GUST_ms"]], y_train)
    return {
        "threshold_ms": threshold,
        "status": "PILOT_FIT_NO_OPERATIONAL_CLAIM",
        "split_counts": counts,
        "model": "logistic_regression_on_GUST_ms",
        "train_coefficient": float(model.coef_[0, 0]),
        "train_intercept": float(model.intercept_[0]),
        "scores": {
            name: score_partition(model, split_frame(df, *bounds), threshold)
            for name, bounds in SPLITS.items()
        },
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[1] / "outputs" / "gfs_knmi_pilot.csv")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()
    df = pd.read_csv(args.input, parse_dates=["valid_time"])
    if df.empty or df["KNMI_FX_ms"].isna().any():
        raise ValueError("calibration pilot requires non-empty, complete paired observations")
    result = {
        "analysis_status": "PILOT_ONLY_NO_OPERATIONAL_BACKTEST",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "input_bytes": args.input.stat().st_size,
        "rows": len(df),
        "station_id": sorted(df["station_id"].astype(str).unique().tolist()),
        "lead_hours": sorted(df["lead_hours"].unique().tolist()),
        "split_definition": SPLITS,
        "predeclared_model": "one-feature logistic regression using GUST_ms",
        "target_semantics": "KNMI FX preceding-hour maximum; GFS GUST instantaneous valid-time forecast",
        "event_relation": "strict exceedance: FX > threshold; equality is admissible in the window contract",
        "boundary_correction": "2026-09-15: aligned the event inequality with the operation contract; no pilot observation equals either threshold, so cohort labels and scores are unchanged",
        "results": [fit_threshold(df, threshold) for threshold in THRESHOLDS],
        "availability_status": "offline historical archive; GFS publication latency not established",
        "interpretation": "Scores are pilot diagnostics only; no forecast skill, calibrated probability, or scheduling-value claim is released.",
        "required_before_main_result": [
            "operational publication latency audit",
            "multiple leads and issue times",
            "predeclared model selection and hyperparameters",
            "frozen validation/test partitions held out from all choices",
            "cross-network scheduling experiment with common weather scenarios",
        ],
    }
    out = args.out or args.input.with_name("gfs_knmi_calibration_pilot.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "rows": len(df),
                      "statuses": [r["status"] for r in result["results"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
