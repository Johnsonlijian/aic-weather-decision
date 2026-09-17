"""Discover which KNMI hourly stations actually serve data for the study window.

The hourly endpoint is slow when many stations are requested at once, so this
probes in small batches with a short window and records, per station, how many
rows came back and which variables were populated. Nothing is inferred: a station
enters the candidate pool only if the endpoint returned rows for it.
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from download_inputs import fetch, parse_knmi

VARS = "FH:FX:T:R:DR:U"


def probe_batch(ids: list[str], start: str, end: str) -> dict:
    params = {"stns": ":".join(ids), "start": start, "end": end, "vars": VARS}
    url = ("https://www.daggegevens.knmi.nl/klimatologie/uurgegevens?"
           + urllib.parse.urlencode(params))
    try:
        raw, meta = fetch(url)
        rows = parse_knmi(raw.decode("utf-8-sig"))
    except Exception as exc:  # noqa: BLE001 - report per-batch, never substitute
        return {"batch": ids, "error": repr(exc)[:160], "stations": {}}
    out: dict[str, dict] = {}
    for row in rows:
        station = row["station_id"]
        entry = out.setdefault(station, {"rows": 0, "columns": sorted(row.keys())})
        entry["rows"] += 1
    return {"batch": ids, "error": None, "stations": out}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--start", default="2024060101")
    parser.add_argument("--end", default="2024060724")
    parser.add_argument("--first", type=int, default=200)
    parser.add_argument("--last", type=int, default=399)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    ids = [str(i) for i in range(args.first, args.last + 1)]
    batches = [ids[i:i + args.batch] for i in range(0, len(ids), args.batch)]
    results, stations = [], {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(probe_batch, b, args.start, args.end): b for b in batches}
        for done, future in enumerate(as_completed(futures), 1):
            res = future.result()
            results.append(res)
            for station, info in res["stations"].items():
                stations[station] = info
            if done % 5 == 0 or done == len(batches):
                print(f"  batches {done}/{len(batches)}; stations found {len(stations)}", flush=True)

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "window": {"start": args.start, "end": args.end},
        "requested_vars": VARS,
        "id_range": [args.first, args.last],
        "stations_found": {k: stations[k] for k in sorted(stations, key=int)},
        "station_count": len(stations),
        "batch_errors": [r for r in results if r["error"]],
        "note": ("A station is listed only because the official endpoint returned rows "
                 "for it in the probe window; no station is inferred from documentation."),
    }
    out = args.root / "outputs" / "gates" / "G3_knmi_station_discovery.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"stations with data: {len(stations)}")
    print(", ".join(sorted(stations, key=int)))
    if report["batch_errors"]:
        print(f"batch errors: {len(report['batch_errors'])}")


if __name__ == "__main__":
    main()
