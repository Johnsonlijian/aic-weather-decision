"""Triage: extract candidate DOIs from a g1 discovery batch JSON by keyword relevance.

Reads sources/raw/g1/<batch>.json (or *_flat.json) and prints compact records whose title
matches any of the requested keyword groups, so that the strongest nearest-work candidates
can be selected for DOI-level verification.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw" / "g1"

GROUPS = {
    "A_weather_sched": ["weather", "rain", "wind", "climate", "gust"],
    "B_decision_value": ["cost-loss", "cost loss", "value of", "economic value",
                         "decision", "verification", "calibration", "reliability",
                         "predict", "regret", "foresight", "information"],
    "C_offshore": ["offshore", "weather window", "downtime", "marine", "vessel",
                   "installation", "operability", "jack-up", "pipelay"],
    "D_forecast_data": ["forecast", "nwp", "gfs", "era5", "ecmwf", "reanalysis",
                        "numerical weather"],
    "E_scheduling_unc": ["scheduling", "project", "nonanticipat", "rolling horizon",
                         "uncertainty", "stochastic", "simulation"],
}


def load(batch: str) -> dict:
    p = RAW / f"{batch}_flat.json"
    if not p.exists():
        p = RAW / f"{batch}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(d, dict) and "openalex" not in d and "crossref" not in d:
        return d
    flat = {}
    for blk in ("openalex", "crossref"):
        for entry in d.get(blk, []):
            for it in entry.get("items", []):
                if it.get("doi"):
                    flat.setdefault(it["doi"].lower(), it)
    return flat


def main() -> None:
    batches = sys.argv[1:] or ["batchC", "batchD"]
    keys = list(GROUPS)
    seen = set()
    for b in batches:
        try:
            flat = load(b)
        except FileNotFoundError:
            print(f"!! missing {b}")
            continue
        print(f"\n########## {b}: {len(flat)} unique works ##########")
        for doi, it in flat.items():
            if doi in seen:
                continue
            t = (it.get("title") or "").lower()
            hits = [g for g in keys if any(k in t for k in GROUPS[g])]
            if not hits:
                continue
            seen.add(doi)
            print(f"[{'/'.join(hits)}] {it.get('year')} | {(it.get('title') or '')[:130]}")
            print(f"        {(it.get('container') or '')[:70]} | {doi} | "
                  f"cit={it.get('cited_by_count') or it.get('cited_by')}")


if __name__ == "__main__":
    main()
