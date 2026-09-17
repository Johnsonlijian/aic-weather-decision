"""G1 batch 2: targeted verification of named paper families (Crossref + OpenAlex).

Each query targets a paper family that the G1 novelty gate must cover explicitly.
Every hit keeps the exact request URL so the verification method is reproducible.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from g1_search_lib import RAW, run_batch  # noqa: E402

QUERIES = [
    # --- named target families ---
    "Kerkhove Vanhoucke optimised scheduling for weather sensitive offshore construction projects",
    "Zhou Ma Yang Zhang stochastic resource constrained project scheduling time varying weather",
    "Ballesteros-Perez del Campo Sanz Incorporating the effect of weather in construction scheduling sine wave curves",
    "Ballesteros-Perez Smith Lloyd Weather-wise weather-aware planning tool construction productivity claims",
    "Ballesteros-Perez weather-related claims construction contracts new approach",
    "Richardson economic value of weather forecasts cost loss ratio",
    "Zhu Toth forecasting rain decision making cost loss ratio meteorological",
    "Kull forecast value decision making cost loss model meteorological applications",
    "Roulin relative economic value ensemble prediction systems",
    "Murphy quality value relationship forecasts decision making",
    "Elmachtoub Grigas Smart Predict then Optimize",
    "Richardson verification decision oriented forecast threshold",
    # --- weather window / offshore installation ---
    "Barlow Teixeira weather window offshore wind installation risk",
    "Sarker Faiz offshore wind farm installation scheduling weather window optimization",
    "Irawan Jones offshore wind installation vessel routing scheduling weather",
    "Dalgic Lazakis weather window availability offshore wind O&M",
    "Kuik Veldman offshore wind farm installation weather downtime simulation",
    "Paterson Perez offshore wind installation weather window probabilistic",
    "Kerkhove Vanhoucke project scheduling with weather sensitive activities",
    "Vanhoucke weather sensitive project scheduling simulation net present value",
    # --- construction weather productivity ---
    "Larsson Smith construction productivity weather rainfall model",
    "Thomas Riley daily labour productivity model weather",
    "Moselhi Khan weather impact construction productivity neural network",
    "Lee Thomas weather effects construction productivity regression",
    # --- GFS / ERA5 applied ---
    "global forecast system GFS forecast skill verification surface wind gusts",
    "ERA5 reanalysis wind gust evaluation observations",
    "numerical weather prediction construction industry application forecast",
    # --- scheduling under uncertainty / nonanticipativity ---
    "nonanticipativity stochastic programming online decision rolling horizon",
    "lookahead policies stochastic scheduling rollout information relaxation",
    "value of information forecast scheduling operations decision",
    "weather window probabilistic forecasting marine operation go no-go decision",
    "threshold exceedance probabilistic forecast decision making binary event",
    "calibration reliability sharpness probabilistic forecasts proper scoring rules",
]

if __name__ == "__main__":
    res = run_batch(QUERIES, rows=6)
    p = RAW / "batch2_metadata.json"
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
                    (it.get("title") or "")[:130],
                    "|",
                    (it.get("container") or "")[:55],
                    "|",
                    it.get("doi"),
                )
