"""Scaled, resumable GFS GUST archive sampler for the weather-sensitive operation study.

Design constraints that make this scientifically usable rather than a convenience dump:

* Only the bounded ``:GUST:surface:`` GRIB2 message is transferred.  The full
  GRIB2 file (hundreds of megabytes) is never downloaded.
* One NOAA index file is fetched per (date, cycle, lead) because the byte offset
  of the surface GUST message depends on the size of all earlier messages in
  that same lead file.  Observed cost: ~40 kB index + ~0.6 MB message.
* ``Last-Modified`` of each index object is retained as an object-publication
  proxy.  It is used only to bound archive availability; the operational
  availability rule remains a separate, declared decision (see
  ``outputs/gates/G3_forecast_availability_contract.*``).
* Resumability is a manifest, not a hope: a (date, cycle, lead, variable) key is
  written to the manifest only after the decoded grid bytes were verified
  (GRIB2 edition 2, declared length == received length, single surface GUST,
  unit m/s).  Re-running skips completed keys.
* Raw GRIB2 messages are not archived by default (they are ~0.6 MB each and the
  source is a public permanent archive).  The manifest stores the exact byte
  range plus the SHA-256 of every message so that any row can be independently
  re-fetched and byte-verified.  ``--keep-grib`` stores them instead.

Outputs (append-and-resume, never overwrite):
    data/raw/gfs_gust/<station>_<year>_gust.csv        decoded station rows
    outputs/gfs_gust_manifest.jsonl                    per-message provenance
    outputs/gfs_gust_failures.jsonl                    per-message failures
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from download_inputs import fetch, save

BUCKET = "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
GRIB_URL_TMPL = BUCKET + "/gfs.{stamp}/{cycle}/atmos/gfs.t{cycle}z.pgrb2.0p25.f{lead:03d}"

CYCLES = ("00", "06", "12", "18")
LEADS = tuple(range(6, 73, 6))

LOCK = threading.Lock()
DECODE_LOCK = threading.Lock()
SCRATCH_COUNTER = itertools.count()


def gust_byte_range(index_text: str) -> tuple[int, int, str]:
    """Return (start_byte, end_byte, index_entry) for the surface GUST message."""
    lines = index_text.splitlines()
    hits: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        if ":GUST:surface:" not in line:
            continue
        start = int(line.split(":")[1])
        end = int(lines[i + 1].split(":")[1]) - 1 if i + 1 < len(lines) else None
        if end is None:
            raise ValueError("surface GUST is the last index entry; bounded range unknown")
        hits.append((start, end, line))
    if len(hits) != 1:
        raise ValueError(f"expected exactly one bounded surface GUST entry, found {len(hits)}")
    return hits[0]


def decode_gust(raw: bytes, stations: list[dict]) -> tuple[dict, list[dict]]:
    """Decode one bounded GRIB2 GUST message and sample the station grid cells.

    GDAL can open a GRIB2 message from an in-memory buffer only through a
    dataset name, so a short-lived scratch file is used.  The scratch name is
    unique per call (thread-safe) and removed in ``finally``.
    """
    import rasterio

    if raw[:4] != b"GRIB" or raw[7] != 2 or raw[-4:] != b"7777":
        raise ValueError("not one complete GRIB2 message")
    if int.from_bytes(raw[8:16], "big") != len(raw):
        raise ValueError("GRIB2 declared length does not match received bytes")

    scratch_dir = Path(__file__).resolve().parent / "_grib_scratch"
    scratch_dir.mkdir(exist_ok=True)
    tmp = scratch_dir / f"msg_{next(SCRATCH_COUNTER):08d}_{threading.get_ident()}.grib2"
    tmp.write_bytes(raw)
    try:
        with rasterio.open(tmp) as ds:
            tags = ds.tags(1)
            if ds.count != 1 or tags.get("GRIB_ELEMENT") != "GUST":
                raise ValueError("decoded message is not single surface GUST")
            if tags.get("GRIB_UNIT") not in ("[m/s]", "m/s"):
                raise ValueError("unexpected GUST unit")
            rows = []
            for station in stations:
                lon, lat = station["longitude"], station["latitude"]
                rr, cc = ds.index(lon, lat)
                if not (0 <= rr < ds.height and 0 <= cc < ds.width):
                    raise ValueError("station outside decoded grid")
                gx, gy = ds.xy(rr, cc)
                value = float(next(ds.sample([(lon, lat)]))[0])
                rows.append({
                    "station_id": station["station_id"],
                    "latitude": lat,
                    "longitude": lon,
                    "grid_longitude": round(gx, 4),
                    "grid_latitude": round(gy, 4),
                    "GUST_ms": value,
                })
            meta = {
                "grib_ref_unix": tags.get("GRIB_REF_TIME"),
                "grib_valid_unix": tags.get("GRIB_VALID_TIME"),
                "grib_forecast_seconds": tags.get("GRIB_FORECAST_SECONDS"),
                "grid_shape": [ds.height, ds.width],
                "crs": str(ds.crs),
                "decoder": f"rasterio/{rasterio.__version__}",
            }
    finally:
        tmp.unlink(missing_ok=True)
    return meta, rows


def process_lead(day: date, cycle: str, lead: int, stations: list[dict],
                 keep_grib: bool, grib_dir: Path) -> dict:
    """Fetch and verify the bounded surface-GUST message for one lead.

    The index of each lead file is required specifically: the byte offset of the
    surface GUST message depends on the total size of all earlier messages in
    that same file, so an offset taken from ``f006`` is invalid for ``f012``.
    """
    stamp = day.strftime("%Y%m%d")
    idx_url = (f"{BUCKET}/gfs.{stamp}/{cycle}/atmos/"
               f"gfs.t{cycle}z.pgrb2.0p25.f{lead:03d}.idx")
    idx_raw, idx_meta = fetch(idx_url)
    lo, hi, entry = gust_byte_range(idx_raw.decode("utf-8"))
    last_modified = next((v for k, v in idx_meta["headers"].items()
                          if k.lower() == "last-modified"), None)
    grib_url = GRIB_URL_TMPL.format(stamp=stamp, cycle=cycle, lead=lead)
    raw, meta = fetch(grib_url, headers={"Range": f"bytes={lo}-{hi}"},
                      require_partial=True)
    content_range = next((v for k, v in meta["headers"].items()
                          if k.lower() == "content-range"), "")
    if not content_range.startswith(f"bytes {lo}-{hi}/") or len(raw) != hi - lo + 1:
        raise ValueError("server range or byte count differs from requested message")
    gmeta, rows = decode_gust(raw, stations)
    valid = datetime.fromtimestamp(int(gmeta["grib_valid_unix"]), tz=timezone.utc)
    ref = datetime.fromtimestamp(int(gmeta["grib_ref_unix"]), tz=timezone.utc)
    declared_lead = float(gmeta["grib_forecast_seconds"]) / 3600.0
    if abs(declared_lead - lead) > 1e-9:
        raise ValueError(f"decoded lead {declared_lead} differs from requested {lead}")
    if keep_grib:
        grib_dir.mkdir(parents=True, exist_ok=True)
        save(raw, meta, grib_dir / f"gfs_{stamp}_{cycle}_f{lead:03d}_gust.grib2")
    return {
        "issue_date": day.isoformat(),
        "issue_cycle": cycle,
        "issue_time": ref.isoformat(),
        "lead_hours": lead,
        "valid_time": valid.isoformat(),
        "index_last_modified": last_modified,
        "index_sha256": idx_meta["sha256"],
        "message_sha256": meta["sha256"],
        "byte_start": lo,
        "byte_end": hi,
        "index_entry": entry,
        "grib_url": grib_url,
        "index_url": idx_url,
        "stations": rows,
        "record_type": "operational_archive_vintage",
    }


def process_one(day: date, cycle: str, leads: list[int], stations: list[dict],
                keep_grib: bool, grib_dir: Path) -> dict:
    """Process every requested lead of one run; a failed lead never hides the rest."""
    results, errors = [], []
    for lead in leads:
        try:
            results.append(process_lead(day, cycle, lead, stations, keep_grib, grib_dir))
        except Exception as exc:  # noqa: BLE001 - per-lead provenance is the point
            errors.append({"issue_date": day.isoformat(), "issue_cycle": cycle,
                           "lead_hours": lead, "error": repr(exc)})
    return {"stamp": day.strftime("%Y%m%d"), "cycle": cycle,
            "leads": results, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2025-09-30")
    parser.add_argument("--cycles", default="00,12")
    parser.add_argument("--leads", default="6,12,18,24,36,48,60,72")
    parser.add_argument("--stations-file", type=Path,
                        default=Path(__file__).resolve().parents[1] / "configs" / "knmi_stations.json")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--keep-grib", action="store_true")
    parser.add_argument("--tag", default="", help="suffix for manifest and data dir, for a re-collection with a different station set")
    parser.add_argument("--limit-runs", type=int, default=0,
                        help="debug: process at most N (date, cycle) pairs")
    args = parser.parse_args()

    stations = json.loads(args.stations_file.read_text(encoding="utf-8"))["stations"]
    cycles = [c.zfill(2) for c in args.cycles.split(",") if re.fullmatch(r"0|00|6|06|12|18", c.strip())]
    leads = [int(x) for x in args.leads.split(",") if x.isdigit() and 0 < int(x) <= 384]
    if not cycles or not leads:
        raise SystemExit("no valid cycles or leads")
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if end < start:
        raise SystemExit("end precedes start")

    out_dir = args.root / "outputs"
    suffix = f"_{args.tag}" if args.tag else ""
    data_dir = args.root / "data" / "raw" / f"gfs_gust{suffix}"
    grib_dir = args.root / "data" / "raw" / "gfs_gust_grib"
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / f"gfs_gust_manifest{suffix}.jsonl"
    failure_path = out_dir / f"gfs_gust_failures{suffix}.jsonl"

    done: set[tuple[str, str, int]] = set()
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            done.add((rec["issue_date"], rec["issue_cycle"], rec["lead_hours"]))
    print(f"resume: {len(done)} (date, cycle, lead) messages already verified", flush=True)

    runs: list[tuple[date, str]] = []
    day = start
    while day <= end:
        for cycle in cycles:
            runs.append((day, cycle))
        day += timedelta(days=1)
    # Work is scheduled per (date, cycle, lead) rather than per run so that one
    # slow lead cannot block the other leads of the same cycle.  Head-of-line
    # blocking across runs was the dominant throughput limit in the first version.
    pending: list[tuple[date, str, int]] = [
        (d, c, lead) for d, c in runs for lead in leads
        if (d.isoformat(), c, lead) not in done]
    if args.limit_runs:
        pending = pending[: args.limit_runs * len(leads)]
    print(f"leads pending: {len(pending)} across {len(runs)} runs", flush=True)

    # Per-station-year writers, opened once and flushed as rows arrive.
    handles: dict[tuple[str, int], object] = {}
    counters: dict[tuple[str, int], int] = {}

    HEADER = ["station_id", "valid_time", "issue_time", "issue_date", "issue_cycle",
              "lead_hours", "GUST_ms", "grid_longitude", "grid_latitude",
              "message_sha256", "byte_start", "byte_end", "index_sha256",
              "index_last_modified"]

    def writer_for(station_id: str, year: int):
        key = (station_id, year)
        if key not in handles:
            path = data_dir / f"{station_id}_{year}_gust.csv"
            new = not path.exists()
            fh = path.open("a", newline="", encoding="utf-8")
            # csv.writer quotes fields containing the delimiter; the HTTP
            # Last-Modified value always does, and a naive join silently wrote one
            # extra column per row
            writer = csv.writer(fh, lineterminator="\n")
            if new:
                writer.writerow(HEADER)
            handles[key] = (fh, writer)
            counters[key] = 0
        return handles[key]

    def emit(rec: dict) -> int:
        year = int(rec["valid_time"][:4])
        written = 0
        with LOCK:
            for row in rec["stations"]:
                _fh, writer = writer_for(row["station_id"], year)
                writer.writerow([
                    row["station_id"], rec["valid_time"], rec["issue_time"], rec["issue_date"],
                    rec["issue_cycle"], rec["lead_hours"], row["GUST_ms"],
                    row["grid_longitude"], row["grid_latitude"], rec["message_sha256"],
                    rec["byte_start"], rec["byte_end"], rec["index_sha256"],
                    rec["index_last_modified"] or ""])
                counters[(row["station_id"], year)] += 1
                written += 1
        return written

    manifest_fh = manifest_path.open("a", encoding="utf-8")
    failure_fh = failure_path.open("a", encoding="utf-8")
    ok_messages = fail_messages = 0
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(process_lead, d, c, lead, stations,
                                   args.keep_grib, grib_dir): (d, c, lead)
                       for d, c, lead in pending}
            for done_count, future in enumerate(as_completed(futures), 1):
                day, cycle, lead = futures[future]
                try:
                    rec = future.result()
                except Exception as exc:  # noqa: BLE001 - per-lead provenance is the point
                    fail_messages += 1
                    failure_fh.write(json.dumps({
                        "issue_date": day.isoformat(), "issue_cycle": cycle,
                        "lead_hours": lead, "error": repr(exc),
                        "recorded_at": datetime.now(timezone.utc).isoformat()}) + "\n")
                else:
                    key = (rec["issue_date"], rec["issue_cycle"], rec["lead_hours"])
                    if key not in done:
                        emit(rec)
                        manifest_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        done.add(key)
                        ok_messages += 1
                if done_count % 250 == 0 or done_count == len(pending):
                    manifest_fh.flush()
                    failure_fh.flush()
                    for fh, _writer in handles.values():
                        fh.flush()
                    print(f"  [{done_count}/{len(pending)}] leads; ok={ok_messages} "
                          f"failed={fail_messages}", flush=True)
    finally:
        manifest_fh.close()
        failure_fh.close()
        for fh, _writer in handles.values():
            fh.close()

    summary = {
        "analysis_status": "ARCHIVE_SAMPLING_ONLY_NO_SKILL_OR_DECISION_RESULT",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "start": args.start, "end": args.end, "cycles": cycles, "leads": leads,
        "stations": stations,
        "messages_verified": ok_messages,
        "runs_failed": fail_messages,
        "rows_per_station_year": {f"{k[0]}_{k[1]}": v for k, v in sorted(counters.items())},
        "manifest": str(manifest_path.name),
        "note": ("GUST is an instantaneous surface gust forecast. KNMI FX is a "
                 "preceding-hour maximum. Pairing is by declared time endpoint only."),
    }
    (out_dir / f"gfs_gust_collection_summary{suffix}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in
                      ("messages_verified", "runs_failed", "rows_per_station_year")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
