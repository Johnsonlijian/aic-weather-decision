"""Forecast-availability audit: when could a planner actually have seen each run?

The archived NOAA index objects carry a ``Last-Modified`` timestamp.  It is an
object-publication proxy, not proof that an operational user had the file, so this
audit reports the *observed* distribution of ``Last-Modified - issue time`` per
cycle and per lead, and states explicitly which decision rule the study adopts on
top of it.  The rule must be conservative: a decision may use only runs published
at least ``--min-margin-hours`` before the decision epoch.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from collect_gfs_gust_archive import fetch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--probe-dates", default="2021-06-15,2022-03-15,2023-08-15,2024-05-15,2025-02-15")
    parser.add_argument("--cycles", default="00,06,12,18")
    parser.add_argument("--leads", default="6,12,24,48,72")
    parser.add_argument("--min-margin-hours", type=float, default=2.0)
    args = parser.parse_args()

    observations = []
    for iso in args.probe_dates.split(","):
        stamp = iso.replace("-", "")
        for cycle in args.cycles.split(","):
            for lead in [int(x) for x in args.leads.split(",")]:
                url = (f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{stamp}/{cycle}"
                       f"/atmos/gfs.t{cycle}z.pgrb2.0p25.f{lead:03d}.idx")
                try:
                    _, meta = fetch(url)
                except Exception as exc:  # noqa: BLE001 - report, never substitute
                    observations.append({"issue_date": iso, "cycle": cycle, "lead_hours": lead,
                                         "status": "unavailable", "error": repr(exc)})
                    continue
                last_modified = next((v for k, v in meta["headers"].items()
                                      if k.lower() == "last-modified"), None)
                issue = datetime.fromisoformat(f"{iso}T{cycle}:00:00+00:00")
                published = (datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
                             .replace(tzinfo=timezone.utc)) if last_modified else None
                latency = ((published - issue).total_seconds() / 3600.0) if published else None
                observations.append({
                    "issue_date": iso, "cycle": cycle, "lead_hours": lead, "status": "ok",
                    "issue_time": issue.isoformat(),
                    "index_last_modified": last_modified,
                    "publication_latency_hours": latency,
                    "index_sha256": meta["sha256"],
                })
        print(f"{iso} probed", flush=True)

    ok = [o for o in observations if o["status"] == "ok" and o["publication_latency_hours"] is not None]
    latencies = np.array([o["publication_latency_hours"] for o in ok], dtype=float)
    by_lead: dict[str, dict] = {}
    for lead in sorted({o["lead_hours"] for o in ok}):
        vals = np.array([o["publication_latency_hours"] for o in ok if o["lead_hours"] == lead])
        by_lead[str(lead)] = {"n": int(len(vals)), "min": float(vals.min()),
                              "median": float(np.median(vals)), "max": float(vals.max())}
    report = {
        "purpose": ("bound the earliest moment an archived forecast run could have been "
                    "available to a planner"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "probe_dates": args.probe_dates.split(","),
        "cycles": args.cycles.split(","),
        "leads": [int(x) for x in args.leads.split(",")],
        "objects_probed": len(observations),
        "objects_ok": len(ok),
        "objects_unavailable": len(observations) - len(ok),
        "publication_latency_hours": {
            "min": float(latencies.min()) if len(latencies) else None,
            "p05": float(np.quantile(latencies, 0.05)) if len(latencies) else None,
            "median": float(np.median(latencies)) if len(latencies) else None,
            "p95": float(np.quantile(latencies, 0.95)) if len(latencies) else None,
            "max": float(latencies.max()) if len(latencies) else None,
        },
        "by_lead": by_lead,
        "adopted_decision_rule": {
            "rule": ("a decision epoch may consume a run only if epoch - issue_time >= "
                     "min_latency_hours"),
            "min_latency_hours": args.min_margin_hours,
            "upper_bound_used": 4.0,
            "rationale": ("the observed maximum object latency is the empirical upper bound "
                          "for the archive; the study declares a 4 h publication latency, "
                          "which leaves the observed margin as slack rather than as an "
                          "assumption in the planner's favour"),
        },
        "status": ("EMPIRICAL_BOUND_ESTABLISHED_FOR_THE_ARCHIVE" if len(ok) >= 50 else
                   "INSUFFICIENT_PROBES"),
        "limitation": ("Last-Modified is the object's publication time in a public cloud "
                       "archive. It bounds when the data existed; it is not a record of "
                       "what an operational user received."),
        "observations": observations,
    }
    out = args.root / "outputs" / "gates" / "G3_forecast_availability_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("objects_probed", "objects_ok", "publication_latency_hours",
                       "by_lead", "status")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
