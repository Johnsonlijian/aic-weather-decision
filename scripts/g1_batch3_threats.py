"""G1 batch 3: threat-hunting queries (offshore response forecasting, weather-window
decisions, forecast value in operations, non-anticipative construction scheduling).

Console output is forced to UTF-8 so non-ASCII author names do not raise on GBK consoles.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g1_search_lib import RAW, run_batch  # noqa: E402

QUERIES = [
    "Use of response forecasting in decision making for weather sensitive offshore construction work",
    "offshore construction decision making forecast response based weather window",
    "weather sensitive offshore construction work forecast decision support vessel operation",
    "probabilistic weather forecast marine operation decision threshold downtime",
    "value of forecast information construction project scheduling simulation",
    "weather window forecast verification offshore operation lead time",
    "forecast calibration logistic regression gust threshold operation decision",
    "threshold based forecast verification user decision meteorology",
    "decision oriented verification forecast binary event threshold exceedance",
    "non-anticipative scheduling weather uncertainty construction online",
    "rolling horizon weather forecast scheduling construction lookahead",
    "wind forecast uncertainty crane operation planning construction site",
    "offshore wind installation weather window forecast probabilistic scheduling",
    "construction weather risk decision analysis expected utility forecast",
    "weather forecasting for construction site operations short term",
    "impact of forecast accuracy on construction scheduling decisions value",
    "cost loss ratio applied operation decision threshold forecast value",
    "relative economic value of forecasts operational decision threshold",
    "reliability diagram calibration forecast threshold event probability",
    "weather window duration statistics offshore installation operability",
    "operability analysis offshore installation weather downtime monte carlo",
    "probabilistic forecasting of weather windows for marine operations",
    "predict then optimize decision focused learning scheduling",
    "contextual optimization decision aware prediction training loss",
    "look ahead scheduling weather forecast energy operations rolling horizon",
    "value of information perfect foresight scheduling regret benchmark",
    "perfect information benchmark scheduling regret weather",
    "GFS forecast archive building energy scheduling decision study",
    "ERA5 versus station observations wind construction site assessment",
    "project scheduling weather sensitive activities simulation offshore Vanhoucke",
]

if __name__ == "__main__":
    res = run_batch(QUERIES, rows=6)
    p = RAW / "batch3_metadata.json"
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
