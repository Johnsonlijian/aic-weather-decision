"""G1 batch 4: DOI-level verification of the classic decision-analytic / verification /
weather-downtime / NWP-archive citations that the G1 gate must cite by exact identity.

These are bibliographic look-ups (title+author family) rather than topic searches, so a
first-page top hit is strong evidence of the exact record. Each hit keeps its request URL.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g1_search_lib import RAW, run_batch  # noqa: E402

QUERIES = [
    # --- cost-loss / value of forecast (meteorology) ---
    "Thompson On the operational deficiencies of weather forecasts 1952",
    "Murphy The value of climatological categorical and perfect forecasts",
    "Katz Murphy Economic value of weather and climate forecasts",
    "Richardson Skill and relative economic value of the ECMWF ensemble prediction system",
    "Zhu Toth The economic value of ensemble based weather forecasts",
    "Roulin Skill and relative economic value of medium range forecasts",
    "Kull The value of weather forecasts decision making cost loss",
    "Murphy What is a good forecast an essay on the nature of goodness in weather forecasting",
    "Wilks sampling distributions of the Brier score reliability",
    "Brier Verification of forecasts expressed in terms of probability",
    "Gneiting Raftery Weather forecasting with ensemble methods probabilistic",
    "Gneiting Balabdaoui Raftery Probabilistic forecasts calibration and sharpness",
    # --- weather downtime / construction scheduling classics ---
    "Ballesteros-Perez del Campo Sanz Weather-wise weather aware planning tool",
    "Ballesteros-Perez Incorporating the effect of weather in construction scheduling management sine wave",
    "Ballesteros-Perez Dealing with weather related claims in construction contracts new approach",
    "Thomas Riley Long term labour productivity model formwork",
    "Moselhi Khan Analysis of labour productivity weather neural network",
    "Larsson Effect of weather on construction productivity",
    # --- offshore weather window / installation classics ---
    "Kerkhove Vanhoucke Optimised scheduling for weather sensitive offshore construction projects",
    "Kerkhove Vanhoucke Scheduling of offshore construction projects weather",
    "Sarker Faiz Minimizing installation cost offshore wind weather window",
    "Irawan Jones Optimisation of offshore wind farm maintenance weather window",
    "Kuik Veldman Offshore wind farm installation weather uncertainty",
    "Dalgic Lazakis Investigation of optimum jack up vessel positioning offshore wind",
    "Paterson Offshore wind installation weather window scheduling optimisation",
    "Barlow Teixeira Weather window risk offshore operations",
    # --- NWP archive / forecast data provenance ---
    "Hersbach ERA5 global reanalysis",
    "Saha NCEP Climate Forecast System Reanalysis",
    "NCEP operational global forecast system GFS documentation",
    "Kalnay NCEP NCAR 40 year reanalysis project",
    # --- decision-focused / predict-then-optimize ---
    "Elmachtoub Grigas Smart Predict then Optimize Management Science",
    "Bertsimas Kallus From predictive to prescriptive analytics",
    "Donti Amos Kolter Task based end to end model learning for decision making",
    "Ban Radovic Delage Structural reliability assessment machine learning",
]

if __name__ == "__main__":
    res = run_batch(QUERIES, rows=4)
    p = RAW / "batch4_metadata.json"
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)
    for blk in ("crossref", "openalex"):
        for entry in res[blk]:
            print(f"[{blk}:{entry['tag']}] {entry['query']!r} err={entry['error']}")
            for it in entry["items"]:
                auth = it.get("authors") or []
                print(
                    "   -",
                    it.get("year"),
                    "|",
                    (it.get("title") or "")[:125],
                    "|",
                    (it.get("container") or "")[:50],
                    "|",
                    it.get("doi"),
                    "|",
                    "; ".join(auth[:3]),
                )
