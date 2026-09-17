"""Collect additional GFS fields so the window event can be made multi-hazard.

The wind analysis uses one forecast field (surface gust). A crane lift, however,
is also stopped by rain, and a concrete or epoxy operation is stopped by
temperature; a joint window therefore needs more than the gust. This collector
adds, for the same runs, two more bounded messages per lead:

* ``TMP:2 m above ground``  - air temperature at 2 m,
* ``APCP:surface``          - the 6-hour accumulated precipitation ending at the
  valid time (the ``(L-6)-L hour acc fcst`` entry of that lead).

Only the indexed byte range of each message is transferred, every message is
validated before decoding, and per-message SHA-256 plus byte ranges are written
to a manifest so each row can be re-fetched and byte-verified.
"""
from __future__ import annotations

import argparse
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import csv

from download_inputs import fetch, save
from collect_gfs_gust_archive import decode_gust

BUCKET = "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
LOCK = threading.Lock()

# field key -> (index line matcher, canonical description, expected unit set)
FIELDS = {
    "TMP2m": (lambda line: ":TMP:2 m above ground:" in line,
              "2 m air temperature", ("[K]", "K")),
    "APCP6h": (None, "6 h accumulated precipitation ending at the valid time", ("[kg/m^2]", "kg/m^2", "[mm]", "mm")),
}


def index_url(day: date, cycle: str, lead: int) -> str:
    stamp = day.strftime("%Y%m%d")
    return (f"{BUCKET}/gfs.{stamp}/{cycle}/atmos/"
            f"gfs.t{cycle}z.pgrb2.0p25.f{lead:03d}.idx")


def grib_url(day: date, cycle: str, lead: int) -> str:
    stamp = day.strftime("%Y%m%d")
    return f"{BUCKET}/gfs.{stamp}/{cycle}/atmos/gfs.t{cycle}z.pgrb2.0p25.f{lead:03d}"


def pick_range(lines: list[str], field: str, lead: int) -> tuple[int, int, str]:
    if field == "APCP6h":
        lo_label = 0 if lead == 6 else lead - 6
        needle = f":APCP:surface:{lo_label}-{lead} hour acc fcst:"
    else:
        needle = ":TMP:2 m above ground:"
    for i, line in enumerate(lines):
        if needle in line:
            start = int(line.split(":")[1])
            end = int(lines[i + 1].split(":")[1]) - 1 if i + 1 < len(lines) else None
            if end is None:
                raise ValueError(f"{field} is the last index entry at lead {lead}")
            return start, end, line
    raise ValueError(f"{field} not found in index at lead {lead}")


def decode_field(raw: bytes, field: str, stations: list[dict]) -> tuple[dict, list[dict]]:
    import rasterio

    if raw[:4] != b"GRIB" or raw[7] != 2 or raw[-4:] != b"7777":
        raise ValueError("not one complete GRIB2 message")
    if int.from_bytes(raw[8:16], "big") != len(raw):
        raise ValueError("GRIB2 declared length does not match received bytes")
    scratch = Path(__file__).resolve().parent / "_grib_scratch_mh"
    scratch.mkdir(exist_ok=True)
    tmp = scratch / f"mh_{threading.get_ident()}_{datetime.now().timestamp():.0f}.grib2"
    tmp.write_bytes(raw)
    try:
        with rasterio.open(tmp) as ds:
            tags = ds.tags(1)
            element = (tags.get("GRIB_ELEMENT") or "").strip()
            unit = (tags.get("GRIB_UNIT") or "").strip()
            # rasterio reports the accumulated product as e.g. "APCP06"; the unit of 2 m
            # temperature is reported as [C] on current pgrb2 files, so both are accepted
            # and the decoded unit is recorded verbatim rather than assumed.
            expect_prefix = "TMP" if field == "TMP2m" else "APCP"
            if not element.startswith(expect_prefix):
                raise ValueError(f"decoded {element}, expected {expect_prefix}*")
            allowed_units = {"TMP2m": ("[K]", "K", "[C]", "C"),
                             "APCP6h": ("[kg/m^2]", "[kg/(m^2)]", "kg/m^2", "kg m-2",
                                         "[mm]", "mm")}
            if unit not in allowed_units[field]:
                raise ValueError(f"unexpected unit {unit} for {field}")
            rows = []
            for station in stations:
                lon, lat = station["longitude"], station["latitude"]
                value = float(next(ds.sample([(lon, lat)]))[0])
                rows.append({"station_id": station["station_id"], "value": value,
                             "unit": unit, "grid_longitude": station.get("grid_longitude"),
                             "grid_latitude": station.get("grid_latitude")})
            meta = {"grib_element": element, "grib_unit": unit,
                    "grib_valid_unix": tags.get("GRIB_VALID_TIME"),
                    "grib_ref_unix": tags.get("GRIB_REF_TIME")}
    finally:
        tmp.unlink(missing_ok=True)
    return meta, rows


def process(day: date, cycle: str, lead: int, field: str, stations: list[dict]) -> dict:
    idx_raw, idx_meta = fetch(index_url(day, cycle, lead))
    lines = idx_raw.decode("utf-8").splitlines()
    lo, hi, entry = pick_range(lines, field, lead)
    raw, meta = fetch(grib_url(day, cycle, lead), headers={"Range": f"bytes={lo}-{hi}"},
                      require_partial=True)
    cr = next((v for k, v in meta["headers"].items() if k.lower() == "content-range"), "")
    if not cr.startswith(f"bytes {lo}-{hi}/") or len(raw) != hi - lo + 1:
        raise ValueError("server range or byte count differs from the requested message")
    gmeta, rows = decode_field(raw, field, stations)
    valid = datetime.fromtimestamp(int(gmeta["grib_valid_unix"]), tz=timezone.utc)
    return {
        "field": field, "issue_date": day.isoformat(), "issue_cycle": cycle,
        "lead_hours": lead, "valid_time": valid.isoformat(),
        "index_entry": entry, "index_sha256": idx_meta["sha256"],
        "message_sha256": meta["sha256"], "byte_start": lo, "byte_end": hi,
        "grib_element": gmeta["grib_element"], "grib_unit": gmeta["grib_unit"],
        "stations": rows, "record_type": "operational_archive_vintage",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--start", default="2021-06-01")
    parser.add_argument("--end", default="2025-09-30")
    parser.add_argument("--cycles", default="00")
    parser.add_argument("--leads", default="24")
    parser.add_argument("--fields", default="TMP2m,APCP6h")
    parser.add_argument("--stations-file", type=Path,
                        default=Path(__file__).resolve().parents[1] / "configs" / "knmi_stations.json")
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args()

    stations = json.loads(args.stations_file.read_text(encoding="utf-8"))["stations"]
    cycles = [c.zfill(2) for c in args.cycles.split(",") if re.fullmatch(r"0|00|6|06|12|18", c.strip())]
    leads = [int(x) for x in args.leads.split(",")]
    fields = [f for f in args.fields.split(",") if f in FIELDS]
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)

    out_dir = args.root / "outputs"
    data_dir = args.root / "data" / "raw" / "gfs_multihazard"
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "gfs_multihazard_manifest.jsonl"
    failures = out_dir / "gfs_multihazard_failures.jsonl"

    done: set[tuple[str, str, int, str]] = set()
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["issue_date"], r["issue_cycle"], r["lead_hours"], r["field"]))
    print(f"resume: {len(done)} messages already verified", flush=True)

    tasks = []
    day = start
    while day <= end:
        for cycle in cycles:
            for lead in leads:
                for field in fields:
                    if (day.isoformat(), cycle, lead, field) not in done:
                        tasks.append((day, cycle, lead, field))
        day += timedelta(days=1)
    print(f"messages pending: {len(tasks)}", flush=True)

    ok = bad = 0
    rows_by_station: dict[str, int] = {}
    with manifest.open("a", encoding="utf-8") as mf, failures.open("a", encoding="utf-8") as ff:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(process, d, c, l, f, stations): (d, c, l, f)
                       for d, c, l, f in tasks}
            for n, future in enumerate(as_completed(futures), 1):
                d, c, l, f = futures[future]
                try:
                    rec = future.result()
                except Exception as exc:  # noqa: BLE001 - provenance over silence
                    bad += 1
                    ff.write(json.dumps({"issue_date": d.isoformat(), "issue_cycle": c,
                                         "lead_hours": l, "field": f, "error": repr(exc)[:200],
                                         "recorded_at": datetime.now(timezone.utc).isoformat()}) + "\n")
                else:
                    mf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    ok += 1
                    for row in rec["stations"]:
                        key = f"{row['station_id']}_{f}"
                        rows_by_station[key] = rows_by_station.get(key, 0) + 1
                if n % 200 == 0 or n == len(tasks):
                    mf.flush(); ff.flush()
                    print(f"  [{n}/{len(tasks)}] ok={ok} failed={bad}", flush=True)

    summary = {"created_at": datetime.now(timezone.utc).isoformat(),
               "fields": fields, "cycles": cycles, "leads": leads,
               "start": args.start, "end": args.end,
               "messages_verified": ok, "failures": bad,
               "rows_per_station_field": rows_by_station}
    (out_dir / "gfs_multihazard_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"messages_verified": ok, "failures": bad}, ensure_ascii=False))


if __name__ == "__main__":
    main()
