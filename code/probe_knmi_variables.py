"""Probe which KNMI hourly variables the study region actually provides.

The operation contract needs more than FX/FH (precipitation, temperature,
radiation, visibility).  This probe requests one station-year with an explicit
variable list, records the returned column header verbatim, and reports the
per-variable availability plus basic exceedance counts.  It never substitutes
a missing variable and never writes an analysis conclusion.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from download_inputs import fetch, parse_knmi, save

STATION = "260"
YEAR = 2024
# KNMI hourly parameter codes offered by the daggegevens service.
CANDIDATE_VARS = [
    "DD", "FH", "FF", "FX", "T", "TD", "SQ", "Q", "DR", "RH", "P",
    "VV", "N", "U", "WW", "IX", "M", "R", "S", "O", "Y",
]


def header_columns(text: str) -> list[str]:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()
            if candidate.startswith("STN") and "YYYYMMDD" in candidate:
                return [x.strip() for x in candidate.split(",")]
    raise ValueError("KNMI column header not found")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--station", default=STATION)
    parser.add_argument("--year", type=int, default=YEAR)
    args = parser.parse_args()

    start = f"{args.year}010101"
    end = f"{args.year}123124"
    params = {"stns": args.station, "start": start, "end": end, "vars": ":".join(CANDIDATE_VARS)}
    raw, meta = fetch("https://www.daggegevens.knmi.nl/klimatologie/uurgegevens?"
                      + "&".join(f"{k}={v}" for k, v in params.items()))
    text = raw.decode("utf-8-sig")
    columns = header_columns(text)
    rows = parse_knmi(text)
    present = [c for c in columns if c not in {"STN", "YYYYMMDD", "HH"}]

    availability: dict[str, dict] = {}
    with_fraction: dict[str, float] = {}
    # Re-parse raw rows to obtain every returned variable verbatim.
    header = None
    verbatim: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()
            if candidate.startswith("STN") and "YYYYMMDD" in candidate:
                header = [x.strip() for x in candidate.split(",")]
            continue
        if not stripped or header is None:
            continue
        verbatim.append(dict(zip(header, [x.strip() for x in stripped.split(",")])))

    for name in present:
        values = [r.get(name, "") for r in verbatim]
        non_empty = sum(1 for v in values if v not in ("", None))
        availability[name] = {
            "non_empty": non_empty,
            "rows": len(values),
            "missing": len(values) - non_empty,
        }
        numeric = [int(v) for v in values if v not in ("", None) and v.lstrip("-").isdigit()]
        if numeric:
            with_fraction[name] = non_empty / max(len(values), 1)

    out_dir = args.root / "outputs" / "gates"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "probe_status": "VARIABLE_AVAILABILITY_ONLY_NO_ANALYSIS_CONCLUSION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request_parameters": params,
        "requested_variables": CANDIDATE_VARS,
        "returned_header": columns,
        "returned_variables": present,
        "parsed_rows": len(rows),
        "verbatim_rows": len(verbatim),
        "availability": availability,
        "retrieval": {k: meta[k] for k in ("url", "http_status", "retrieved_at", "sha256", "bytes")},
    }
    dest = args.root / "data" / "raw" / "knmi_probe" / f"knmi_{args.station}_{args.year}_allvars.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    save(raw, meta, dest)
    with dest.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(verbatim)
    (out_dir / "G3_knmi_variable_availability.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(verbatim), "returned_variables": present,
                      "availability": availability},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
