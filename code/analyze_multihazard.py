"""WITHDRAWN multi-hazard joint window -- retained only as a defect record.

Status: the results this script produced are NOT valid and must not be cited.
Two independent defects were found in review:

1. Rain. In the KNMI hourly dataset `R` is a 0/1 *occurrence* flag, not an
   amount. Re-parsing the whole retained archive (`code/reparse_knmi_multi.py`)
   confirms it: across 945,685 reported hours `R` takes only the values 0
   (752,787) and 1 (192,898). The old `R/10` "millimetre total" could therefore
   never exceed 0.1 mm per hour, so the "dry window" label was meaningless and
   the reported rain-failure rate was an artefact.
2. Temperature. The 5-35 C range in the placing/jointing specifications is a
   *concrete mixture* temperature limit, not the 1.5 m air temperature that this
   archive reports. Equating them is not a defensible proxy.

The joint labels are no longer written by `code/build_epoch_table_multi.py`
(they require an explicit `--allow-joint-hazard` opt-in) and the section that
reported these numbers has been removed from the manuscript. This module now
refuses to run rather than regenerate withdrawn numbers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from calibration import BinnedCalibrator, brier_skill_score

WIND_LIMIT = 12.0
TEMP_RANGE = (5.0, 35.0)   # concrete placing window (GB 50666-2011, read directly)
SPLITS = {"FIT": ("2021-06-01", "2023-12-31"),
          "CAL": ("2024-01-01", "2024-12-31"),
          "TEST": ("2025-01-01", "2025-09-30")}


def load_features(root: Path) -> pd.DataFrame:
    """Join the archived 24 h-lead TMP/APCP messages onto the station observation blocks."""
    manifest = root / "outputs" / "gfs_multihazard_manifest.jsonl"
    if not manifest.exists():
        raise SystemExit("multi-hazard manifest not found; run collect_gfs_multihazard.py")
    recs = [json.loads(l) for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for rec in recs:
        valid = pd.Timestamp(rec["valid_time"])
        for st in rec["stations"]:
            rows.append({"field": rec["field"], "issue_time": pd.Timestamp(rec["issue_date"] + "T" + rec["issue_cycle"] + ":00:00Z"),
                         "valid_time": valid, "station_id": str(st["station_id"]),
                         "value": float(st["value"]), "unit": st["unit"]})
    fc = pd.DataFrame(rows)
    wide = fc.pivot_table(index=["station_id", "issue_time", "valid_time"],
                          columns="field", values="value", aggfunc="first").reset_index()
    units = fc.groupby("field")["unit"].first().to_dict()

    # the gust predictor comes from the multi-station gust collection for the same runs
    gust_frames = []
    for folder in ("gfs_gust_multi", "gfs_gust_multi00"):
        gust_frames += [pd.read_csv(p) for p in
                        sorted((root / "data" / "raw" / folder).glob("*_gust.csv"))]
    if not gust_frames:
        raise SystemExit("multi-station gust tables not found; run collect_gfs_gust_archive.py --tag multi")
    gust = pd.concat(gust_frames, ignore_index=True)
    gust["station_id"] = gust["station_id"].astype(str)
    gust["valid_time"] = pd.to_datetime(gust["valid_time"], utc=True)
    gust["issue_time"] = pd.to_datetime(gust["issue_time"], utc=True)
    gust = gust[(gust["lead_hours"] == 24) & (gust["issue_cycle"] == 0)]
    gust = (gust.drop_duplicates(["station_id", "issue_time", "valid_time"])
                .rename(columns={"GUST_ms": "GUST"})[["station_id", "issue_time",
                                                         "valid_time", "GUST"]])
    wide = wide.merge(gust, on=["station_id", "issue_time", "valid_time"], how="inner")
    units["GUST"] = "m/s"

    # observations: the 6 h block ending at valid_time
    obs_frames = [pd.read_csv(p) for p in sorted((root / "data" / "raw" / "knmi_multi").glob("*.csv"))]
    obs = pd.concat(obs_frames, ignore_index=True)
    obs["valid_time"] = pd.to_datetime(obs["interval_end"], utc=True)
    obs["station_id"] = obs["station_id"].astype(str)
    obs = obs[["station_id", "valid_time", "FX_ms", "T_degC", "R_mm"]].drop_duplicates(
        ["station_id", "valid_time"])

    # vectorised 6 h blocks: one rolling pass per station instead of a per-group filter
    obs = obs.sort_values(["station_id", "valid_time"])
    parts = []
    for station, g in obs.groupby("station_id", sort=False):
        g = g.set_index("valid_time").sort_index()
        full = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h", tz="UTC"))
        block = pd.DataFrame({
            "obs_max_gust": full["FX_ms"].rolling(6).max(),
            "obs_total_rain": full["R_mm"].rolling(6).sum(),
            "obs_min_temp": full["T_degC"].rolling(6).min(),
            "obs_max_temp": full["T_degC"].rolling(6).max(),
            "obs_n": full["FX_ms"].rolling(6).count(),
        })
        block["station_id"] = station
        block.index.name = "valid_time"
        parts.append(block.reset_index())
    blocks_df = pd.concat(parts, ignore_index=True)
    blocks_df = blocks_df[blocks_df["obs_n"] == 6].drop(columns=["obs_n"])
    wide = wide.merge(blocks_df, on=["station_id", "valid_time"], how="inner")
    block_df = wide.copy()
    if block_df.empty:
        raise SystemExit("no usable multi-hazard blocks were assembled")

    # temperature unit handling, recorded not assumed
    tmp_unit = units.get("TMP2m", "")
    if tmp_unit in ("[K]", "K"):
        block_df["TMP2m"] = block_df["TMP2m"] - 273.15
    block_df["tmp_unit_original"] = tmp_unit
    block_df["apcp_unit_original"] = units.get("APCP6h", "")

    block_df["wind_ok"] = block_df["obs_max_gust"] <= WIND_LIMIT
    block_df["dry_ok"] = block_df["obs_total_rain"] <= 0.0
    block_df["temp_ok"] = ((block_df["obs_min_temp"] >= TEMP_RANGE[0])
                           & (block_df["obs_max_temp"] <= TEMP_RANGE[1]))
    block_df["joint_ok"] = block_df["wind_ok"] & block_df["dry_ok"] & block_df["temp_ok"]
    block_df["event_joint"] = (~block_df["joint_ok"]).astype(int)
    block_df["event_wind"] = (~block_df["wind_ok"]).astype(int)
    block_df["split"] = "OTHER"
    for name, (lo, hi) in SPLITS.items():
        lo_ts, hi_ts = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1)
        block_df.loc[(block_df["valid_time"] >= lo_ts) & (block_df["valid_time"] < hi_ts), "split"] = name
    return block_df


def fit_eval(frame: pd.DataFrame, target: str, features: list[str]) -> dict:
    fit = frame[frame["split"] == "FIT"]
    test = frame[frame["split"] == "TEST"]
    if fit[target].sum() == 0 or test[target].sum() == 0:
        return {"not_estimable": True, "fit_positives": int(fit[target].sum()),
                "test_positives": int(test[target].sum())}
    x_fit = np.column_stack([fit[f].to_numpy(float) for f in features])
    x_test = np.column_stack([test[f].to_numpy(float) for f in features])
    y_fit = fit[target].to_numpy(float)
    y_test = test[target].to_numpy(float)
    if x_fit.shape[1] == 1:
        model = BinnedCalibrator().fit(x_fit[:, 0], y_fit)
        p = model.predict(x_test[:, 0])
    else:
        # multi-predictor: equal-count bins on the gust plus a logistic blend of the others
        from calibration import LogisticCalibrator
        base = BinnedCalibrator().fit(x_fit[:, 0], y_fit)
        logit = LogisticCalibrator().fit(x_fit[:, 0], y_fit)
        coef = np.zeros(x_fit.shape[1])
        for j in range(1, x_fit.shape[1]):
            m = LogisticCalibrator().fit(x_fit[:, j], y_fit)
            coef[j] = m.coef
        z = logit.intercept + logit.coef * x_test[:, 0] + sum(
            coef[j] * x_test[:, j] for j in range(1, x_test.shape[1]))
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        p = 0.5 * p + 0.5 * base.predict(x_test[:, 0])
    base_rate = np.full_like(y_test, y_fit.mean())
    out = {"n": int(len(y_test)), "positives": int(y_test.sum()),
           "brier": float(np.mean((p - y_test) ** 2)),
           "skill_vs_climatology": brier_skill_score(p, y_test, base_rate)}
    if features == ["TMP2m"]:
        pass
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--i-understand-this-is-withdrawn", action="store_true",
                        help="regenerate the withdrawn numbers for forensic comparison only")
    args = parser.parse_args()
    if not args.i_understand_this_is_withdrawn:
        raise SystemExit(
            "analyze_multihazard.py is WITHDRAWN: its rain labels used a 0/1 occurrence "
            "flag as a millimetre amount and its temperature window used a concrete "
            "mixture limit as an air temperature. Pass "
            "--i-understand-this-is-withdrawn only to reproduce the defect for comparison."
        )
    root: Path = args.root

    frame = load_features(root)
    frame.to_csv(root / "outputs" / "multihazard_blocks.csv", index=False)

    report = {
        "wind_limit": WIND_LIMIT, "temperature_range": TEMP_RANGE,
        "rows": int(len(frame)), "stations": int(frame["station_id"].nunique()),
        "units": {"tmp": frame["tmp_unit_original"].iloc[0],
                  "apcp": frame["apcp_unit_original"].iloc[0]},
        "event_rates": {
            "wind_event": float(frame["event_wind"].mean()),
            "rain_fails": float((~frame["dry_ok"]).mean()),
            "temp_fails": float((~frame["temp_ok"]).mean()),
            "joint_event": float(frame["event_joint"].mean()),
            "joint_ok": float(frame["joint_ok"].mean()),
        },
        "rows_per_split": {k: int(v) for k, v in frame.groupby("split").size().items()},
        "models": {},
    }
    # single-variable vs multi-variable on the same target
    report["models"]["gust_only"] = fit_eval(frame, "event_joint", ["GUST"])
    report["models"]["gust_tmp_apcp"] = fit_eval(frame, "event_joint",
                                                 ["GUST", "TMP2m", "APCP6h"])
    report["models"]["wind_event_gust_only"] = fit_eval(frame, "event_wind", ["GUST"])
    # does the gust alone explain the non-wind failures?
    report["models"]["temp_fail_from_tmp"] = fit_eval(
        frame.assign(event_temp=(~frame["temp_ok"]).astype(int)), "event_temp", ["TMP2m"])
    report["models"]["rain_fail_from_apcp"] = fit_eval(
        frame.assign(event_rain=(~frame["dry_ok"]).astype(int)), "event_rain", ["APCP6h"])

    out = root / "outputs" / "g5_multihazard_joint.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["event_rates"], ensure_ascii=False, indent=2))
    for k, v in report["models"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
