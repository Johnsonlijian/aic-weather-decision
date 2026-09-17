"""Coordinate-sensitivity check for the GFS nearest-cell lookup.

The exact published coordinates of the KNMI stations could not be retrieved from
the provider's ftp/cdn endpoints during this study (the station-list file returns
HTTP 403 to programmatic clients).  Rather than leave an unverified constant in the
pipeline, this probe measures whether the result is sensitive to that uncertainty:

for every candidate coordinate set it reports the selected GFS 0.25-degree cell and
the decoded gust, over a spread of archived messages.  If all candidates select the
same cell, the station-coordinate question cannot change any result in the study.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from collect_gfs_gust_archive import decode_gust, fetch, gust_byte_range

CANDIDATES = {
    "240": [("current_pipeline", 52.30, 4.79), ("variant_a", 52.31, 4.77),
            ("variant_b", 52.29, 4.76), ("variant_c", 52.32, 4.80)],
    "260": [("current_pipeline", 52.10, 5.18), ("variant_a", 52.10, 5.18),
            ("variant_b", 52.06, 5.18), ("variant_c", 52.12, 5.15)],
    "344": [("current_pipeline", 51.89, 4.31), ("variant_a", 51.90, 4.31),
            ("variant_b", 51.96, 4.45), ("variant_c", 51.92, 4.48)],
}
PROBE_DATES = ("2022-01-15", "2023-07-15", "2024-11-15", "2025-03-15")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--lead", type=int, default=6)
    parser.add_argument("--cycle", default="00")
    args = parser.parse_args()

    observations = []
    for iso in PROBE_DATES:
        day = date.fromisoformat(iso)
        stamp = day.strftime("%Y%m%d")
        idx_url = (f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{stamp}/{args.cycle}"
                   f"/atmos/gfs.t{args.cycle}z.pgrb2.0p25.f{args.lead:03d}.idx")
        idx_raw, _ = fetch(idx_url)
        lo, hi, entry = gust_byte_range(idx_raw.decode("utf-8"))
        grib_url = idx_url[:-4]
        raw, _ = fetch(grib_url, headers={"Range": f"bytes={lo}-{hi}"}, require_partial=True)
        per_station = {}
        for station, variants in CANDIDATES.items():
            rows = []
            for label, lat, lon in variants:
                meta, decoded = decode_gust(raw, [{"station_id": station,
                                                   "latitude": lat, "longitude": lon}])
                rows.append({"variant": label, "latitude": lat, "longitude": lon,
                             "grid_longitude": decoded[0]["grid_longitude"],
                             "grid_latitude": decoded[0]["grid_latitude"],
                             "GUST_ms": decoded[0]["GUST_ms"]})
            cells = {(r["grid_longitude"], r["grid_latitude"]) for r in rows}
            values = {round(r["GUST_ms"], 6) for r in rows}
            per_station[station] = {
                "variants": rows,
                "distinct_cells": sorted(cells),
                "same_cell_for_all_variants": len(cells) == 1,
                "distinct_values": sorted(values),
                "value_spread_ms": max(values) - min(values),
            }
        observations.append({"issue_date": iso, "cycle": args.cycle, "lead_hours": args.lead,
                             "index_entry": entry, "stations": per_station})
        print(f"{iso} processed", flush=True)

    summary = {
        "purpose": ("measure whether the unresolved official station coordinates can "
                    "change any GFS sample used by the study"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "lead_hours": args.lead, "cycle": args.cycle,
        "probe_dates": list(PROBE_DATES),
        "per_station": {},
        "observations": observations,
    }
    for station in CANDIDATES:
        same = [o["stations"][station]["same_cell_for_all_variants"] for o in observations]
        spreads = [o["stations"][station]["value_spread_ms"] for o in observations]
        summary["per_station"][station] = {
            "all_probes_single_cell": bool(np.all(same)),
            "max_value_spread_ms": float(np.max(spreads)),
            "cells_seen": sorted({tuple(c) for o in observations
                                  for c in o["stations"][station]["distinct_cells"]}),
        }
    out = args.root / "outputs" / "gates" / "G3_station_coordinate_sensitivity.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary["per_station"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
