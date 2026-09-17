#!/usr/bin/env python
"""Write sources/raw/g1x/verified_expansion.json: every DOI verified during the
G1 five-direction expansion, with all three verification routes, URLs, date and result.

This is the machine-readable audit trail behind outputs/gates/G1_expansion_matrix.csv.
It deliberately INCLUDES the DOIs that failed verification, so the discarded
memory-constructed identifiers stay on the record.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources/raw/g1x")

NOTES = {
    "10.3390/app15094683": ("augustyn2025app", True, "1-crane-wind",
        "STRONGEST NEW THREAT. Overturning-critical wind speed 35-53 m/s for a top-slewing tower crane; "
        "2-5x above every documented in-service limit (9-20 m/s) used in this project. Threat is to framing "
        "(is the contracted limit physically meaningful?), not to the measurement. CC BY 4.0."),
    "10.3390/jmse11040803": ("li2023jmse", True, "1-crane-wind",
        "IoT-monitored tower crane through typhoon In-fa; documents response lag and weathercock effect in the "
        "NON-WORKING state, i.e. crane response is hysteretic. Supports the parked-state caveat on crane-level "
        "wind proxies. CC BY 4.0."),
    "10.1007/978-981-97-1876-4_60": ("wang2024lnme", True, "1-crane-wind",
        "Wind-vibration coefficient of a QTZ25 crane varies 12.0-18.6% with assumed wind spectrum and direction. "
        "Justifies treating the gust/mean averaging interval as a sensitivity axis."),
    "10.1016/j.ssci.2022.106044": ("hu2023ssci", True, "1-crane-wind",
        "Crane-operation hazard EXPOSURE (kinematic, no weather input). Shows 'crane exposure' is an established "
        "measurable object; no forecast, no decision, no calibration."),
    "10.1177/1461348419847306": ("chen2019jlf", True, "1-crane-wind",
        "Pre-2022 anchor: full-scale CFD + FE wind-induced vibration of a tower crane. Structural-safety line is "
        "decades old; used to avoid implying 'wind matters for cranes' is new. CC BY 4.0."),
    "10.1016/j.marstruc.2023.103483": ("jafarpour2023marstruc", True, "2-multihazard",
        "Same authors as jafarpour2024 (already in the positioning matrix); companion paper on weather windows for "
        "transportation of large offshore structures. Reviewed together to avoid appearing to miss it."),
    "10.1016/j.marstruc.2021.103050": ("wu2021marstruc", True, "2-multihazard",
        "THEORETICAL HOME OF THE ALPHA-FACTOR that doskeland2023 applies: response-based correction factor for "
        "allowable sea state under forecast uncertainty. Must be cited wherever the project contrasts alpha-factors "
        "with fitted calibration. Crossref records a CC BY licence on the article."),
    "10.1115/omae2016-54774": ("wang2016omae", True, "2-multihazard",
        "Multi-phase offshore transshipment downtime: persistency analysis vs scatter analysis; scatter is "
        "optimistic. Classical ancestor of the 'a window is not a point condition' argument. Waves only."),
    "10.1016/j.oceaneng.2025.121664": ("li2025oceaneng", True, "2-multihazard",
        "Joint probability of significant wave height and wind speed. Multi-hazard CLIMATOLOGY, not multi-hazard "
        "INFORMATION: no forecast, no decision, no calibration."),
    "10.1016/j.wace.2024.100718": ("mohamed2024wace", True, "2-multihazard",
        "Compound hail + wind + rainfall multivariate extremes; single-hazard risk assessment is misleading. "
        "Citable motivation for a wind+rain operational window as future work. CC BY-NC 4.0."),
    "10.3390/jmse10020284": ("wu2022jmse", True, "2-multihazard",
        "Only located work coupling wind AND rain as simultaneous physical loads (5 MW floating wind turbine, "
        "WARFoam Euler multiphase). Physics coupling exists; decision coupling does not. CC BY 4.0."),
    "10.1175/mwr-d-21-0150.1": ("schulz2022mwr", True, "3-ensemble-decisions",
        "CLOSEST METHODOLOGICAL NEIGHBOUR. Eight methods for ensemble wind-GUST postprocessing, 6 years, 175 German "
        "stations. Target is the marginal gust distribution, not a decision event; no window, no schedule, no "
        "cost-loss value, no latency audit. A reviewer may ask why this project uses a binned table on "
        "deterministic GFS instead of postprocessing an ensemble."),
    "10.1175/waf-d-21-0118.1": ("coburn2022waf", True, "3-ensemble-decisions",
        "ANN vs regression for gust OCCURRENCE and magnitude skill; 1000 random 70/30 subsets. Establishes gust "
        "occurrence probabilities are improvable; adjacent to, but distinct from, calibrating a block decision event."),
    "10.1175/waf-d-22-0006.1": ("benacek2023waf", True, "3-ensemble-decisions",
        "Tree-based probabilistic postprocessing with a CHRONOLOGICAL hold-out (train 2015-18, test 2019). "
        "Precedent for the project's split discipline - so the split itself cannot carry the novelty claim."),
    "10.1016/j.oceaneng.2023.115265": ("kolios2023oceaneng", True, "3-ensemble-decisions",
        "FULL TEXT READ THIS SESSION (CC BY, 14 pp, downloaded from Strathprints and text-extracted). Three forecast "
        "GENERATORS (Markov, gradient boosting, hybrid) drive an offshore wind O&M availability simulation; forecast "
        "modelling uncertainty changes KPIs materially. Keyword census of the extracted text: calibrat=0, Brier=0, "
        "cost-loss=0, economic value=0, latency=0, issue time=0; 'ensemble' once = gradient-boosting ensemble. "
        "Confirms uncertainty propagation into operability AND the absence of the calibration/availability/value layer."),
    "10.1016/j.renene.2016.10.064": ("azcarate2017rene", True, "3-ensemble-decisions",
        "Pre-2022 anchor: probabilistic resource forecast -> tactical/operational wind-energy management with storage."),
    "10.1002/essoar.10505717.1": ("hubbard2021firo", True, "4-forecast-value",
        "Engineering-domain measurement of forecast value outside meteorology: FIRO Lake Mendocino, 5 scenarios, "
        "16 metrics, benefits monetised across five sectors. PREPRINT - peer-review status NOT verified in this "
        "audit; cite only with that label."),
    "10.1111/risa.70328": ("lin2026risa", True, "4-forecast-value",
        "Two controlled experiments (n=324; n=122): probabilistic vs deterministic high-impact weather information "
        "changes response and null-event tolerance; asymmetric institutional error costs govern false-alarm "
        "tolerance. Behavioural justification for reporting an exposure-miss FRONTIER rather than one accuracy number."),
    "10.1016/j.mex.2024.103010": ("sitthiyot2024mex", True, "4-forecast-value",
        "Methods note on improving binary forecast skill verification. Metadata only; cite only if a specific "
        "scoring choice needs defending."),
    "10.1029/2023MS004019": ("rasp2024wb2", True, "5-data-resources",
        "WeatherBench 2: community benchmark and evaluation protocol for global weather models (deterministic and "
        "probabilistic metrics, baselines, open code/data). CC BY 4.0. Citable, community-standard way to state "
        "where the GFS gust field sits in forecast-skill terms."),
    "10.1175/bams-d-12-00014.1": ("hamill2014bams", True, "5-data-resources",
        "GEFS Reforecast v2 dataset paper. Long consistent ensemble reforecast archive (NOAA/PSL page verified "
        "live HTTP 200). Highest-value new data resource: the only practical route past the project's rare-event "
        "ceiling, and it enables a calibrated-deterministic vs ensemble comparison."),
    "10.1115/omae2020-19119": ("omae2020weatherwindow", True, "5-data-resources",
        "Verified during discovery (direct doi.org resolve) but NOT carried into the matrix: 2020 conference paper "
        "on extending the weather window for offshore drilling via simulations + probabilistic machine learning. "
        "Recorded here as verified-but-uncited so the trail is complete."),
    "10.1016/j.ssci.2021.105578": ("see2022ssci", True, "1-crane-wind",
        "Verified during discovery but NOT carried into the matrix: evolutionary-game safety supervision of tower "
        "crane operation. Management/regulatory angle, no weather input. Recorded as verified-but-uncited."),
    "10.1109/igarss55030.2025.11242810": ("igarss2025gefs", True, "3-ensemble-decisions",
        "Verified during discovery but NOT carried into the matrix: bias correction of NOAA GEFS wind forecasts "
        "using machine learning. Relevant to the ensemble extension; conference paper. Verified-but-uncited."),
    "10.1155/2024/9970264": ("gustfactor2024", True, "1-crane-wind",
        "Verified during discovery but NOT carried into the matrix: gust-factor models involving wind speed and "
        "temperature profiles for gust estimation. Verified-but-uncited."),
    "10.1175/waf-d-24-0017.1": ("gustml2026waf", True, "3-ensemble-decisions",
        "Verified during discovery but NOT carried into the matrix: maximum wind gust forecast method combining "
        "traditional statistics and machine learning (2026, Weather and Forecasting). Verified-but-uncited."),
    "10.1016/j.autcon.2022.104341": ("seo2022autcon", False, "redundant",
        "ALREADY PRESENT in outputs/gates/G1_verified_references.json as seo2022 - re-verified during this session's "
        "discovery, not a new work. Excluded from the expansion count."),
}


def main():
    # NOTES keys must match on a case-insensitive DOI basis (Crossref lower-cases DOIs)
    notes = {k.lower(): v for k, v in NOTES.items()}
    recs = []
    for name in ("verified_batch1.json", "verified_batch2.json", "verified_extra.json",
                 "verify_route2_batch1.json"):
        path = os.path.join(SRC, name)
        if os.path.exists(path):
            recs.extend(json.load(open(path, encoding="utf-8")))

    merged = {}
    for r in recs:
        doi = r["doi"].lower()
        cr = r.get("crossref") or {}
        oa = r.get("openalex") or {}
        dr = r.get("doi_resolve") or {}
        prev = merged.get(doi, {})
        # best-known values win; a later partial record must never blank an earlier confirmation
        merged[doi] = {
            "doi": doi,
            "verify_date": "2026-09-15",
            "crossref_verified": bool(prev.get("crossref_verified")) or bool(cr.get("verified")),
            "doi_resolve_verified": bool(prev.get("doi_resolve_verified")) or bool(dr.get("resolve_verified")),
            "openalex_verified": bool(prev.get("openalex_verified")) or bool(oa.get("openalex_verified")),
            "openalex_note": ("OpenAlex returned HTTP 429 for every call in this audit window; "
                              "not usable as a cross-check this session."),
            "verification_method": [
                f"Crossref REST /works/{doi}?mailto=research@example.org",
                f"https://doi.org/{doi} content negotiation (Accept: application/vnd.citationstyles.csl+json)",
                f"https://api.openalex.org/works/https://doi.org/{doi}?mailto=research@example.org (HTTP 429)",
            ],
            "title": cr.get("title") or dr.get("title") or prev.get("title") or oa.get("title"),
            "container_title": (cr.get("container") or dr.get("container")
                                or prev.get("container_title") or oa.get("container")),
            "year": cr.get("year") or dr.get("year") or prev.get("year") or oa.get("year"),
            "volume": cr.get("volume") or prev.get("volume"),
            "issue": cr.get("issue") or prev.get("issue"),
            "page": cr.get("page") or cr.get("article_number") or prev.get("page"),
            "type": cr.get("type") or dr.get("type") or prev.get("type") or oa.get("type"),
            "publisher": cr.get("publisher") or prev.get("publisher"),
            "authors": cr.get("authors") or prev.get("authors") or [],
            "license": cr.get("license") or prev.get("license") or [],
            "is_referenced_by_count": (cr.get("is_referenced_by_count")
                                       if cr.get("is_referenced_by_count") is not None
                                       else prev.get("is_referenced_by_count")),
        }
        if doi in notes:
            ck, new_work, direction, note = notes[doi]
            merged[doi].update({"cite_key": ck, "new_work": new_work,
                                "direction": direction, "audit_note": note})

    discarded = [
        {"doi": "10.5194/gmd-17-6431-2024", "status": "DISCARDED - FAILED all routes",
         "reason": "Memory-constructed guess at a WeatherBench 2 identifier; Crossref returns no record and "
                   "doi.org does not resolve. Correct identifier is 10.1029/2023MS004019.",
         "crossref_verified": False, "doi_resolve_verified": False, "openalex_verified": False},
        {"doi": "10.5194/gmd-14-5745-2021", "status": "DISCARDED - FAILED all routes",
         "reason": "Memory-constructed guess; Crossref returns no record and doi.org does not resolve.",
         "crossref_verified": False, "doi_resolve_verified": False, "openalex_verified": False},
        {"doi": "10.1115/1.4071742", "status": "VERIFIED on retry",
         "reason": "First resolution attempt failed transiently (doi.org and OpenAlex both empty); a retry "
                   "resolved successfully via doi.org and Crossref. Recorded because the first failure was "
                   "real and the retry is the evidence.",
         "crossref_verified": True, "doi_resolve_verified": True, "openalex_verified": False},
    ]

    payload = {
        "generated": "2026-09-15",
        "purpose": ("Machine-readable audit trail for outputs/gates/G1_expansion_2026-09-15.md and "
                    "outputs/gates/G1_expansion_matrix.csv (G1 five-direction literature expansion)."),
        "verification_environment": {
            "crossref": "WORKED (REST /works/{doi})",
            "doi_resolver": "WORKED (doi.org content negotiation, CSL-JSON)",
            "openalex": "NOT USABLE THIS SESSION - HTTP 429 on every query and DOI lookup. Degraded relative "
                        "to the 2026-09-15 G1 closure, which did cross-check OpenAlex.",
            "publisher_fulltext": "ScienceDirect / ASME Digital Collection / MDPI returned HTTP 403 to "
                                  "programmatic clients. No paywall bypass attempted.",
        },
        "counts": {
            "unique_dois_verified": sum(1 for v in merged.values() if v["crossref_verified"]),
            "new_works_in_matrix": sum(1 for v in merged.values() if v.get("new_work") is True),
            "verified_but_not_in_matrix": sum(1 for v in merged.values() if v.get("new_work") is False),
        },
        "works": list(merged.values()),
        "discarded_or_flagged": discarded,
    }
    out = os.path.join(SRC, "verified_expansion.json")
    json.dump(payload, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"WROTE {out}")
    print("counts:", json.dumps(payload["counts"]))
    for v in payload["works"]:
        flag = "MATRIX" if v.get("new_work") else ("redundant" if v.get("new_work") is False else "extra")
        print(f"  {v['doi']:42s} cr={str(v['crossref_verified']):5s} {flag:9s} {v.get('cite_key','')}")


if __name__ == "__main__":
    main()
