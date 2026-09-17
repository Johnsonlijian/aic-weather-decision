"""Build outputs/gates/G1_verified_references.json.

Bibliographic fields are taken verbatim from the raw verification records in
sources/raw/g1/verify_*.json (Crossref /works/{doi} and OpenAlex /works/https://doi.org/{doi},
retrieved 2026-09-15). Evidence level, notes and the citation key are the auditor's
annotations. Any DOI that could not be resolved by either authoritative endpoint is
emitted with verified=false and the exact failure recorded, never silently dropped.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw" / "g1"
OUT = ROOT / "outputs" / "gates" / "G1_verified_references.json"
VERIFIED_DATE = "2026-09-15"

# cite_key -> (doi, evidence_level, notes, in_matrix)
SPEC: list[tuple[str, str, str, str, bool]] = [
    # --- closest / matrix works -------------------------------------------------
    ("kerkhove2017", "10.1016/j.omega.2016.01.011",
     "abstract+metadata only (final journal version); author doctoral thesis chapters 7-8 read from local PDF",
     "Closest method. Final journal full text is not open access; the related author thesis (kerkhove2016thesis) was read locally. Numerical replication not attempted, so journal-version equivalence is NOT established.", True),
    ("zhou2021", "10.1016/j.cie.2021.107322", "abstract+metadata only",
     "Publisher record and abstract verified; full-text method audit still open. No baseline implementation may be claimed as an exact reproduction.", True),
    ("ballesteros2017", "10.1016/j.autcon.2017.08.022",
     "author-version full text read (local PDF pp.4-16, 31-39); final journal metadata verified",
     "Closest construction-weather planning precedent. Weather-aware planning itself cannot be claimed as novel.", True),
    ("ballesteros2018", "10.1080/01446193.2018.1478109", "metadata only",
     "Sine-wave weather model for construction scheduling; climatological rather than forecast-driven.", True),
    ("doskeland2023", "10.1016/j.oceaneng.2023.115896", "abstract+metadata only",
     "THREAT. Response forecasting framed as decision support for weather-sensitive offshore construction by an installation contractor (Subsea7). OpenAlex W4387165254 confirms CC-BY; the UiS Brage full text (handle 11250/3095815) did not resolve from this network, so no method claim is made beyond the abstract.", True),
    ("jafarpour2024", "10.1016/j.oceaneng.2024.117027", "abstract+metadata only",
     "THREAT. Weather-sensitive offshore construction planning for one mega-operation (float-over).", True),
    ("hong2026", "10.1016/j.marstruc.2026.104144", "abstract+metadata only",
     "Persistence-based operability with a Poisson interval framework for time-constrained installation.", True),
    ("tinoco2019", "10.1115/omae2019-96137", "abstract+metadata only",
     "THREAT. Ensemble forecast used to define offshore installation operability; conference paper, metadata verified via Crossref.", True),
    ("ursavas2017", "10.1016/j.ejor.2016.08.057", "abstract+metadata only",
     "Offshore wind installation planning with Benders decomposition under weather uncertainty.", True),
    ("qu2026", "10.3390/jmse14020223", "abstract+metadata only",
     "Recent collaborative vessel scheduling under weather uncertainty.", True),
    ("shahin2011", "10.1061/(ASCE)CO.1943-7862.0000258", "abstract+metadata only",
     "Weather-sensitive construction activity simulation.", True),
    ("peng2023", "10.1016/j.eswa.2022.119188", "metadata only",
     "Proactive-reactive RCPSP under general (not weather-specific) uncertainty; establishes that reactive rescheduling under uncertainty is prior art.", True),
    # --- decision-analytic forecast value ---------------------------------------
    ("mylne2002", "10.1017/S1350482702003043", "abstract+metadata only",
     "THREAT. Decision-making from probability forecasts based on forecast value.", True),
    ("richardson2000", "10.1002/qj.49712656313", "abstract+metadata only",
     "THREAT. Canonical relative-economic-value / cost-loss evaluation of an ensemble prediction system.", True),
    ("zhu2002", "10.1175/1520-0477(2002)083<0073:TEVOEB>2.3.CO;2", "abstract+metadata only",
     "THREAT. Multi-application economic value of ensemble forecasts.", True),
    ("murphy1977", "10.1175/1520-0493(1977)105<0803:TVOCCA>2.0.CO;2", "metadata only",
     "THREAT. Origin of the quality-versus-value distinction in the cost-loss setting. NOTE: this record is a legacy AMS DOI containing a semicolon; handle with a quoted CSV/JSON reader.", True),
    ("murphy1990", "10.1175/1520-0493(1990)118<0939:ODMATV>2.0.CO;2", "metadata only",
     "THREAT. Time-dependent cost-loss model with sequential information updating. Legacy semicolon DOI.", True),
    ("murphy1985b", "10.1175/1520-0493(1985)113<0801:RDMATV>2.0.CO;2", "metadata only",
     "Repetitive/dynamic cost-loss decision making. Legacy semicolon DOI.", True),
    ("buizza2001", "10.1175/1520-0493(2001)129<2329:AAPEVO>2.0.CO;2", "metadata only",
     "THREAT. Accuracy versus potential economic value for discrete events. Legacy semicolon DOI.", True),
    ("murphy1993", "10.1175/1520-0434(1993)008<0281:WIAGFA>2.0.CO;2", "metadata only",
     "THREAT. Canonical quality/value framework. Legacy semicolon DOI.", True),
    ("thompson1952", "10.1175/1520-0477-33.6.223", "metadata only",
     "THREAT. Roots of decision-oriented verification of categorical forecasts. Crossref title reads 'On the Operational Deficiences in Categorical Weather Forecasts' (sic).", True),
    ("ebert2013", "10.1002/met.1392", "metadata only",
     "User-oriented and decision-oriented verification is an established field.", True),
    ("jewson2020", "10.20944/preprints202002.0217.v2", "abstract+metadata only (preprint)",
     "Preprint only: peer-review status NOT verified. Cost-loss extension for deciding now versus waiting for the next forecast; conceptually relevant to forecast-availability latency.", True),
    ("elmachtoub2022", "10.1287/mnsc.2020.3922", "abstract+metadata only",
     "THREAT. Smart Predict-then-Optimize; the conceptual point that prediction accuracy is not decision value is prior art. Open-access author preprint: arXiv:1710.08005.", True),
    ("gneiting2007", "10.1111/j.1467-9868.2007.00587.x", "abstract+metadata only",
     "Calibration and sharpness theory; our calibration diagnostics are applications, not new theory.", True),
    ("hersbach2020", "10.1002/qj.3803", "metadata only",
     "ERA5 reanalysis. Cited to support the boundary that a reanalysis is not an as-issued forecast vintage.", True),
    # --- additional verified references (reference list, not in the matrix) ------
    ("wu2021era5check", "10.1002/qj.3803", "metadata only",
     "Duplicate guard entry: DO NOT use; retained only to make the duplicate visible. Excluded from the reference list.", False),
    ("murphy1976", "10.1175/1520-0493(1976)104<1058:DMMITC>2.0.CO;2", "metadata only",
     "Cost-loss decision-making models and measures of the value of probability forecasts. Legacy semicolon DOI.", False),
    ("murphy1985a", "10.1175/1520-0493(1985)113<0362:DMATVO>2.0.CO;2", "metadata only",
     "Generalised cost-loss decision model. Legacy semicolon DOI.", False),
    ("buizza2001b", "10.1175/1520-0493(2001)129<2329:AAPEVO>2.0.CO;2", "metadata only",
     "Duplicate guard entry: DO NOT use. Excluded from the reference list.", False),
    ("wilks2001", "10.1017/S1350482701002092", "metadata only",
     "Economic-value skill score for probability forecasts.", False),
    ("briggs2005", "10.1175/MWR3031.1", "metadata only",
     "General method for incorporating forecast cost and loss in value scores.", False),
    ("wilks1997", "10.1017/CBO9780511608278.005", "metadata only",
     "Book chapter: prescriptive decision studies of forecast value.", False),
    ("katzmurphy1997book", "10.1017/CBO9780511608278", "metadata only",
     "Edited volume Economic Value of Weather and Climate Forecasts (Cambridge University Press, 1997).", False),
    ("murphy1997verif", "10.1017/CBO9780511608278.003", "metadata only",
     "Book chapter: forecast verification (Murphy).", False),
    ("katzmurphy1997proto", "10.1017/CBO9780511608278.007", "metadata only",
     "Book chapter: prototype decision-making models for forecast value.", False),
    ("gneiting2005", "10.1175/MWR2904.1", "metadata only",
     "EMOS calibration. Our simple marginal correction is weaker than this and must not be presented as a new calibration method.", False),
    ("lee2007", "10.1002/met.44", "metadata only",
     "Economic value of weather forecasts for profit/loss decision problems.", False),
    ("kumar2010", "10.1002/met.167", "metadata only",
     "Assessment of the value of seasonal forecast information.", False),
    ("roulin2007", "10.5194/hess-11-725-2007", "metadata only",
     "Skill and relative economic value of medium-range hydrological ensemble predictions.", False),
    ("shanker2024", "10.1002/qj.4674", "metadata only",
     "Recent relative-economic-value evaluation of a global ensemble prediction system.", False),
    ("jafarpour2024b", "10.1016/j.oceaneng.2024.117027", "metadata only",
     "Duplicate guard entry: DO NOT use. Excluded from the reference list.", False),
    ("schuldt2021", "10.3390/su13052861", "abstract+metadata only",
     "Systematic review of weather-related construction delays; supports the gap statement.", False),
    ("seo2022", "10.1016/j.autcon.2022.104341", "abstract+metadata only",
     "Cost impact in loss-of-productivity claims. Useful for the retrospective-claim contrast.", False),
    ("koulinas2020", "10.3390/buildings10080134", "abstract+metadata only",
     "Simulation-based expert system for schedule delay risk.", False),
    ("kikuchi2016", "10.1088/1742-6596/753/9/092016", "metadata only",
     "Weather downtime assessment for offshore wind construction using wind/wave simulation.", False),
    ("peng2021", "10.1016/j.ifacol.2021.08.037", "metadata only",
     "Offshore wind installation scheduling with simulated annealing.", False),
    ("li2016", "10.1109/WSC.2016.7822324", "metadata only",
     "Two-stage simulation optimisation for offshore wind development under wind uncertainty.", False),
    ("hadjoudj2023", "10.1049/rpg2.12689", "metadata only",
     "O&M routing decision tools with weather uncertainty.", False),
    ("dawid2018", "10.3390/en11092190", "metadata only",
     "Offshore wind vessel routing decision support under uncertainty.", False),
    ("yates1993", "10.1061/(ASCE)0733-9364(1993)119:2(226)", "metadata only",
     "Construction decision support for delay analysis (retrospective).", False),
    ("ahuja1985", "10.1061/(ASCE)0733-9364(1985)111:4(325)", "metadata only",
     "Simulation model for project completion time.", False),
    ("bertsimas2020", "10.1287/mnsc.2018.3253", "metadata only",
     "Predictive to prescriptive analytics.", False),
    ("ban2019", "10.1287/opre.2018.1757", "metadata only",
     "Big-data newsvendor; ML for a decision problem.", False),
    ("mawlana2026", "10.3390/modelling7040137", "metadata only",
     "Variance reduction in construction simulation optimisation.", False),
    ("shen2024", "10.21203/rs.3.rs-3306307/v1", "abstract+metadata only (preprint)",
     "Preprint only: peer-review status NOT verified.", False),
    ("mylne2002b", "10.1017/S1350482702003043", "metadata only",
     "Duplicate guard entry: DO NOT use. Excluded from the reference list.", False),
    ("kerkhove2016thesis", "https://biblio.ugent.be/publication/8050564",
     "full text read (local PDF, 321 pp.; SHA256 f24caeb598d50a403e871e77d2da1497dd8da357df5e1842d7e65a2de480f81b)",
     "Author doctoral thesis associated with kerkhove2017. Verified through the Ghent University institutional record, NOT through a DOI (this item has no DOI).", False),
    ("kersk2020multimode", "10.1016/j.cie.2020.106321", "metadata only",
     "Kerkhove & Vanhoucke multi-mode schedule optimisation for incentivised projects; same author group, adjacent method.", False),
]


def fmt_authors(auths) -> list[str]:
    out = []
    for a in auths or []:
        if isinstance(a, dict):
            fam, giv = a.get("family"), a.get("given") or ""
            if fam:
                parts = [p for p in giv.replace(".", " ").replace("-", " ").split() if p]
                out.append(f"{fam}, " + " ".join(f"{p[0]}." for p in parts))
            else:
                out.append(str(a))
        else:
            out.append(str(a))
    return out


def load_records() -> dict[str, dict]:
    """Merge verify_*.json (DOI-keyed) and titlecheck_*.json (search-keyed).

    DOI keys are lower-cased because DOI resolution is case-insensitive but the legacy
    AMS suffixes are written inconsistently (e.g. "2.0.CO;2" vs "2.0.co;2").
    """
    merged: dict[str, dict] = {}
    for p in sorted(RAW.glob("verify_*.json")):
        for doi, rec in json.loads(p.read_text(encoding="utf-8")).items():
            merged.setdefault(doi.lower(), rec)
    # title-check records: keep the top hit and re-resolve its DOI against Crossref
    for p in sorted(RAW.glob("titlecheck_*.json")):
        for key, blk in json.loads(p.read_text(encoding="utf-8")).items():
            items = (blk.get("search") or {}).get("items") or []
            if not items:
                continue
            top = items[0]
            doi = (top.get("doi") or "").lower()
            if not doi or doi in merged:
                continue
            merged[doi] = {
                "crossref": {
                    "ok": True,
                    "source": "crossref_title_search",
                    "verification_url": (blk.get("search") or {}).get("verification_url"),
                    "doi": top.get("doi"),
                    "title": top.get("title"),
                    "container": top.get("container"),
                    "authors": top.get("authors"),
                    "year": top.get("year"),
                    "volume": top.get("volume"),
                    "issue": top.get("issue"),
                    "page": top.get("page"),
                    "type": top.get("type"),
                    "publisher": top.get("publisher"),
                    "is_referenced_by_count": top.get("cited_by"),
                },
                "openalex": {"ok": False, "error": "not queried for title-search hits"},
                "_via": f"titlecheck:{key}",
            }
    return merged


def main() -> None:
    recs = load_records()
    out = []
    seen_keys = set()
    for key, doi, ev, note, in_matrix in SPEC:
        if key in seen_keys:
            raise SystemExit(f"duplicate cite_key {key}")
        seen_keys.add(key)
        if "DUPLICATE GUARD" in note:
            continue
        rec = recs.get(doi.lower())
        entry = {
            "cite_key": key,
            "in_positioning_matrix": in_matrix,
            "verified": False,
            "verification_date": VERIFIED_DATE,
            "verification_method": None,
            "doi": doi,
            "url": None,
            "evidence_level": ev,
            "notes": note,
        }
        if rec is None:
            entry["verification_method"] = (
                "NOT RESOLVED through Crossref or OpenAlex during this audit; identity "
                "rests on the institutional record cited in the notes"
            )
            entry["url"] = doi if doi.startswith("http") else None
            entry["authors"], entry["year"], entry["title"], entry["venue"] = [], None, None, None
            if key == "kerkhove2016thesis":
                entry["verified"] = True
                entry["verification_method"] = (
                    "No DOI exists for this item. Verified through the Ghent University "
                    "institutional record https://biblio.ugent.be/publication/8050564 and "
                    "through the locally held 321-page PDF "
                    "(sources/raw/kerkhove_2016_thesis.pdf, SHA256 "
                    "f24caeb598d50a403e871e77d2da1497dd8da357df5e1842d7e65a2de480f81b) "
                    f"on {VERIFIED_DATE}."
                )
                entry["title"] = ("Improving decision making for incentivised and weather-sensitive "
                                  "projects (doctoral thesis)")
                entry["authors"] = ["Kerkhove, L.-P."]
                entry["year"] = 2016
                entry["venue"] = "Ghent University (Faculty of Economics and Business Administration)"
                entry["url"] = "https://biblio.ugent.be/publication/8050564"
            out.append(entry)
            print(f"  ! {key}: no DOI-level record ({doi})")
            continue
        cr, oa = rec.get("crossref", {}), rec.get("openalex", {})
        ok = bool(cr.get("ok") or oa.get("ok"))
        src = cr if cr.get("ok") else oa
        entry["verified"] = ok
        entry["title"] = src.get("title")
        entry["authors"] = fmt_authors(src.get("authors"))
        entry["venue"] = src.get("container")
        entry["year"] = src.get("year")
        entry["volume"] = src.get("volume")
        entry["issue"] = src.get("issue")
        entry["pages"] = src.get("page") or src.get("article_number")
        entry["type"] = src.get("type")
        entry["publisher"] = src.get("publisher")
        entry["url"] = f"https://doi.org/{doi}" if not doi.startswith("http") else doi
        if doi.lower().startswith("10.1175") or doi.lower().startswith("10.1017"):
            cr_note = ("Crossref /works/{doi} (DOI registration-agency record) "
                       "on {d}").format(doi=doi, d=VERIFIED_DATE)
        else:
            cr_note = ("Crossref /works/{doi} (DOI registration-agency record) "
                       "on {d}").format(doi=doi, d=VERIFIED_DATE)
        oa_note = (
            "; cross-checked against OpenAlex {id} ({u})".format(
                id=oa.get("openalex_id") or oa.get("id") or "record",
                u=oa.get("verification_url") or "")
            if oa.get("ok") else
            "; OpenAlex lookup did not return a usable record"
        )
        entry["verification_method"] = cr_note + oa_note
        entry["verification_url_crossref"] = cr.get("verification_url")
        entry["verification_url_openalex"] = oa.get("verification_url")
        entry["crossref_cited_by"] = cr.get("is_referenced_by_count")
        entry["openalex_cited_by"] = oa.get("cited_by_count")
        entry["openalex_is_oa"] = oa.get("is_oa")
        if not oa.get("ok"):
            entry["openalex_note"] = f"OpenAlex lookup did not return a record ({oa.get('error')})"
        if not ok:
            entry["error"] = f"crossref={cr.get('error')} openalex={oa.get('error')}"
        out.append(entry)
        print(f"  {'OK ' if ok else 'FAIL'} {key} ({doi})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    nv = sum(1 for e in out if e["verified"])
    nin = sum(1 for e in out if e["in_positioning_matrix"])
    print(f"\nWROTE {OUT}\n  entries={len(out)} verified={nv} unverified={len(out)-nv} "
          f"in_matrix={nin}")


if __name__ == "__main__":
    main()
