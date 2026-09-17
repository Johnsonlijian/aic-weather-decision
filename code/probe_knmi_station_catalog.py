"""Probe KNMI hourly station IDs one at a time to build the real station list.

The hourly endpoint answers HTTP 500 when the requested station list contains an
ID it does not serve, so batches cannot be used for discovery. Each candidate ID
is requested alone with a short window and no retry; an ID enters the pool only
if the endpoint returned parsed rows for it.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from download_inputs import parse_knmi

BASE = "https://www.daggegevens.knmi.nl/klimatologie/uurgegevens"


def probe_one(station: str, start: str, end: str, timeout: int = 25) -> dict:
    params = {"stns": station, "start": start, "end": end, "vars": "FH:FX:T:R"}
    url = BASE + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AcademicResearchInputClient/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        rows = parse_knmi(raw.decode("utf-8-sig"))
        return {"station_id": station, "status": "OK", "rows": len(rows),
                "fx_missing": sum(1 for r in rows if r["FX_ms"] is None),
                "t_missing": sum(1 for r in rows if r.get("T_ms") is None)}
    except Exception as exc:  # noqa: BLE001 - one probe per ID, failures are data
        return {"station_id": station, "status": "FAIL", "error": repr(exc)[:120]}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    start, end = "2024060101", "2024060724"
    ids = [str(i) for i in range(200, 400)]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(probe_one, s, start, end): s for s in ids}
        for n, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if n % 40 == 0:
                good = sum(1 for r in results if r["status"] == "OK")
                print(f"  probed {n}/200; serving {good}", flush=True)

    ok = sorted((r for r in results if r["status"] == "OK"), key=lambda r: int(r["station_id"]))
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "probe_window": {"start": start, "end": end},
        "requested_variables": "FH:FX:T:R",
        "candidate_ids": [int(x) for x in ids],
        "serving": [{"station_id": r["station_id"], "rows": r["rows"],
                     "fx_missing": r["fx_missing"], "t_missing": r["t_missing"]} for r in ok],
        "not_serving": [r["station_id"] for r in results if r["status"] != "OK"],
        "serving_count": len(ok),
        "method_note": ("Each ID was requested alone and without retry; an ID is listed as "
                        "serving only because the official endpoint returned parsed rows."),
    }
    out = root / "outputs" / "gates" / "G3_knmi_station_catalog.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"serving stations: {len(ok)}: {[r['station_id'] for r in ok]}")


if __name__ == "__main__":
    main()
