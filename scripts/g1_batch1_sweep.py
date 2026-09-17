"""G1 batch 1: broad novelty sweep across Crossref + OpenAlex (metadata only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from g1_search_lib import RAW, run_batch  # noqa: E402

QUERIES = [
    # --- weather-sensitive project scheduling ---
    "weather sensitive project scheduling construction",
    "weather-aware planning tool construction productivity claims",
    "stochastic resource-constrained project scheduling time varying weather conditions estimation of distribution algorithm",
    "weather impact construction labour productivity scheduling simulation",
    "rain effect construction activity duration delay model",
    # --- offshore weather windows / downtime ---
    "weather window offshore wind turbine installation scheduling",
    "weather downtime modelling offshore construction operations",
    "marine operations weather window forecast decision support installation",
    "offshore installation vessel scheduling weather uncertainty optimization",
    "access window forecasting offshore maintenance operation planning",
    # --- value of forecast / cost-loss / decision-analytic verification ---
    "cost-loss ratio forecast value decision making meteorology",
    "relative operating characteristic economic value weather forecast",
    "value of weather forecast decision analytic cost loss model",
    "economic value of ensemble forecasts decision making",
    "user oriented verification forecast decision threshold exceedance",
    "forecast calibration decision threshold binary event reliability",
    # --- decision-focused learning / predict then optimize ---
    "smart predict then optimize decision focused learning",
    "decision focused learning prediction optimization end to end",
    "predict then optimize contextual stochastic optimization",
    # --- simulation-optimization under uncertainty / nonanticipativity ---
    "nonanticipative online scheduling rolling horizon lookahead scheduling uncertainty",
    "simulation optimization project scheduling correlated random numbers variance reduction",
    "proactive reactive scheduling weather uncertainty offshore project",
    # --- archives: GFS / ERA5 / ECMWF applied ---
    "GFS global forecast system forecast data construction scheduling",
    "ERA5 reanalysis construction weather productivity study",
    "ECMWF ensemble forecast operational decision construction energy",
    "archived numerical weather prediction forecast verification built environment",
    # --- construction / crane operation decisions ---
    "crane lifting operation wind speed threshold safety decision",
    "wind speed limit tower crane operation stoppage construction",
    "weather risk management construction project schedule delay",
    "decision support system construction weather forecast delay claim",
    # --- construction 4.0 / digital twin weather ---
    "digital twin weather informed construction scheduling",
    "machine learning construction schedule delay prediction weather",
]

if __name__ == "__main__":
    res = run_batch(QUERIES, rows=6)
    p = RAW / "batch1_metadata.json"
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)
    for blk in ("crossref", "openalex"):
        for entry in res[blk]:
            print(f"[{blk}:{entry['tag']}] {entry['query']!r} err={entry['error']}")
            for it in entry["items"]:
                print(
                    "   -",
                    it.get("year"),
                    "|",
                    (it.get("title") or "")[:120],
                    "|",
                    (it.get("container") or "")[:55],
                    "|",
                    it.get("doi"),
                )
