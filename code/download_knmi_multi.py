"""Download KNMI hourly observations for the full serving station list.

Variables: FH (hourly mean wind), FX (preceding-hour maximum gust), T (air
temperature at 1.5 m), R (preceding-hour precipitation *occurrence*, a 0/1
flag).  R is not an amount: the amount is RH (0.1 mm, -1 = trace) and the
duration is DR (0.1 h), neither of which is requested here.  An earlier version
of this module treated R as tenths of a millimetre, which is not a valid
reading of the field.

Station IDs come from outputs/gates/G3_knmi_station_catalog.json, which was built
by probing the official endpoint one ID at a time; a station is requested here
only because the endpoint served it.
"""
from __future__ import annotations

import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from download_inputs import fetch, parse_knmi, restrict_knmi_rows, save

BASE = "https://www.daggegevens.knmi.nl/klimatologie/uurgegevens"
VARS = "FH:FX:T:R"


def chunk(station: str, year: int, root: Path, *, late_end: bool = False,
          suffix: str = "") -> dict:
    start = f"{year}060101" if year == 2021 else f"{year}010101"
    if year == 2025 and not late_end:
        end = f"{year}092124"
    else:
        end = f"{year}123124"
    params = {"stns": station, "start": start, "end": end, "vars": VARS}
    dest = root / "data" / "raw" / "knmi_multi" / f"{station}_{year}{suffix}.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.with_suffix(".txt.metadata.json").exists():
        raw = dest.read_bytes()
        meta = json.loads(dest.with_suffix(".txt.metadata.json").read_text(encoding="utf-8"))
    else:
        raw, meta = fetch(BASE + "?" + urlencode(params))
    text = raw.decode("utf-8-sig")
    parsed = parse_knmi(text)
    rows = restrict_knmi_rows(parsed, start, end, station)
    meta.update(request_parameters=params, response_rows=len(parsed), retained_rows=len(rows),
                source_type="station_observation",
                availability_status="historical archive; observation reporting latency not established")
    save(raw, meta, dest)
    with dest.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return {"station": station, "year": year, "rows": len(rows),
            "fx_missing": sum(1 for r in rows if r["FX_ms"] is None),
            "t_missing": sum(1 for r in rows if r.get("T_ms") is None),
            "r_missing": sum(1 for r in rows if r.get("R_occurrence") is None),
            "sha256": meta["sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--years", default="2021,2022,2023,2024,2025")
    parser.add_argument("--late-end", action="store_true",
                        help="for 2025, request through 31 December instead of 21 September; "
                             "used to extend the record past the original study window")
    parser.add_argument("--suffix", default="",
                        help="suffix for the output files, so an extended pull does not "
                             "overwrite the frozen study files")
    args = parser.parse_args()

    catalog = json.loads((args.root / "outputs" / "gates" / "G3_knmi_station_catalog.json")
                         .read_text(encoding="utf-8"))
    stations = [s["station_id"] for s in catalog["serving"]]
    years = [int(y) for y in args.years.split(",")]
    print(f"stations: {len(stations)}; years: {years}; chunks: {len(stations) * len(years)}", flush=True)

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(chunk, s, y, args.root, late_end=args.late_end,
                               suffix=args.suffix): (s, y)
                   for s in stations for y in years}
        for n, future in enumerate(as_completed(futures), 1):
            try:
                results.append({"status": "OK", **future.result()})
            except Exception as exc:  # noqa: BLE001 - per-chunk provenance
                results.append({"status": "FAILED", "station_year": futures[future],
                                "error": repr(exc)[:160]})
            if n % 40 == 0 or n == len(futures):
                ok = sum(1 for r in results if r["status"] == "OK")
                print(f"  [{n}/{len(futures)}] ok={ok}", flush=True)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "variables": VARS,
        "stations": stations, "years": years,
        "chunks_ok": sum(1 for r in results if r["status"] == "OK"),
        "chunks_failed": sum(1 for r in results if r["status"] != "OK"),
        "total_rows": sum(r.get("rows", 0) for r in results if r["status"] == "OK"),
        "results": results,
    }
    out = args.root / "outputs" / "knmi_multi_coverage.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("chunks_ok", "chunks_failed", "total_rows")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
