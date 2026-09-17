#!/usr/bin/env python
"""Build outputs/gates/G1_expansion_matrix.csv from the verified G1-expansion records."""
from __future__ import annotations

import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V1 = json.load(open(os.path.join(ROOT, "sources/raw/g1x/verified_batch1.json"), encoding="utf-8"))
V2 = json.load(open(os.path.join(ROOT, "sources/raw/g1x/verified_batch2.json"), encoding="utf-8"))
EXTRA = json.load(open(os.path.join(ROOT, "sources/raw/g1x/verified_extra.json"), encoding="utf-8"))
BY_DOI = {}
for rec in V1 + V2 + EXTRA:
    BY_DOI[rec["doi"].lower()] = rec

DATE = "2026-09-15"
IETF = "https://www.ietf.org/rfc/rfc3339.txt"

# cite_key, doi, direction, object_and_domain, weather_input, calibration_target, dataset_used,
# why_relevant, threat_level, how_we_differ, evidence_level
ROWS = [
    # ---------------- Direction 1: crane / lifting wind safety ----------------
    ("augustyn2025app", "10.3390/app15094683", "1-crane-wind",
     "Top-slewing tower crane structural stability: CFD + analytical critical (overturning) wind speed, by jib angle and payload; two crane configurations",
     "None. No forecast, no observation timeseries; wind is a design load case",
     "None. Output is a critical wind-speed value (35-53 m/s) compared against standards",
     "CFD simulations of crane aerodynamics + analytical overturning model (own model, no public dataset)",
     "The only 2025 peer-reviewed work that puts a defensible wind-threshold number on a tower crane; open access so reviewers will find it. Anchors why 9-20 m/s in-service limits are administrative, and gives the paper a citable structural-safety contrast",
     "medium (framing risk, not measurement risk)",
     "It asks when the machine fails (35-53 m/s); this paper asks whether the planner correctly knows the contracted limit is exceeded (9-20 m/s). No forecast, no decision epoch, no window event, no calibration, no economic value. Its critical speeds are 2-5x above every documented in-service limit, which is exactly why the binding operational question is a decision-detection problem rather than a stability problem",
     "abstract+metadata only"),

    ("li2023jmse", "10.3390/jmse11040803", "1-crane-wind",
     "Single instrumented tower crane (IoT monitoring) through super typhoon In-fa; two ML models predict tower displacement from measured site wind speed",
     "Site-measured wind speed from the monitoring system (not a forecast, not a station archive)",
     "None. Prediction target is structural displacement, not a decision event",
     "Long-term IoT monitoring records from one coastal construction site (proprietary, not public)",
     "Documents the response lag and weathercock effect in the crane NON-WORKING state and shows max displacement does not coincide with max wind - directly relevant to whether a 10 m station gust is a valid proxy for crane-level load, and to the parked-state caveat in the wind-engineering threat",
     "low (strengthens the paper's stated boundary by making the height/state caveat citable)",
     "Measured wind in, structural response out. No forecast archive, no forecast publication latency, no operational threshold, no probability calibration, no decision or schedule evaluation. Included for the physical-proxy caveat, not as prior art for the measurement",
     "abstract+metadata only"),

    ("hu2023ssci", "10.1016/j.ssci.2022.106044", "1-crane-wind",
     "Construction site: estimating and visualising worker exposure to tower-crane operation hazards (kinematic exposure from crane motion and site geometry)",
     "None. No weather variable at all",
     "None",
     "Site geometry / crane motion simulation (own model)",
     "Establishes that 'crane operation exposure' is an accepted measurable object in Safety Science, so the exposure-miss frontier has a familiar home; useful for the Introduction's framing of exposure as a first-class quantity",
     "low",
     "Its exposure is kinematic (being under a moving crane), not informational (attempting a lift in a block whose true wind exceeds the limit). No weather input, no forecast, no threshold, no calibration, no economic value",
     "abstract+metadata only"),

    ("chen2019jlf", "10.1177/1461348419847306", "1-crane-wind",
     "Single tower crane: full-scale CFD wind coefficients + FE random-vibration analysis; wind-induced vibration and safety evaluation",
     "Simulated fluctuating wind (autoregressive time histories), wind speed spectra; no observation and no forecast",
     "None. Output is displacement/stress/acceleration against design rules",
     "FE model of one tower crane (own model)",
     "Deliberate pre-2022 anchor showing that wind acting on cranes is a decades-settled structural question; helps the paper avoid implying that 'wind matters for cranes' is new",
     "low",
     "Design-stage structural analysis with synthetic wind. No forecast archive, no operational limit, no decision, no window event, no calibration",
     "abstract+metadata only"),

    ("wang2024lnme", "10.1007/978-981-97-1876-4_60", "1-crane-wind",
     "QTZ25 tower crane: wind-induced response and wind-vibration coefficient under different wind speed spectra and wind direction angles",
     "Simulated wind speed time histories (harmonic synthesis) for Simiu, Davenport and Harris spectra",
     "None",
     "Parametric APDL finite-element model (own model)",
     "Quantifies how much the structural demand estimate moves with the assumed wind spectrum (12.0-18.6% coefficient deviation) - a useful, citable statement that wind-input assumptions carry real uncertainty, which supports treating the gust/mean averaging interval as a sensitivity axis",
     "low",
     "Structural dynamics only. No measurement, no forecast, no operational threshold, no decision, no schedule, no calibration",
     "abstract+metadata only"),

    # ---------------- Direction 2: multi-hazard operational windows ----------------
    ("jafarpour2023marstruc", "10.1016/j.marstruc.2023.103483", "2-multihazard",
     "Transportation of large-scale offshore structures: optimal weather window determination",
     "Metocean conditions / reliability-based window analysis (abstract not exposed by Crossref)",
     "Not verifiable at abstract level; companion to the float-over paper already in the matrix",
     "Not verified (no full text retrieved)",
     "Same authors as jafarpour2024 already in the positioning matrix, so a reviewer will read this as one line of work; it must be cited together with that paper to avoid appearing to miss it",
     "medium (companion work, not an independent method)",
     "Second paper by the same authors on the same reliability-based weather-window logic. Shares the three established differences from this study: no archived as-issued forecast, no forecast-publication latency audit, no fitted calibration of the forecast-to-event mapping. No statistical (Brier/reliability) calibration of a recurring decision event",
     "abstract+metadata only"),

    ("wu2021marstruc", "10.1016/j.marstruc.2021.103050", "2-multihazard",
     "Marine operations: methodology for a response-based correction factor (alpha-factor) for allowable sea state assessment",
     "Weather forecast uncertainty enters explicitly as the quantity the alpha-factor is designed to absorb",
     "The alpha-factor itself: a response-based safety correction on the allowable sea state, NOT a fitted probability of a decision event",
     "Not verified (no full text retrieved); Crossref records a CC BY licence on the article",
     "This is the theoretical home of the alpha-factor that doskeland2023 applies. It pre-empts any reading that 'replacing alpha-factors with calibration' is itself a new observation, so it must be cited wherever the paper contrasts alpha-factors with fitted calibration",
     "high (occupies the alpha-factor concept the paper contrasts against)",
     "It derives a correction factor on an allowable limit to cover forecast uncertainty; it does not fit P(decision event | forecast), does not produce Brier/reliability diagnostics, and is not a multi-year archive replay. The distinction to state precisely is response-based safety correction of a limit versus statistical calibration of a recurring decision event",
     "abstract+metadata only"),

    ("wang2016omae", "10.1115/omae2016-54774", "2-multihazard",
     "Multi-phase offshore floating bulk transshipment operation: downtime/operability methodology with per-phase durations and sea-state shift during the operation",
     "Persistency statistics of waves (scatter diagrams vs persistence); wind and current explicitly NOT considered",
     "None. Output is estimated downtime from persistency vs scatter analysis",
     "Persistency data / wave scatter diagrams (not a forecast archive)",
     "The closest classical analogue to a multi-hour uninterrupted window with phase structure, and it demonstrates that ignoring persistency makes downtime estimates optimistic - a citable precedent for why the window-maximum event differs from a point condition",
     "medium",
     "Persistence-statistics input, not an as-issued forecast; single-hazard (waves only, wind and current explicitly excluded); no publication latency, no probability calibration, no cost-loss value, no chronologically held-out replay",
     "abstract+metadata only"),

    ("li2025oceaneng", "10.1016/j.oceaneng.2025.121664", "2-multihazard",
     "Joint probability of significant wave height and wind speed under extreme weather conditions (multivariate/copula joint structure)",
     "Climatological joint distribution of two metocean variables; no forecast",
     "None. Output is a joint probability structure, not a calibrated decision probability",
     "Not verified (no full text retrieved)",
     "The multi-hazard climatology half of the problem: establishes that wind and wave are treated jointly in the offshore literature, which makes the paper's single-variable gust input a visible limitation and makes a two-variable decision event a natural extension",
     "low",
     "Joint CLIMATOLOGICAL probability of two hazards; no forecast, no decision, no operational threshold, no event calibration, no schedule. This paper studies the joint INFORMATION problem (which forecast, how calibrated), not the joint climatology",
     "abstract+metadata only"),

    ("mohamed2024wace", "10.1016/j.wace.2024.100718", "2-multihazard",
     "Compound hail, wind and rainfall extremes in Alberta's hail alley: multivariate extreme-value analysis; shows single-hazard risk assessment is incomplete and potentially misleading",
     "Observational extreme-value climatology of three hazards jointly",
     "None",
     "Regional observational record of hail, wind and rainfall extremes",
     "The clearest published statement that wind-only analysis is incomplete when rain co-occurs; gives the paper a citable justification for naming a wind+rain operational window as future work rather than leaving the single-hazard choice undefended",
     "medium (constrains the 'single-hazard' limitation)",
     "Regional compound-extremes climatology for hail risk. No operation, no forecast, no window, no decision, no calibration, no economic evaluation. It supplies the motivation for a multi-hazard window; it does not perform one",
     "abstract+metadata only"),

    ("wu2022jmse", "10.3390/jmse10020284", "2-multihazard",
     "5 MW floating wind turbine: load response under the COMBINED action of wind and rain (Euler multiphase solver WARFoam; rain-load influence envelope)",
     "Simulated wind and rain fields (no observation, no forecast)",
     "None. Output is a structural load response and an influence-coefficient envelope",
     "Own CFD solver and simulation cases",
     "The only work found that physically couples wind AND rain as simultaneous loads; it shows the physical coupling is real and quantified, which is what makes a joint wind+rain operability criterion a defensible next step rather than a speculative one",
     "low",
     "Structural load physics on a single turbine. No forecast, no operational window, no decision, no calibration, no scheduling or economic evaluation",
     "abstract+metadata only"),

    # ---------------- Direction 3: ensemble / probabilistic forecasts as decision inputs ----------------
    ("schulz2022mwr", "10.1175/mwr-d-21-0150.1", "3-ensemble-decisions",
     "Wind-gust ensemble postprocessing: systematic comparison of eight statistical and machine-learning methods (EMOS, member-by-member, isotonic distributional regression, gradient-boosting EMOS, quantile regression forests, three neural-network approaches)",
     "High-resolution convection-permitting ENSEMBLE prediction system run operationally at the German weather service (DWD)",
     "The MARGINAL gust distribution (calibrated probabilistic gust forecasts verified against observations)",
     "6 years of operational ensemble forecasts + hourly observations at 175 German surface stations",
     "The closest methodological neighbour found in this whole expansion: multi-year, multi-station, ensemble-based calibrated probabilistic GUST forecasting. A reviewer may ask why this paper uses a binned table on deterministic GFS instead of postprocessing an ensemble; the paper must answer that explicitly",
     "high (closest methodological alternative to the repair the paper proposes)",
     "Its target is the marginal gust distribution, not a decision event; there is no operational contract, no block/window maximum, no schedule, no exposure-miss accounting, no cost-loss value, and no forecast-publication latency audit. It answers 'how do we sharpen the gust probability', not 'does the planner's decision event become resolvable within the information actually available'",
     "abstract+metadata only"),

    ("coburn2022waf", "10.1175/waf-d-21-0118.1", "3-ensemble-decisions",
     "Skill improvement for short-term forecasting of wind-gust OCCURRENCE and MAGNITUDE using artificial neural networks vs regression, with an autoregressive term; model uncertainty via 1000 random 70/30 train-test subsets",
     "ERA5 reanalysis geophysical predictors plus an autoregressive term",
     "Gust occurrence probability and gust magnitude (marginal), not a decision event",
     "ERA5 predictors + observations at three high-passenger-volume US airports",
     "Provides the direct precedent that modelled gust OCCURRENCE PROBABILITIES improve with ML, which is adjacent to this paper's core move (thresholding a value versus estimating an event probability) and must be distinguished from it",
     "medium",
     "Marginal gust occurrence/magnitude at point locations; no operation, no window maximum, no contract threshold, no schedule, no calibration-of-decision-object, no economic value. It improves the forecast; this paper measures whether the DECISION becomes resolvable",
     "abstract+metadata only"),

    ("benacek2023waf", "10.1175/waf-d-22-0006.1", "3-ensemble-decisions",
     "Tree-based probabilistic postprocessing of ensemble forecasts (natural gradient boosting, quantile random forests, distributional regression forests) benchmarked against EMOS and its boosting version",
     "ECMWF ensemble prediction, hourly 2 m temperature, lead times 1-10 days, Czech Republic domain",
     "The conditional predictive distribution of 2 m temperature",
     "ECMWF ensemble; training periods 2015-18 and 2018-only; skill evaluated on a held-out 2019",
     "Its chronological hold-out design (train on earlier years, evaluate on a reserved later year) is exactly the evaluation discipline this paper claims, so it is a citable methodological precedent that also shows the discipline is standard - the novelty cannot rest on the split alone",
     "medium",
     "Target is temperature and is the marginal distribution, not a decision event; no operations or scheduling, no window, no cost-loss value, no forecast-availability audit. It supplies the hold-out precedent; this paper supplies the decision-event object and the availability boundary",
     "abstract+metadata only"),

    ("kolios2023oceaneng", "10.1016/j.oceaneng.2023.115265", "3-ensemble-decisions",
     "Offshore wind farm availability / O&M simulation: three forecast-modelling methods (Markov chains, gradient boosting, novel hybrid regression/statistical) generate wind and wave projections that feed an O&M simulation model over the wind-farm lifespan",
     "SYNTHETIC forecast generators fitted to wind and wave data - not archived as-issued NWP",
     "None. No probabilistic calibration of any event; the object is KPI sensitivity to forecast-modelling choice",
     "Wind and wave records driving three forecast generators; O&M simulation model (own)",
     "FULL TEXT READ THIS SESSION (CC BY, 14 pp). Keyword census of the extracted text: 'calibrat' 0, 'Brier' 0, 'cost-loss' 0, 'economic value' 0, 'latency' 0, 'issue time' 0; 'ensemble' occurs once and means gradient-boosting ensemble, not an ensemble forecast. It shows forecast uncertainty propagates into operability KPIs - and by omission it shows the calibration/availability/value layer is genuinely absent in this literature",
     "medium (shows forecast uncertainty matters to operability, which constrains any 'we are first to care about forecast quality' framing)",
     "Forecast generators, not an archived as-issued forecast archive; no publication latency; no calibration of a decision event (no Brier, no reliability); no economic value or cost-loss analysis; the decision object is annual availability, not a per-epoch attempt/decline decision",
     "full text read (open-access CC BY PDF retrieved this session; extracted text at sources/raw/g1x/fulltext/kolios2023_oceaneng.txt)"),

    ("azcarate2017rene", "10.1016/j.renene.2016.10.064", "3-ensemble-decisions",
     "Wind energy systems with storage: tactical and operational management using a probabilistic forecast of the energy resource",
     "Probabilistic wind-energy resource forecast",
     "None stated at metadata level",
     "Not verified (no full text retrieved)",
     "Pre-2022 anchor for the pattern 'probabilistic forecast -> operational decision rule' in an energy-operations setting; useful for showing the pattern is established outside construction, which is where the paper's contribution has to be located",
     "low",
     "Energy storage dispatch, not a weather-sensitive physical operation with a contract threshold; no window event, no schedule replay, no cost-loss value analysis, no forecast-availability audit",
     "metadata only"),

    # ---------------- Direction 4: forecast value and calibration in engineering practice ----------------
    ("hubbard2021firo", "10.1002/essoar.10505717.1", "4-forecast-value",
     "Forecast-Informed Reservoir Operations (FIRO) at Lake Mendocino: five management scenarios evaluated on 16 metrics; water-availability difference between baseline and FIRO alternatives monetised across recreation, hydropower, municipal/industrial supply, agriculture and fisheries",
     "Operational weather/streamflow forecasts incorporated into the water control plan",
     "None probabilistic; the object is a scenario-based benefit difference, not a calibrated event probability",
     "Hydrologic engineering analysis of Lake Mendocino operations; benefit transfer values for recreation, hydropower and water supply",
     "The clearest located example of MEASURING THE ECONOMIC VALUE OF FORECAST INFORMATION FOR AN ENGINEERING OPERATION outside meteorology - exactly the category the audit was asked to fill. It also shows the standard of evidence that domain reviewers expect for a value claim",
     "medium",
     "Water-resources operations, not scheduling; the value is computed from a scenario/planning analysis rather than a non-anticipative replay over archived as-issued forecasts; no Brier/reliability; no cost-loss sweep; no exposure-miss accounting. PREPRINT: peer-review status NOT verified in this audit - cite only with that label",
     "abstract+metadata only (preprint; peer-review status not verified)"),

    ("lin2026risa", "10.1111/risa.70328", "4-forecast-value",
     "Two internally controlled experiments (n=324 general public; n=122 public employees) on how probabilistic low-probability/high-impact versus deterministic high-probability/low-impact weather information changes response measures, null-event tolerance and trust",
     "Probabilistic (ensemble-derived) weather information as the treatment condition",
     "None. Outcome variables are behavioural intentions, not a calibrated probability",
     "Two controlled experiments with human participants",
     "Evidence that probabilistic information CHANGES operational decisions and that asymmetric institutional error costs (unprepared disasters penalised more than overreactions) govern how much false-alarm tolerance a decision maker will accept. That is a citable justification for reporting an exposure-miss FRONTIER with an explicit risk setting rather than a single accuracy number",
     "medium (behavioural, constrains how the risk setting should be argued)",
     "Human decision-making under probabilistic information; no engineering operation, no forecast archive, no calibration, no schedule. It motivates the frontier framing; it does not perform or replace the measurement",
     "abstract+metadata only"),

    ("sitthiyot2024mex", "10.1016/j.mex.2024.103010", "4-forecast-value",
     "Methods note: a method to improve binary forecast skill verification",
     "Generic binary forecast/observation pairs",
     "Binary event verification score (methodological proposal)",
     "Not verified (no full text retrieved); CC BY licence recorded by Crossref",
     "Candidate alternative citation for the paper's binary verification of the block-exceedance event, and a caution that binary skill scoring has its own methodological literature that a verification-literate reviewer may invoke",
     "low",
     "Generic verification methodology; no engineering operation, no decision, no value, no forecast availability. Cite only if a specific scoring choice needs defending",
     "metadata only"),

    # ---------------- Direction 5: data and benchmark resources ----------------
    ("rasp2024wb2", "10.1029/2023MS004019", "5-data-resources",
     "WeatherBench 2: a community benchmark and evaluation protocol for data-driven and physics-based global weather models (deterministic and probabilistic metrics, baselines, open evaluation code and data)",
     "Global NWP analyses and forecasts used as ground truth and baselines (IFS, GFS, ERA5)",
     "Not a calibration target; the object is benchmarked forecast skill (RMSE, ACC, CRPS, spread-skill)",
     "Open benchmark dataset and evaluation code; CC BY 4.0",
     "Gives the paper a citable, community-standard way to state where the GFS gust field sits in forecast-skill terms, instead of relying only on its own raw-threshold detector table; also demonstrates the accepted practice of the spread-skill relationship, which is the language the ensemble extension would use",
     "low (different spatial scale and object, but strengthens the methods framing)",
     "It benchmarks hemispheric/global gridded forecast fields against analyses. It says nothing about a site-level operational threshold, forecast publication latency, a decision event, or economic value - this paper's contribution begins exactly where a benchmark score stops being decision-relevant",
     "metadata only (DOI + venue + licence verified via Crossref and doi.org; not read)"),

    ("hamill2014bams", "10.1175/bams-d-12-00014.1", "5-data-resources",
     "NOAA's Second-Generation Global Medium-Range Ensemble Reforecast Dataset (GEFS Reforecast v2): dataset paper describing a long, consistent reforecast archive for ensemble applications",
     "Archived as-issued GEFS ensemble reforecasts, re-run with a frozen model version",
     "Not a calibration target; the object is the dataset and its verification",
     "GEFS Reforecast v2 archive (NOAA/PSL), served at https://www.psl.noaa.gov/forecasts/reforecast2/ (URL verified live HTTP 200 on 2026-09-15)",
     "The single most useful new DATA resource for a deeper study: a long reforecast archive is the only practical way to push past the paper's declared rare-event ceiling (19 positives at the 12 m/s mean-wind event; zero at 20 m/s) without waiting for more station years, and it supports a direct calibrated-deterministic vs ensemble comparison",
     "low",
     "A dataset and its verification. It provides no decision object, no operational threshold, no calibration of a decision event and no value analysis; it is an input to the deeper study this paper points at, not a competing result",
     "metadata only (DOI verified via Crossref + doi.org; project page fetched live)"),
]

HEADER = ["cite_key", "authors", "year", "title", "venue", "doi_or_url", "verified",
          "evidence_level", "object_and_domain", "weather_input", "calibration_target",
          "dataset_used", "why_relevant", "threat_level", "how_we_differ"]

# authors supplied explicitly (from the Crossref author records) to avoid encoding surprises
AUTHORS = {
    "augustyn2025app": "Augustyn, M.; Barski, M.",
    "li2023jmse": "Li, Q.; Fan, W.; Huang, M.; Jin, H.; Zhang, J.; Ma, J.",
    "hu2023ssci": "Hu, S.; Fang, Y.; Moehler, R.",
    "chen2019jlf": "Chen, W.; Qin, X.; Yang, Z.; Zhan, P.",
    "wang2024lnme": "Wang, X.; Zhang, H.; Liu, W.",
    "jafarpour2023marstruc": "Jafarpour Hamedani, S.; Khedmati, M. R.",
    "wu2021marstruc": "Wu, M.; Gao, Z.",
    "wang2016omae": "Wang, Y.; van Deyzen, A.; Pauw, W.; Huijsmans, R.",
    "li2025oceaneng": "Li, J.; Liang, B.; Shao, Z.; Gao, H.",
    "mohamed2024wace": "Mohamed, I.; Najafi, M. R.; Joe, P.; Brimelow, J.",
    "wu2022jmse": "Wu, S.; Sun, H.; Li, X.",
    "schulz2022mwr": "Schulz, B.; Lerch, S.",
    "coburn2022waf": "Coburn, J.; Pryor, S. C.",
    "benacek2023waf": "Benacek, P.; Farda, A.; Stepanek, P.",
    "kolios2023oceaneng": "Kolios, A.; Richmond, M.; Koukoura, S.; Yeter, B.",
    "azcarate2017rene": "Azcarate, C.; Mallor, F.; Mateo, P.",
    "hubbard2021firo": "Hubbard, T.",
    "lin2026risa": "Lin, X.; Yeo, J.",
    "sitthiyot2024mex": "Sitthiyot, T.; Holasut, K.",
    "rasp2024wb2": "Rasp, S.; Hoyer, S.; Merose, A.; Langmore, I.; Battaglia, P.; Russell, T.; Sanchez-Gonzalez, A.; Yang, V.; Carver, R.; Agrawal, S.; Chantry, M.; Ben Bouallegue, Z.; et al.",
    "hamill2014bams": "Hamill, T. M.; Bates, G. T.; Whitaker, J. S.; Murray, D. R.; Fiorino, M.; Galarneau, T. J.; Zhu, Y.; Lapenta, W.",
}

out_path = os.path.join(ROOT, "outputs/gates/G1_expansion_matrix.csv")
written = 0
with open(out_path, "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, quoting=csv.QUOTE_ALL)
    w.writerow(HEADER)
    for (ck, doi, direction, obj, win, cal, dat, why, threat, differ, ev) in ROWS:
        rec = BY_DOI.get(doi.lower())
        if rec is None:
            raise SystemExit(f"NO VERIFICATION RECORD for {doi} ({ck})")
        cr = rec["crossref"]
        assert cr.get("verified"), f"crossref not verified: {doi}"
        year = cr.get("year")
        title = cr.get("title")
        venue = cr.get("container") or cr.get("short_container") or ""
        vol, page = cr.get("volume"), cr.get("page") or cr.get("article_number")
        loc = f"{venue}"
        if vol:
            loc += f" {vol}"
        if page:
            loc += f":{page}"
        verified = (f"yes - Crossref /works/{doi} + doi.org content negotiation, both 2026-09-15; "
                    f"OpenAlex unavailable (HTTP 429) this session")
        w.writerow([ck, AUTHORS[ck], year, title, loc, f"https://doi.org/{doi}", verified,
                    ev, obj, win, cal, dat, why, threat, differ])
        written += 1

print(f"WROTE {out_path} ({written} new works, {len(HEADER)} columns)")
assert written == len(ROWS) == 21, (written, len(ROWS))
