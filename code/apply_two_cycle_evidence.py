"""Apply the two-cycle (00 UTC + 12 UTC) evidence to the manuscript.

Every replacement is asserted, so a silent miss cannot leave the text describing
an older dataset than the one the results were computed from.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md"

N_MSG = 39646
N_RUNS = 3306
N_ROWS = 281817
SPLITS = (169184, 65491, 47142)

text = MD.read_text(encoding="utf-8")
edits: list[tuple[str, str]] = []

# ---- dataset paragraph ----
old = [l for l in text.split("\n") if l.startswith("Observations are KNMI")][0]
new = (
    "Observations are KNMI hourly records from June 2021 to September 2025 at the 46 stations the provider "
    "endpoint actually serves, downloaded with four variables (mean wind, gust, 2 m temperature, precipitation): "
    "1,737,696 station-hours [@knmi]. One station reports no wind and is excluded, leaving 45 usable sites "
    "(gust coverage above 95%); temperature is reported by 30 of them and precipitation by 6, so the wind analysis "
    "uses all 45 and the multi-hazard extension is scoped to the stations that support it. Forecasts are NOAA GFS "
    "0.25-degree surface `GUST` messages, transferred only as their bounded GRIB byte ranges and validated before "
    f"decoding: {N_MSG:,} as-issued messages from {N_RUNS:,} runs covering both the 00 and 12 UTC cycles "
    "(6\u201372 h leads at 6-hourly steps), each with per-message SHA-256 provenance [@gfsarchive]. Station coordinates "
    "for the grid lookup come from a published station table (CRAN spatialrisk 0.8.2, knmi_stations), because the "
    "provider station-list file answers HTTP 403 to programmatic clients."
)
edits.append((old, new))

# ---- Table 1 (two-cycle) ----
edits.append(("Table 1. Detector performance of the raw deterministic rule on the held-out 2025 split (45 stations, 47,276 epochs).",
              f"Table 1. Detector performance of the raw deterministic rule on the held-out 2025 split "
              f"(45 stations, {SPLITS[2]:,} epochs)."))
edits.append(("| 9.0 | 40.9% | 47.0% | 15.6% | 30.7% | 22,228 |",
              "| 9.0 | 40.7% | 47.0% | 15.4% | 30.8% | 22,174 |"))
edits.append(("| 12.0 | 18.8% | 20.1% | 8.0% | 38.4% | 9,489 |",
              "| 12.0 | 18.9% | 20.0% | 8.0% | 37.9% | 9,450 |"))
edits.append(("| 13.0 | 13.3% | 14.5% | 5.7% | 42.2% | 6,838 |",
              "| 13.0 | 13.3% | 14.4% | 5.8% | 42.3% | 6,811 |"))
edits.append(("| 16.5 | 3.8% | 5.1% | 1.6% | 53.8% | 2,399 |",
              "| 16.5 | 3.8% | 5.1% | 1.6% | 53.5% | 2,392 |"))
edits.append(("| 20.0 | 1.2% | 1.1% | 0.7% | 51.3% | 507 |",
              "| 20.0 | 1.2% | 1.1% | 0.7% | 53.6% | 506 |"))

# ---- 3.1 detector text ----
edits.append(("At the primary 12 m/s limit the rule claims an exceedance in 18.8% of blocks while the true rate is 20.1%: it misses 38.4% of real exceedance blocks and still alarms on 8.0% of safe blocks. Across the documented limit spread the miss rate runs from 30.7% to 53.8%.",
              "At the primary 12 m/s limit the rule claims an exceedance in 18.9% of blocks while the true rate is 20.0%: it misses 37.9% of real exceedance blocks and still alarms on 8.0% of safe blocks. Across the documented limit spread the miss rate runs from 30.8% to 53.6%."))

# ---- 3.2 skill ----
edits.append(("the binned calibrator lifts Brier skill over climatology by +0.41 (9.0 m/s), +0.41 (12.0), +0.41 (13.0), +0.37 (16.5) and +0.28 (20.0), and over the raw threshold by +0.35, +0.32, +0.31, +0.26 and +0.38 respectively, all on the 47,276-epoch test split the calibrator never saw. The rare-event ceiling of the three-station pilot is gone: the 20 m/s event now has 507 test positives instead of 26.",
              "the binned calibrator lifts Brier skill over climatology by +0.41 (9.0 m/s), +0.42 (12.0), +0.41 (13.0), +0.38 (16.5) and +0.27 (20.0), and over the raw threshold by +0.35, +0.32, +0.32, +0.26 and +0.37 respectively, all on the 47,142-epoch test split the calibrator never saw. The rare-event ceiling of the three-station pilot is gone: the 20 m/s event now has 506 test positives instead of 26."))

# ---- 3.3 REV ----
edits.append(("the calibrated rule relative value peaks at 0.44 (9.0 m/s), 0.25 (12.0), 0.24 (13.0) and 0.18 (16.5), decaying toward zero at 20 m/s where the event becomes rare.",
              "the calibrated rule relative value peaks at 0.44 (9.0 m/s), 0.25 (12.0), 0.24 (13.0) and 0.17 (16.5), decaying toward zero at 20 m/s where the event becomes rare."))

# ---- spatial transfer + lead ----
edits.append(("Fitting the calibrator on the other 44 stations and evaluating it on the station held out (leave-one-station-out) gives a median held-out Brier skill of +0.368 over climatology, negative on only 2 of 45 stations; fitting on that station own history instead gives +0.392, and the raw threshold gives +0.108. The mechanism transfers: a site with no calibration history still gains about 0.37 Brier skill from a table fitted elsewhere, and about 0.02 more when the table is fitted locally.",
              "Fitting the calibrator on the other 44 stations and evaluating it on the station held out (leave-one-station-out) gives a median held-out Brier skill of +0.377 over climatology, negative on only 2 of 45 stations; fitting on that station own history instead gives +0.398, and the raw threshold gives +0.123. The mechanism transfers: a site with no calibration history still gains about 0.38 Brier skill from a table fitted elsewhere, and about 0.02 more when the table is fitted locally."))
edits.append(("Skill also depends on lead. Under the audited availability rule with 12 UTC runs, the usable lead for a 12 h window falls between 12 and 30 hours, and the test skill is +0.32 (12 h), +0.46 (18 h), +0.43 (24 h) and +0.36 (30 h). Because the lead bins contain different station mixes, we report the range rather than fitting a decay curve.",
              "Skill also depends on lead. Because both cycles are archived and the availability rule admits only a run issued at least four hours before the decision, the lead actually used for a 12 h window is 12 or 18 hours, and the test skill is +0.39 (12 h) and +0.41 (18 h). Adding the second cycle therefore also removed the long-lead tail that the single-cycle archive forced on half the epochs, and it left the skill essentially unchanged across the two leads now in use."))

# ---- rare-event subsection: expand wording for the two-cycle table ----
edits.append(("With 45 stations the documented 20 m/s event is estimable (507 test positives, +0.28 Brier skill over climatology), whereas the three-station pilot had 26.",
              "With 45 stations the documented 20 m/s event is estimable (506 test positives, +0.27 Brier skill over climatology), whereas the three-station pilot had 26."))

# ---- abstract ----
old_abs = text[text.index("# Abstract"):text.index("**Keywords:**")]
new_abs = (
    "# Abstract {-}\n\n"
    "A crane lift is scheduled by comparing an archived wind-gust forecast with a documented in-service limit, yet the "
    "forecast is an instantaneous grid-point gust and the decision depends on whether any hour of the window will exceed "
    f"the limit. Across 46 KNMI stations and five years ({N_ROWS:,} decision epochs built from {N_MSG:,} byte-verified GFS "
    "messages), the raw deterministic threshold misses 31-54% of true exceedance events and alarms on up to 15.4% of safe "
    "blocks. Calibrating the block event at the decision level under an archive-audited latency rule recovers the signal: "
    "held-out Brier skill is +0.27 to +0.42 over climatology and +0.26 to +0.37 over the raw threshold, a calibrator fitted "
    "without a station still transfers to it (median +0.38), and the calibrated rule spans an exposure-miss frontier whose "
    "economic value peaks at 0.17-0.44. The decision fails at the detector, not the weather model; the repair is a per-site "
    "probability table.\n\n"
)
edits.append((old_abs, new_abs))

applied = 0
for old_text, new_text in edits:
    if old_text in text:
        text = text.replace(old_text, new_text, 1)
        applied += 1
    else:
        raise SystemExit(f"replacement not found: {old_text[:90]}...")

MD.write_text(text, encoding="utf-8")
abstract = text[text.index("# Abstract"):text.index("**Keywords:**")]
print(f"applied {applied}/{len(edits)} edits; abstract words = {len(abstract.replace('# Abstract {-}', '').split())}")
print(json.dumps({"messages": N_MSG, "runs": N_RUNS, "epochs": N_ROWS, "splits": SPLITS}))
