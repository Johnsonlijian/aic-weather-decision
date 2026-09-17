"""Regenerate outputs/gates/G1_positioning_matrix.csv from verified records.

The CSV is written with csv.writer (QUOTE_ALL) because several verified DOIs contain
semicolons (legacy AMS "2.0.CO;2" / "2.3.CO;2" suffixes), which corrupt naive
comma-splitting pipelines. Run this script to rebuild the matrix reproducibly.

Sources of truth for the bibliographic fields:
  sources/raw/g1/verify_core.json, verify_b.json, verify_near.json, verify_final.json
  sources/raw/g1/titlecheck_classics.json
Assessment columns (evidence_level, what_it_does_NOT_do..., threat_level) are the
auditor's judgement and are stated explicitly below.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "gates" / "G1_positioning_matrix.csv"

COLS = [
    "cite_key", "authors", "year", "title", "venue", "doi_or_url", "verified_yes_no",
    "evidence_level", "object_and_scale", "weather_data_used", "forecast_latency_handled",
    "calibration_target", "decision_nonanticipatory_yes_no", "metrics_used",
    "what_it_does_NOT_do_that_this_project_does", "threat_level_to_our_novelty",
]

FT = "full text read (local PDF)"
ABS = "abstract+metadata only"
MET = "metadata only"

R: list[dict] = []


def add(**kw):
    assert set(kw) == set(COLS), set(COLS) ^ set(kw)
    R.append(kw)


# ---------------------------------------------------------------- construction / weather scheduling
add(
    cite_key="kerkhove2017", authors="Kerkhove, L.-P.; Vanhoucke, M.", year=2017,
    title="Optimised scheduling for weather sensitive offshore construction projects",
    venue="Omega", doi_or_url="https://doi.org/10.1016/j.omega.2016.01.011",
    verified_yes_no="yes",
    evidence_level="abstract+metadata only (final journal version); author doctoral thesis chapters 7-8 read from local PDF sources/raw/kerkhove_2016_thesis.pdf",
    object_and_scale="resource-constrained offshore construction project; weather-sensitive activities; real case parameters",
    weather_data_used="simulated joint wind-wave states (transition probabilities + Weibull persistence, 4-hour step); NOT an archived NWP forecast",
    forecast_latency_handled="no",
    calibration_target="none",
    decision_nonanticipatory_yes_no="no (optimises pre-set activity resource-release times, then compares via simulation with common random numbers)",
    metrics_used="expected net present value; schedule; common-random-number variance reduction",
    what_it_does_NOT_do_that_this_project_does="use real archived as-issued NWP runs; distinguish start from continuation thresholds; report unsafe-exceedance exposure and regret against perfect foresight",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="zhou2021", authors="Zhou, Y.; Miao, J.; Yan, B.; Zhang, Z.", year=2021,
    title="Stochastic resource-constrained project scheduling problem with time varying weather conditions and an improved estimation of distribution algorithm",
    venue="Computers & Industrial Engineering",
    doi_or_url="https://doi.org/10.1016/j.cie.2021.107322", verified_yes_no="yes",
    evidence_level=ABS,
    object_and_scale="stochastic RCPSP on benchmark-style instances; time-varying weather affecting activity durations",
    weather_data_used="parametric time-varying weather process, not an as-issued forecast archive",
    forecast_latency_handled="no", calibration_target="none",
    decision_nonanticipatory_yes_no="no (offline stochastic optimisation)",
    metrics_used="expected makespan; EDA convergence",
    what_it_does_NOT_do_that_this_project_does="use an actual archived forecast trajectory; model the information set available at decision time; calibrate the decision-threshold event",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="ballesteros2017",
    authors="Ballesteros-Pérez, P.; Rojas-Céspedes, Y. A.; Hughes, W.; Kabiri, S.; Pellicer, E.; Mora-Melià, D.; del Campo-Hitschfeld, M. L.",
    year=2017,
    title="Weather-wise: A weather-aware planning tool for improving construction productivity and dealing with claims",
    venue="Automation in Construction", doi_or_url="https://doi.org/10.1016/j.autcon.2017.08.022",
    verified_yes_no="yes",
    evidence_level="author-version full text read (sources/raw/weatherwise_author.pdf pp.4-16, 31-39); final journal version metadata only",
    object_and_scale="building construction planning; two Spanish locations; activity precedence and durations",
    weather_data_used="historical weather records driving a stochastic weather-productivity-delay model",
    forecast_latency_handled="no", calibration_target="none",
    decision_nonanticipatory_yes_no="no",
    metrics_used="project duration increase when weather is ignored (reported 5-20%)",
    what_it_does_NOT_do_that_this_project_does="feed an as-issued NWP forecast into the decision; treat forecast-to-observation calibration as the object of study; run a non-anticipative online replay",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="ballesteros2018", authors="Ballesteros-Pérez, P.; Smith, S. T.; Lloyd-Papworth, J. G.",
    year=2018,
    title="Incorporating the effect of weather in construction scheduling and management with sine wave curves: application in the United Kingdom",
    venue="Construction Management and Economics",
    doi_or_url="https://doi.org/10.1080/01446193.2018.1478109", verified_yes_no="yes",
    evidence_level=MET,
    object_and_scale="construction scheduling method with a UK case application",
    weather_data_used="seasonal sine-wave weather model fitted to historical climate records",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="activity duration adjustment; schedule comparison",
    what_it_does_NOT_do_that_this_project_does="use forecast trajectories rather than climatological envelopes; evaluate downstream decisions under uncertainty",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="shahin2011", authors="Shahin, A.; AbouRizk, S. M.; Mohamed, Y.", year=2011,
    title="Modeling Weather-Sensitive Construction Activity Using Simulation",
    venue="Journal of Construction Engineering and Management",
    doi_or_url="https://doi.org/10.1061/(ASCE)CO.1943-7862.0000258", verified_yes_no="yes",
    evidence_level=ABS,
    object_and_scale="general weather-sensitive construction activity simulation",
    weather_data_used="historical weather records driving simulation",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="activity duration distributions; productivity loss",
    what_it_does_NOT_do_that_this_project_does="use forecast trajectories with an explicit as-issued information set; decision-aligned calibration",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="shahin2014", authors="Shahin, A.; AbouRizk, S. M.; Mohamed, Y.; Fernando, S.", year=2014,
    title="Simulation modeling of weather-sensitive tunnelling construction activities subject to cold weather",
    venue="Canadian Journal of Civil Engineering",
    doi_or_url="https://doi.org/10.1139/cjce-2013-0087", verified_yes_no="yes",
    evidence_level=MET,
    object_and_scale="weather-sensitive tunnelling with cold-weather stopping rules",
    weather_data_used="historical cold-weather records",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="production rate; stoppage days",
    what_it_does_NOT_do_that_this_project_does="forecast-conditioned decisions with calibration; multi-activity resource-constrained scheduling",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="ahuja1985", authors="Ahuja, H. N.; Nandakumar, V.", year=1985,
    title="Simulation Model to Forecast Project Completion Time",
    venue="Journal of Construction Engineering and Management",
    doi_or_url="https://doi.org/10.1061/(ASCE)0733-9364(1985)111:4(325)", verified_yes_no="yes",
    evidence_level=MET,
    object_and_scale="construction project completion-time distribution",
    weather_data_used="stochastic activity durations (weather one source of variability among others)",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="completion-time distribution; probability of meeting deadline",
    what_it_does_NOT_do_that_this_project_does="use an actual forecast product as the decision input; separate forecast value from generic duration variability",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="yates1993", authors="Yates, J. K.", year=1993,
    title="Construction Decision Support System for Delay Analysis",
    venue="Journal of Construction Engineering and Management",
    doi_or_url="https://doi.org/10.1061/(ASCE)0733-9364(1993)119:2(226)", verified_yes_no="yes",
    evidence_level=MET,
    object_and_scale="construction delay analysis and claim decision support",
    weather_data_used="weather records used as delay evidence",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="delay attribution; decision-support system design",
    what_it_does_NOT_do_that_this_project_does="support prospective forecast-informed decisions rather than retrospective delay attribution",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="schuldt2021", authors="Schuldt, S. J.; Nicholson, M. R.; Adams, Y. A.; Delorit, J. D.",
    year=2021,
    title="Weather-Related Construction Delays in a Changing Climate: A Systematic State-of-the-Art Review",
    venue="Sustainability", doi_or_url="https://doi.org/10.3390/su13052861", verified_yes_no="yes",
    evidence_level=ABS,
    object_and_scale="systematic review of weather-related construction delay research",
    weather_data_used="review-level (no primary dataset)",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="review synthesis",
    what_it_does_NOT_do_that_this_project_does="provide any decision-analytic forecast-value method; the review documents that this gap exists",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="peng2023", authors="Peng, W.; Lin, X.; Li, H.", year=2023,
    title="Critical chain based Proactive-Reactive scheduling for Resource-Constrained project scheduling under uncertainty",
    venue="Expert Systems with Applications", doi_or_url="https://doi.org/10.1016/j.eswa.2022.119188",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="resource-constrained project scheduling under general uncertainty",
    weather_data_used="general uncertainty, not weather-specific and not forecast-specific",
    forecast_latency_handled="no", calibration_target="none",
    decision_nonanticipatory_yes_no="yes (proactive-reactive policy reacts to realised state)",
    metrics_used="makespan; schedule stability; buffer performance",
    what_it_does_NOT_do_that_this_project_does="use a weather forecast as the information source, calibrate it at the operation threshold, and add unsafe-exceedance plus regret metrics",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="mawlana2026", authors="Mawlana, M.; Hammad, A.", year=2026,
    title="Enhancing Construction Simulation Optimization Performance Through Variance Reduction Techniques",
    venue="Modelling", doi_or_url="https://doi.org/10.3390/modelling7040137", verified_yes_no="yes",
    evidence_level=MET, object_and_scale="construction simulation-optimisation", weather_data_used="not weather-specific",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="simulation variance reduction; optimisation efficiency",
    what_it_does_NOT_do_that_this_project_does="apply variance-reduction discipline specifically to paired weather-policy comparisons with regret",
    threat_level_to_our_novelty="low",
)

# ---------------------------------------------------------------- offshore / weather windows
add(
    cite_key="doskeland2023", authors="Døskeland, Ø.; Gudmestad, O. T.; Moen, P.", year=2023,
    title="Use of response forecasting in decision making for weather sensitive offshore construction work",
    venue="Ocean Engineering", doi_or_url="https://doi.org/10.1016/j.oceaneng.2023.115896",
    verified_yes_no="yes",
    evidence_level=ABS + " (OpenAlex W4387165254; CC-BY full text located at UiS Brage handle 11250/3095815 but that host did not resolve from this network)",
    object_and_scale="offshore installation contractor perspective; pipelay case study; operational decision-support service",
    weather_data_used="vessel response forecasting (forecast-to-response modelling), not only atmospheric forecast fields",
    forecast_latency_handled="unclear from abstract (the service is built around changing forecast information)",
    calibration_target="none stated in abstract",
    decision_nonanticipatory_yes_no="unclear from abstract",
    metrics_used="qualitative reliability and efficiency of weather-sensitive operations; case-study impact on decision making",
    what_it_does_NOT_do_that_this_project_does="(as far as the abstract shows) non-anticipative replay with an archived latency-audited NWP product; decision-aligned threshold calibration; explicit regret and unsafe-exceedance accounting",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="jafarpour2024", authors="Jafarpour Hamedani, S.; Khedmati, M. R.", year=2024,
    title="Optimized planning for weather-sensitive offshore construction operations - An application to float-over installation of super-heavy offshore topsides",
    venue="Ocean Engineering", doi_or_url="https://doi.org/10.1016/j.oceaneng.2024.117027",
    verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="single mega-operation: float-over installation of super-heavy offshore topsides",
    weather_data_used="metocean conditions with operational limits; weather-window analysis",
    forecast_latency_handled="unclear", calibration_target="none", decision_nonanticipatory_yes_no="unclear",
    metrics_used="allowable sea states; operation duration; planning improvement",
    what_it_does_NOT_do_that_this_project_does="generalise to a multi-activity resource-constrained network; use an as-issued NWP archive; quantify decision value against blind and perfect-foresight baselines",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="hong2026", authors="Hong, S.; Zhang, H.; Halse, K. H.", year=2026,
    title="Persistence-based operability for time-constrained onsite installation of floating offshore wind turbines: Poisson interval framework",
    venue="Marine Structures", doi_or_url="https://doi.org/10.1016/j.marstruc.2026.104144",
    verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="time-constrained onsite installation of floating offshore wind turbines; interval-based operability",
    weather_data_used="persistence statistics of metocean conditions; Poisson interval framework",
    forecast_latency_handled="unclear", calibration_target="none",
    decision_nonanticipatory_yes_no="no (probabilistic assessment, not a rolling decision policy)",
    metrics_used="operability; interval/persistence statistics; per-turbine installation time",
    what_it_does_NOT_do_that_this_project_does="couple operability statistics to an archived forecast's information set and to a rolling non-anticipative controller; report schedule delay, idle time and exceedance exposure together",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="tinoco2019", authors="Tinoco, F.; Ting, K. C.; Chavan, K.", year=2019,
    title="The Use of Ensemble Forecast in Defining Offshore Installation Operability: A Case Study on Umbilical Shore Float-In Operations",
    venue="ASME OMAE 2019 - Volume 1: Offshore Technology; Offshore Geotechnics",
    doi_or_url="https://doi.org/10.1115/omae2019-96137", verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="single offshore installation operation (umbilical shore float-in)",
    weather_data_used="ensemble (probabilistic) forecast used to define operability windows",
    forecast_latency_handled="yes (the ensemble forecast is itself the decision input)",
    calibration_target="operability threshold",
    decision_nonanticipatory_yes_no="unclear",
    metrics_used="operability windows; ensemble-based downtime estimate",
    what_it_does_NOT_do_that_this_project_does="run a multi-activity scheduling replay with competing resources; separate calibration quality from scheduling value; report regret",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="kikuchi2016", authors="Kikuchi, Y.; Ishihara, T.", year=2016,
    title="Assessment of weather downtime for the construction of offshore wind farm by using wind and wave simulations",
    venue="Journal of Physics: Conference Series",
    doi_or_url="https://doi.org/10.1088/1742-6596/753/9/092016", verified_yes_no="yes",
    evidence_level=MET, object_and_scale="offshore wind farm construction; downtime estimation",
    weather_data_used="mesoscale wind and wave simulation (hindcast-style)",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="weather downtime hours; workable-day statistics",
    what_it_does_NOT_do_that_this_project_does="treat the forecast as a decision input under latency; calibrate the threshold event; measure scheduling regret",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="ursavas2017", authors="Ursavas, E.", year=2017,
    title="A benders decomposition approach for solving the offshore wind farm installation planning at the North Sea",
    venue="European Journal of Operational Research",
    doi_or_url="https://doi.org/10.1016/j.ejor.2016.08.057", verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="offshore wind farm installation planning and vessel logistics, North Sea",
    weather_data_used="stochastic weather scenarios; weather windows for installation",
    forecast_latency_handled="unclear", calibration_target="none", decision_nonanticipatory_yes_no="unclear",
    metrics_used="installation cost; vessel utilisation; decomposition performance",
    what_it_does_NOT_do_that_this_project_does="use an as-issued archived NWP forecast with an explicit information set; calibrate at the operational threshold; report unsafe exceedance and regret",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="qu2026", authors="Qu, S.; Yu, C.; Zhou, Y.; Hou, Y.; Wang, J.; Li, F.", year=2026,
    title="Optimization of Collaborative Vessel Scheduling for Offshore Wind Farm Installation Under Weather Uncertainty",
    venue="Journal of Marine Science and Engineering",
    doi_or_url="https://doi.org/10.3390/jmse14020223", verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="offshore wind farm installation; collaborative multi-vessel scheduling",
    weather_data_used="weather uncertainty scenarios",
    forecast_latency_handled="unclear", calibration_target="none", decision_nonanticipatory_yes_no="unclear",
    metrics_used="installation cost/makespan; collaborative scheduling gain",
    what_it_does_NOT_do_that_this_project_does="use real archived forecast runs with publication latency; report calibration quality and decision value; distinguish initiation from continuation rules",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="hadjoudj2023", authors="Hadjoudj, Y.; Pandit, R. K.", year=2023,
    title="Improving O&M decision tools for offshore wind farm vessel routing by incorporating weather uncertainty",
    venue="IET Renewable Power Generation", doi_or_url="https://doi.org/10.1049/rpg2.12689",
    verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="offshore wind O&M vessel routing", weather_data_used="weather uncertainty in the forecast",
    forecast_latency_handled="unclear", calibration_target="none", decision_nonanticipatory_yes_no="unclear",
    metrics_used="routing cost; vessel downtime; accessibility",
    what_it_does_NOT_do_that_this_project_does="target construction/installation scheduling with continuous-operation contracts; align calibration to the decision threshold",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="dawid2018", authors="Dawid, R.; McMillan, D.; Revie, M.", year=2018,
    title="Decision Support Tool for Offshore Wind Farm Vessel Routing under Uncertainty",
    venue="Energies", doi_or_url="https://doi.org/10.3390/en11092190", verified_yes_no="yes",
    evidence_level=ABS, object_and_scale="offshore wind farm vessel routing decisions",
    weather_data_used="weather/accessibility uncertainty",
    forecast_latency_handled="unclear", calibration_target="none", decision_nonanticipatory_yes_no="unclear",
    metrics_used="cost; accessibility; decision-support tool evaluation",
    what_it_does_NOT_do_that_this_project_does="address installation scheduling under a continuous-operation contract and as-issued forecast latency",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="peng2021", authors="Peng, S.; Rippel, D.; Becker, M.; Szczerbicka, H.", year=2021,
    title="Scheduling of Offshore Wind Farm Installation using Simulated Annealing",
    venue="IFAC-PapersOnLine", doi_or_url="https://doi.org/10.1016/j.ifacol.2021.08.037",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="offshore wind farm installation scheduling",
    weather_data_used="weather windows as scheduling constraints",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="makespan; metaheuristic performance",
    what_it_does_NOT_do_that_this_project_does="model the forecast information set; calibrate forecast-to-observation at the decision threshold; evaluate decision value",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="li2016", authors="Li, Q.; Wang, H.", year=2016,
    title="Two-stage simulation optimization for optimal development of offshore wind farm under wind uncertainty",
    venue="2016 Winter Simulation Conference (WSC)",
    doi_or_url="https://doi.org/10.1109/WSC.2016.7822324", verified_yes_no="yes", evidence_level=MET,
    object_and_scale="offshore wind farm development; capacity/layout decision",
    weather_data_used="wind uncertainty", forecast_latency_handled="no", calibration_target="none",
    decision_nonanticipatory_yes_no="no", metrics_used="expected cost; simulation-optimisation performance",
    what_it_does_NOT_do_that_this_project_does="focus on operational scheduling decisions with archived forecast dynamics",
    threat_level_to_our_novelty="low",
)

# ---------------------------------------------------------------- decision-analytic forecast value
add(
    cite_key="mylne2002", authors="Mylne, K. R.", year=2002,
    title="Decision-making from probability forecasts based on forecast value",
    venue="Meteorological Applications", doi_or_url="https://doi.org/10.1017/S1350482702003043",
    verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="meteorological decision-making for a generic user decision problem",
    weather_data_used="probability forecasts", forecast_latency_handled="no",
    calibration_target="decision threshold (value-based decision rule)",
    decision_nonanticipatory_yes_no="no (single-period expected-value decision rule)",
    metrics_used="relative economic value; value score",
    what_it_does_NOT_do_that_this_project_does="apply the value framework to a multi-activity construction schedule with resource coupling and continuation constraints",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="richardson2000", authors="Richardson, D. S.", year=2000,
    title="Skill and relative economic value of the ECMWF ensemble prediction system",
    venue="Quarterly Journal of the Royal Meteorological Society",
    doi_or_url="https://doi.org/10.1002/qj.49712656313", verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="ensemble prediction system evaluation for a generic cost-loss user",
    weather_data_used="ECMWF ensemble forecasts", forecast_latency_handled="no",
    calibration_target="decision threshold (cost-loss ratio sweep)",
    decision_nonanticipatory_yes_no="no",
    metrics_used="relative economic value; ROC; cost-loss curves",
    what_it_does_NOT_do_that_this_project_does="map the cost-loss value framework onto engineering operation contracts and schedule-level outcomes",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="zhu2002", authors="Zhu, Y.; Toth, Z.; Wobus, R.; Richardson, D.; Mylne, K.", year=2002,
    title="The Economic Value Of Ensemble-Based Weather Forecasts",
    venue="Bulletin of the American Meteorological Society",
    doi_or_url="https://doi.org/10.1175/1520-0477(2002)083<0073:TEVOEB>2.3.CO;2",
    verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="ensemble forecast value across several user applications",
    weather_data_used="ensemble forecasts", forecast_latency_handled="no",
    calibration_target="decision threshold (cost-loss)", decision_nonanticipatory_yes_no="no",
    metrics_used="relative economic value",
    what_it_does_NOT_do_that_this_project_does="extend decision-analytic forecast value to a scheduling decision with resource coupling",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="murphy1977", authors="Murphy, A. H.", year=1977,
    title="The Value of Climatological, Categorical and Probabilistic Forecasts in the Cost-Loss Ratio Situation",
    venue="Monthly Weather Review",
    doi_or_url="https://doi.org/10.1175/1520-0493(1977)105<0803:TVOCCA>2.0.CO;2",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="prototype cost-loss decision problem",
    weather_data_used="probability and categorical forecasts", forecast_latency_handled="no",
    calibration_target="decision threshold (cost-loss)", decision_nonanticipatory_yes_no="no",
    metrics_used="expected expense; value of forecasts",
    what_it_does_NOT_do_that_this_project_does="ESTABLISHES the origin of the finding that better forecast quality need not imply better decisions; our novelty claim must not rest on that insight",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="murphy1990", authors="Murphy, A. H.; Ye, Q.", year=1990,
    title="Optimal Decision Making and the Value of Information in a Time-Dependent Version of the Cost-Loss Ratio Situation",
    venue="Monthly Weather Review",
    doi_or_url="https://doi.org/10.1175/1520-0493(1990)118<0939:ODMATV>2.0.CO;2",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="multi-period cost-loss decision problem",
    weather_data_used="sequential forecasts", forecast_latency_handled="no",
    calibration_target="decision threshold (time-dependent cost-loss)",
    decision_nonanticipatory_yes_no="yes (sequential decision with information updating)",
    metrics_used="expected expense; value of information",
    what_it_does_NOT_do_that_this_project_does="apply sequential decision-value analysis to a construction schedule rather than a repeated single-asset protection problem",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="murphy1985a", authors="Murphy, A. H.", year=1985,
    title="Decision Making and the Value of Forecasts in a Generalized Model of the Cost-Loss Ratio Situation",
    venue="Monthly Weather Review",
    doi_or_url="https://doi.org/10.1175/1520-0493(1985)113<0362:DMATVO>2.0.CO;2",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="generalised cost-loss decision model", weather_data_used="probability forecasts",
    forecast_latency_handled="no", calibration_target="decision threshold (generalised cost-loss)",
    decision_nonanticipatory_yes_no="no", metrics_used="value of forecasts; decision-model sensitivity",
    what_it_does_NOT_do_that_this_project_does="specialise to an engineering operation contract with an uninterrupted-duration requirement",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="murphy1985b", authors="Murphy, A. H.; Katz, R. W.; Winkler, R. L.; Hsu, W. R.", year=1985,
    title="Repetitive Decision Making and the Value of Forecasts in the Cost-Loss Ratio Situation: A Dynamic Model",
    venue="Monthly Weather Review",
    doi_or_url="https://doi.org/10.1175/1520-0493(1985)113<0801:RDMATV>2.0.CO;2",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="repeated cost-loss decisions over time",
    weather_data_used="forecasts with temporal dependence", forecast_latency_handled="no",
    calibration_target="decision threshold (dynamic cost-loss)",
    decision_nonanticipatory_yes_no="yes (dynamic repeated decision)",
    metrics_used="expected expense over repetitions",
    what_it_does_NOT_do_that_this_project_does="transfer dynamic decision-value analysis to resource-coupled construction scheduling",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="wilks2001", authors="Wilks, D. S.", year=2001,
    title="A skill score based on economic value for probability forecasts",
    venue="Meteorological Applications", doi_or_url="https://doi.org/10.1017/S1350482701002092",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="verification methodology: economic value skill score",
    weather_data_used="probability forecasts", forecast_latency_handled="no",
    calibration_target="decision threshold (economic value score)", decision_nonanticipatory_yes_no="no",
    metrics_used="economic value skill score",
    what_it_does_NOT_do_that_this_project_does="use an engineering decision loss (schedule delay, idle time, unsafe exceedance) rather than a two-state expense matrix",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="briggs2005", authors="Briggs, W.", year=2005,
    title="A General Method of Incorporating Forecast Cost and Loss in Value Scores",
    venue="Monthly Weather Review", doi_or_url="https://doi.org/10.1175/MWR3031.1",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="verification methodology: cost and loss in value scores",
    weather_data_used="probability forecasts", forecast_latency_handled="no",
    calibration_target="decision threshold (generalised value score)",
    decision_nonanticipatory_yes_no="no", metrics_used="value score",
    what_it_does_NOT_do_that_this_project_does="replace the binary expense model with a scheduling loss function and resource constraints",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="buizza2001", authors="Buizza, R.", year=2001,
    title="Accuracy and Potential Economic Value of Categorical and Probabilistic Forecasts of Discrete Events",
    venue="Monthly Weather Review",
    doi_or_url="https://doi.org/10.1175/1520-0493(2001)129<2329:AAPEVO>2.0.CO;2",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="verification and value of discrete-event forecasts",
    weather_data_used="ensemble/categorical forecasts", forecast_latency_handled="no",
    calibration_target="decision threshold", decision_nonanticipatory_yes_no="no",
    metrics_used="accuracy; potential economic value",
    what_it_does_NOT_do_that_this_project_does="apply the accuracy-versus-value distinction to a construction operation threshold on real archived forecast runs",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="wilks1997", authors="Wilks, D. S.", year=1997,
    title="Forecast value: prescriptive decision studies",
    venue="In: Economic Value of Weather and Climate Forecasts (Cambridge University Press)",
    doi_or_url="https://doi.org/10.1017/CBO9780511608278.005", verified_yes_no="yes", evidence_level=MET,
    object_and_scale="book chapter: prescriptive decision-analytic forecast value",
    weather_data_used="generic", forecast_latency_handled="no", calibration_target="decision threshold",
    decision_nonanticipatory_yes_no="no", metrics_used="expected value of forecast information",
    what_it_does_NOT_do_that_this_project_does="domain specialisation to construction scheduling",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="katzmurphy1997", authors="Katz, R. W.; Murphy, A. H.", year=1997,
    title="Forecast value: prototype decision-making models",
    venue="In: Economic Value of Weather and Climate Forecasts (Cambridge University Press)",
    doi_or_url="https://doi.org/10.1017/CBO9780511608278.007", verified_yes_no="yes", evidence_level=MET,
    object_and_scale="book chapter: prototype decision models for forecast value",
    weather_data_used="generic", forecast_latency_handled="no", calibration_target="decision threshold",
    decision_nonanticipatory_yes_no="no", metrics_used="expected value; prototype model comparison",
    what_it_does_NOT_do_that_this_project_does="domain specialisation plus a real archived forecast product",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="jewson2020", authors="Jewson, S.; Scher, S.; Messori, G.", year=2020,
    title="Decide Now or Wait for the Next Forecast? A Decision Framework Based on an Extension of the Cost-Loss Model",
    venue="Preprint (MDPI Preprints) - peer-review status not verified",
    doi_or_url="https://doi.org/10.20944/preprints202002.0217.v2", verified_yes_no="yes",
    evidence_level=ABS + " (preprint; not confirmed as peer-reviewed)",
    object_and_scale="meteorology: whether to decide now or wait for a better forecast",
    weather_data_used="forecast updates",
    forecast_latency_handled="yes at the conceptual level (the entire point is deferral until the next forecast arrives)",
    calibration_target="decision threshold",
    decision_nonanticipatory_yes_no="yes (sequential decision with forecast availability)",
    metrics_used="expected cost of deciding now vs waiting",
    what_it_does_NOT_do_that_this_project_does="handle forecast timing with an archived latency-audited NWP product and a resource-constrained engineering schedule",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="shen2024", authors="Shen, D.; Zuo, Z.; Zhang, X.; Zhao, X.", year=2024,
    title="The impact of weather forecast accuracy on the economic value of weather-sensitive industries",
    venue="Preprint (Research Square) - peer-review status not verified",
    doi_or_url="https://doi.org/10.21203/rs.3.rs-3306307/v1", verified_yes_no="yes",
    evidence_level=ABS + " (preprint; not confirmed as peer-reviewed)",
    object_and_scale="weather-sensitive industries; forecast accuracy and economic value",
    weather_data_used="forecast accuracy metrics", forecast_latency_handled="no",
    calibration_target="economic value", decision_nonanticipatory_yes_no="no",
    metrics_used="economic value of forecast accuracy",
    what_it_does_NOT_do_that_this_project_does="operate at the level of an individual construction operation's scheduling decision",
    threat_level_to_our_novelty="low",
)

# ---------------------------------------------------------------- verification / calibration
add(
    cite_key="thompson1952", authors="Thompson, J. C.", year=1952,
    title="On the Operational Deficiences in Categorical Weather Forecasts",
    venue="Bulletin of the American Meteorological Society",
    doi_or_url="https://doi.org/10.1175/1520-0477-33.6.223", verified_yes_no="yes", evidence_level=MET,
    object_and_scale="meteorology: deficiencies of categorical forecasts",
    weather_data_used="deterministic categorical forecasts", forecast_latency_handled="no",
    calibration_target="decision-relevant categorical outcome", decision_nonanticipatory_yes_no="no",
    metrics_used="operational deficiency measures",
    what_it_does_NOT_do_that_this_project_does="nothing; it defines the decision-oriented verification tradition this project sits inside, so threshold-focused verification is NOT a new concept",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="brier1950", authors="Brier, G. W.", year=1950,
    title="Verification of Forecasts Expressed in Terms of Probability",
    venue="Monthly Weather Review",
    doi_or_url="https://doi.org/10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="meteorology: probability forecast verification",
    weather_data_used="probability forecasts", forecast_latency_handled="no", calibration_target="none",
    decision_nonanticipatory_yes_no="no", metrics_used="Brier score",
    what_it_does_NOT_do_that_this_project_does="nothing; our use of the Brier score is standard methodology and cannot be claimed as a contribution",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="murphy1993", authors="Murphy, A. H.", year=1993,
    title="What Is a Good Forecast? An Essay on the Nature of Goodness in Weather Forecasting",
    venue="Weather and Forecasting",
    doi_or_url="https://doi.org/10.1175/1520-0434(1993)008<0281:WIAGFA>2.0.CO;2",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="meteorology: quality-value framework", weather_data_used="forecast systems",
    forecast_latency_handled="no", calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="conceptual quality/value framework",
    what_it_does_NOT_do_that_this_project_does="nothing; this is the canonical statement that forecast quality and forecast value are distinct, so 'value of forecast' framing is not new",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="gneiting2007", authors="Gneiting, T.; Balabdaoui, F.; Raftery, A. E.", year=2007,
    title="Probabilistic Forecasts, Calibration and Sharpness",
    venue="Journal of the Royal Statistical Society Series B: Statistical Methodology",
    doi_or_url="https://doi.org/10.1111/j.1467-9868.2007.00587.x", verified_yes_no="yes",
    evidence_level=ABS,
    object_and_scale="statistics/meteorology: calibration and sharpness theory",
    weather_data_used="probability forecasts", forecast_latency_handled="no", calibration_target="none",
    decision_nonanticipatory_yes_no="no", metrics_used="calibration; sharpness; proper scoring rules",
    what_it_does_NOT_do_that_this_project_does="nothing; our calibration diagnostics are applications of this theory, not new theory",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="gneiting2005", authors="Gneiting, T.; Raftery, A. E.; Westveld, A. H.; Goldman, T.", year=2005,
    title="Calibrated Probabilistic Forecasting Using Ensemble Model Output Statistics and Minimum CRPS Estimation",
    venue="Monthly Weather Review", doi_or_url="https://doi.org/10.1175/MWR2904.1",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="statistical post-processing of forecast ensembles",
    weather_data_used="ensemble forecasts", forecast_latency_handled="no", calibration_target="none",
    decision_nonanticipatory_yes_no="no", metrics_used="CRPS; calibration diagnostics",
    what_it_does_NOT_do_that_this_project_does="nothing directly; note that our deliberately simple marginal correction is weaker than EMOS and must not be presented as a new calibration method",
    threat_level_to_our_novelty="low",
)
add(
    cite_key="ebert2013", authors="Ebert, E.; Wilson, L.; Weigel, A.; Mittermaier, M.; Nurmi, P.; Gill, P.; Göber, M.; Joslyn, S.; Brown, B.; Fowler, T.; Watkins, A.",
    year=2013, title="Progress and challenges in forecast verification",
    venue="Meteorological Applications", doi_or_url="https://doi.org/10.1002/met.1392",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="meteorology: state of the art in forecast verification",
    weather_data_used="generic", forecast_latency_handled="no", calibration_target="none",
    decision_nonanticipatory_yes_no="no", metrics_used="review",
    what_it_does_NOT_do_that_this_project_does="nothing; it shows user-oriented and decision-oriented verification is an established field that our framing must cite rather than claim to open",
    threat_level_to_our_novelty="medium",
)

# ---------------------------------------------------------------- decision-focused learning
add(
    cite_key="elmachtoub2022", authors="Elmachtoub, A. N.; Grigas, P.", year=2022,
    title='Smart "Predict, then Optimize"', venue="Management Science",
    doi_or_url="https://doi.org/10.1287/mnsc.2020.3922", verified_yes_no="yes", evidence_level=ABS,
    object_and_scale="operations research / machine learning: decision-focused prediction",
    weather_data_used="not weather-specific", forecast_latency_handled="no",
    calibration_target="downstream decision loss",
    decision_nonanticipatory_yes_no="yes (decision-theoretic framing)",
    metrics_used="decision loss; SPO+ regret bound",
    what_it_does_NOT_do_that_this_project_does="apply the framework to a weather-to-schedule mapping with real archived forecasts; the conceptual claim that prediction accuracy is not decision value is already established here",
    threat_level_to_our_novelty="high",
)
add(
    cite_key="bertsimas2020", authors="Bertsimas, D.; Kallus, N.", year=2020,
    title="From Predictive to Prescriptive Analytics", venue="Management Science",
    doi_or_url="https://doi.org/10.1287/mnsc.2018.3253", verified_yes_no="yes", evidence_level=MET,
    object_and_scale="operations research: predictive-to-prescriptive pipeline",
    weather_data_used="not weather-specific", forecast_latency_handled="no",
    calibration_target="downstream decision cost", decision_nonanticipatory_yes_no="no",
    metrics_used="prescriptive cost; comparison to predict-then-optimise",
    what_it_does_NOT_do_that_this_project_does="domain application only; the framework itself is prior art",
    threat_level_to_our_novelty="medium",
)
add(
    cite_key="ban2019", authors="Ban, G.-Y.; Rudin, C.", year=2019,
    title="The Big Data Newsvendor: Practical Insights from Machine Learning",
    venue="Operations Research", doi_or_url="https://doi.org/10.1287/opre.2018.1757",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="operations research: machine learning for a decision problem",
    weather_data_used="not weather-specific", forecast_latency_handled="no",
    calibration_target="downstream decision cost", decision_nonanticipatory_yes_no="no",
    metrics_used="newsvendor cost; feature-based policies",
    what_it_does_NOT_do_that_this_project_does="domain application only",
    threat_level_to_our_novelty="low",
)

# ---------------------------------------------------------------- data provenance
add(
    cite_key="hersbach2020", authors="Hersbach, H.; Bell, B.; Berrisford, P.; Hirahara, S.; Horányi, A.; Muñoz-Sabater, J.; Nicolas, J.; Peubey, C.; Radu, R.; Schepers, D.; Simmons, A.; Soci, C.; Abdalla, S.; Abellan, X.; Balsamo, G.; Bechtold, P.; Biavati, G.; Bidlot, J.; Bonavita, M.; De Chiara, G.; Dahlgren, P.; Dee, D.; Diamantakis, M.; Dragani, R.; Flemming, J.; Forbes, R.; Fuentes, M.; Geer, A.; Haimberger, L.; Healy, S.; Hogan, R. J.; Hólm, E.; Janisková, M.; Keeley, S.; Laloyaux, P.; Lopez, P.; Lupu, C.; Radnoti, G.; de Rosnay, P.; Rozum, I.; Vamborg, F.; Villaume, S.; Thépaut, J.-N.",
    year=2020, title="The ERA5 global reanalysis",
    venue="Quarterly Journal of the Royal Meteorological Society", doi_or_url="https://doi.org/10.1002/qj.3803",
    verified_yes_no="yes", evidence_level=MET,
    object_and_scale="global atmospheric reanalysis dataset",
    weather_data_used="ERA5 reanalysis", forecast_latency_handled="no (a reanalysis is not an as-issued forecast)",
    calibration_target="none", decision_nonanticipatory_yes_no="no",
    metrics_used="dataset description and evaluation",
    what_it_does_NOT_do_that_this_project_does="provide as-issued forecast runs; this citation supports the point that reanalysis evidence cannot substitute for forecast-vintage evidence",
    threat_level_to_our_novelty="low",
)


DROP = ['ahuja1985', 'ban2019', 'bertsimas2020', 'brier1950', 'briggs2005', 'dawid2018', 'gneiting2005', 'hadjoudj2023', 'katzmurphy1997', 'kikuchi2016', 'li2016', 'mawlana2026', 'murphy1985a', 'peng2021', 'schuldt2021', 'shahin2014', 'shen2024', 'wilks1997', 'wilks2001', 'yates1993']


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    global R
    R = [r for r in R if r["cite_key"] not in DROP]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_ALL,
                           lineterminator="\r\n")
        w.writeheader()
        w.writerows(R)
    print(f"wrote {OUT} with {len(R)} works")
    # validate
    import pandas as pd

    df = pd.read_csv(OUT, encoding="utf-8")
    assert list(df.columns) == COLS, list(df.columns)
    assert len(df) == len(R)
    assert df["cite_key"].is_unique
    assert set(df["verified_yes_no"]) == {"yes"}
    assert set(df["threat_level_to_our_novelty"]) <= {"high", "medium", "low"}
    print("VALIDATION OK")
    print(df["threat_level_to_our_novelty"].value_counts().to_dict())
    print(df["evidence_level"].str.slice(0, 22).value_counts().to_dict())


if __name__ == "__main__":
    main()
