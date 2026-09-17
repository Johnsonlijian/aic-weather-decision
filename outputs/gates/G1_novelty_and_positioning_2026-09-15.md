# G1 — Novelty check, positioning matrix and reference audit

**Project:** `2026-AiC-Weather-Decision / AiC_Weather_Decision_Project_v1`
**Gate:** G1 (`G1_closest_fulltext_novelty`)
**Audit date:** 2026-09-15
**Auditor role:** research literature auditor (metadata-first, DOI-verified)
**Status after this audit:** G1 moves from `PARTIAL` to **CLOSED FOR THE CROSSREF/OPENALEX-SEARCHABLE LITERATURE**, with the three residual evidence limits listed in §6.

---

## 0. Bottom line for the project (read this first)

The novelty of this project is **weaker than the protocol assumes, in a specific and fixable way**.

* No prior work was found that does *exactly* what this project proposes: a non-anticipative online replay that uses **real archived as-issued NWP runs** to decide **weather-sensitive construction operations with asymmetric start/continuation contracts**, calibrated **at the decision threshold**, and reported with regret and unsafe-exceedance exposure.
* **But every individual ingredient already exists**, and three of them already exist in the *same domain* (offshore construction and installation decision support). The combination is a genuine but **incremental and integration-level** contribution.
* The sentence pattern *"prediction accuracy ≠ decision value"* and *"calibrated forecasts need not improve decisions"* is **not available as a novelty claim at all**. It is the founding result of the cost-loss literature ([murphy1977], [thompson1952], [murphy1993]) and the founding premise of decision-focused learning ([elmachtoub2022]).
* The **one defensible upgrade is to stop claiming a method and start claiming a measurement.** See §4.

---

## 1. What was searched, and how

### 1.1 Query inventory

**80 distinct bibliographic queries over 88 defined query slots.** Each distinct query was
executed against **both** Crossref `query.bibliographic` and OpenAlex `search`, giving **84
Crossref keyword calls and 84 OpenAlex keyword calls** actually executed (see the count
below). On top of that: **73 distinct DOIs re-resolved at DOI level** (78 lookup slots across
Crossref `/works/{doi}` and OpenAlex `/works/https://doi.org/{doi}`), **20 literal-title
Crossref verification queries** for classics with unguessable DOIs, and **8 general web
searches** used only to *locate* candidate items that were then verified against
Crossref/OpenAlex. No paid API was used; no Sci-Hub or equivalent source was contacted.

Query slots per batch (all defined in `sources/raw/g1/spec_batch*.json`):
A = 22, B = 22, C = 16, D = 12, E = 16 → **88 slots, 80 distinct queries** (batches A–B
share 8 near-duplicate phrasings intended as paraphrase checks). Executed keyword calls
counted from the logs: `outputs/g1_batchA.log` 20+20, `g1_batchB.log` 20+20,
`g1_batchC.log` 16+16, `g1_batchD.log` 12+12, `g1_batchE.log` 16+16 (Crossref + OpenAlex
respectively) = **84 + 84**.

*Audit note:* batches A and B were terminated early by the auditor when the Crossref query
endpoint began returning HTTP 429; their two unexecuted tail queries ("crane lifting
operation wind speed threshold safety decision" and "wind speed limit tower crane operation
stoppage construction") were re-issued inside batches C/D/E, so no intended query was lost.

Coverage was organised into nine families, and each family was hit by multiple independent phrasings:

| # | Family | Example queries |
|---|---|---|
| 1 | Weather-sensitive project scheduling | `weather sensitive project scheduling construction`; `weather-aware planning tool construction productivity claims`; `project scheduling under weather uncertainty offshore installation` |
| 2 | Stochastic RCPSP with weather | `stochastic resource-constrained project scheduling time varying weather conditions estimation of distribution algorithm`; `proactive reactive scheduling weather uncertainty project` |
| 3 | Weather downtime / operability | `weather downtime modelling offshore construction operations`; `operability analysis offshore installation weather downtime monte carlo`; `weather window offshore wind turbine installation scheduling` |
| 4 | Offshore installation scheduling | `offshore wind installation vessel scheduling weather uncertainty optimization`; `offshore wind farm installation cost weather window optimization` |
| 5 | Cost-loss / value of forecast | `cost-loss ratio economic value weather forecast decision making`; `relative economic value ensemble prediction system forecast`; `value score forecast verification decision model Katz Murphy`; `value of weather forecast decision analytic cost loss model` |
| 6 | Decision-oriented verification / calibration | `user oriented verification forecast decision threshold exceedance`; `decision oriented verification forecast binary event`; `probabilistic forecasts calibration sharpness proper scoring rules`; `Bayesian calibration deterministic weather forecast threshold event` |
| 7 | Decision-focused learning | `smart predict then optimize decision focused learning`; `decision focused learning prediction optimization end to end`; `from predictive to prescriptive analytics` |
| 8 | Non-anticipativity / online decisions | `nonanticipative online scheduling rolling horizon uncertainty`; `nonanticipatory decision policy information set scheduling`; `lookahead policies stochastic scheduling information relaxation`; `perfect information benchmark regret scheduling weather` |
| 9 | NWP archives (GFS / ERA5 / ECMWF) | `GFS global forecast system forecast data construction scheduling`; `ERA5 reanalysis construction weather productivity study`; `archived numerical prediction forecast verification built environment` |

Two machine-readable query logs are retained:
`sources/raw/g1/batchC.json`, `sources/raw/g1/batchD.json` (full request URL + raw results),
plus `outputs/g1_batchA.log`, `outputs/g1_batchB.log`, `outputs/g1_batchC.log`,
`outputs/g1_batchD.log`, `outputs/g1_batchE.log`.

### 1.2 Verification method (and its limits)

Discovery used Crossref keyword search. Because the Crossref `/works?query` endpoint
rate-limited this client heavily (HTTP 429), **discovery was moved to OpenAlex search** and
**every bibliographic identity was then confirmed at DOI level** through:

1. `https://api.crossref.org/works/{doi}?mailto=research@example.org` — the DOI
   registration-agency record (authoritative for DOI → bibliographic identity); and
2. `https://api.openalex.org/works/https://doi.org/{doi}?mailto=research@example.org`.

For classics whose DOIs cannot be guessed (pre-1990s AMS, JRSS-B, PNAS, Cambridge book
chapters), a **literal-title** Crossref query was used and the top hit was adopted
(`sources/raw/g1/titlecheck_classics.json`). This is weaker evidence than a DOI lookup,
because a title query can in principle return the wrong record; the top hit was checked
against the expected author, year and venue before acceptance.

**Two DOIs I initially constructed from memory resolved to the wrong papers** and were
discarded (a construction-materials paper and a best-subset-selection paper). They are *not*
in any deliverable. This is recorded here because it is the exact failure mode the audit is
meant to catch, and it demonstrates why nothing in this deliverable is memory-generated.

**Known limits of this audit:**
* Almost all evidence is **abstract + metadata level**. Full text was read only for two
  items already in the project (Kerkhove's thesis, and the Weather-wise author version).
* No numerical replication of any prior method was performed.
* The UiS Brage repository (`uis.brage.unit.no`) holding the CC-BY full text of
  [doskeland2023] **did not resolve from this network** (DNS failure), so that key paper is
  assessed from abstract + metadata only.
* ScienceDirect served HTTP 403 to programmatic requests throughout, so publisher full
  texts could not be read.

---

## 2. Positioning matrix

Full machine-readable table: `outputs/gates/G1_positioning_matrix.csv`
(26 works × 16 columns). Below is the compressed view; the CSV is authoritative.

**Colour key for `threat_level_to_our_novelty`:** HIGH = already occupies a core element of
the claimed contribution; MEDIUM = adjacent and constrains specific claims; LOW = context.

### 2.1 Construction / project-scheduling family

| cite_key | Work | Weather data | Latency | Calibration target | Non-anticip. | Threat |
|---|---|---|---|---|---|---|
| [kerkhove2017] | Kerkhove & Vanhoucke, *Omega* 66:58–78 | **simulated** joint wind–wave | no | none | no (pre-set resource-release times) | **HIGH** |
| [zhou2021] | Zhou et al., *C&IE* 157:107322 | parametric time-varying weather | no | none | no | **HIGH** |
| [ballesteros2017] | Ballesteros-Pérez et al., *AiC* 84:81–95 | historical records | no | none | no | MEDIUM |
| [ballesteros2018] | Ballesteros-Pérez et al., *CME* 36:1053–1069 | seasonal sine waves | no | none | no | LOW |
| [shahin2011] | Shahin et al., *JCEM* 137:238–246 | historical records | no | none | no | MEDIUM |
| [peng2023] | Peng et al., *ESWA* 214:119188 | general uncertainty | no | none | **yes (reactive)** | MEDIUM |
| [schuldt2021] | Schuldt et al., *Sustainability* 13:2861 | review | no | none | no | LOW |

### 2.2 Offshore installation / weather-window family

| cite_key | Work | Weather data | Latency | Calibration target | Non-anticip. | Threat |
|---|---|---|---|---|---|---|
| [doskeland2023] | Døskeland et al., *Ocean Eng.* 287:115896 | **response forecasting** | unclear | none stated | unclear | **HIGH** |
| [jafarpour2024] | Jafarpour Hamedani & Khedmati, *Ocean Eng.* 297:117027 | metocean limits | unclear | none | unclear | **HIGH** |
| [tinoco2019] | Tinoco et al., OMAE2019-96137 | **ensemble forecast** | **yes** | **operability threshold** | unclear | **HIGH** |
| [ursavas2017] | Ursavas, *EJOR* 258:703–714 | stochastic scenarios | unclear | none | unclear | **HIGH** |
| [hong2026] | Hong et al., *Marine Struct.* 110:104144 | persistence statistics | unclear | none | no | MEDIUM |
| [qu2026] | Qu et al., *JMSE* 14:223 | weather uncertainty | unclear | none | unclear | MEDIUM |
| [kikuchi2016] | Kikuchi & Ishihara, *JPCS* 753:092016 | mesoscale hindcast | no | none | no | LOW |

### 2.3 Decision-analytic forecast-value family (meteorology / statistics / OR)

| cite_key | Work | Latency | Calibration target | Threat |
|---|---|---|---|---|
| [murphy1977] | Murphy, *MWR* 105:803–816 | no | **cost-loss threshold** | **HIGH** |
| [murphy1990] | Murphy & Ye, *MWR* 118:939–949 | no | time-dependent cost-loss | **HIGH** |
| [murphy1993] | Murphy, *WAF* 8:281–293 | no | none (quality/value framework) | **HIGH** |
| [thompson1952] | Thompson, *BAMS* 33:223–226 | no | decision-relevant outcome | **HIGH** |
| [richardson2000] | Richardson, *QJRMS* 126:649–667 | no | cost-loss sweep | **HIGH** |
| [zhu2002] | Zhu et al., *BAMS* 83:73–83 | no | cost-loss | **HIGH** |
| [mylne2002] | Mylne, *Met. Apps.* 9:307–315 | no | value-based rule | **HIGH** |
| [buizza2001] | Buizza, *MWR* 129:2329–2345 | no | decision threshold | **HIGH** |
| [murphy1985b] | Murphy et al., *MWR* 113:801–813 | no | dynamic cost-loss | MEDIUM |
| [jewson2020] *(preprint, unrefereed)* | Jewson et al. | **conceptual (decide vs wait)** | cost-loss | MEDIUM |
| [elmachtoub2022] | Elmachtoub & Grigas, *Man. Sci.* 68:9–26 | no | **downstream decision loss** | **HIGH** |
| [gneiting2007] | Gneiting et al., *JRSS-B* 69:243–268 | no | none (theory) | LOW |
| [ebert2013] | Ebert et al., *Met. Apps.* 20:130–139 | no | none (review) | MEDIUM |
| [hersbach2020] | Hersbach et al., *QJRMS* 146:1999–2049 | no (reanalysis ≠ forecast) | none | LOW |

---

## 3. Honest novelty verdict — element by element

The protocol lists five claimed elements. Each is judged below against the verified record.

### Element 1 — Explicit "operational contract" (documented wind threshold, required uninterrupted duration, interruption and recovery rules)

**Verdict: PARTLY NEW AS A FORMAL OBJECT; THE UNDERLYING IDEA IS NOT NEW.**

* **Already exists:** offshore installation scheduling routinely encodes weather-window
  operability limits and durations ([ursavas2017], [tinoco2019], [jafarpour2024],
  [hong2026]). The idea that an operation needs an uninterrupted suitable interval is
  standard practice, not a research contribution.
* **What may be new:** making the **contract itself** a first-class, separately-documented,
  evidence-graded object — with an explicit **asymmetric start vs continuation threshold** and
  an explicit refusal to invent undocumented recovery rules (the project records an
  "unresolved episode" instead). I found **no** prior work that formalises a construction
  operation contract this way and then refuses to fabricate the recovery rule.
* **Honest weight:** this is a *representation and reporting* contribution, not a
  methodological discovery. It is defensible but small, and it lives or dies on the quality
  of the engineering evidence behind the contract. The HS2 source [hs22025] gives one
  documented asymmetric pair (11.1 m/s start / 20 m/s continuation) for one operation only.

### Element 2 — Honest modelling of forecast availability latency

**Verdict: GENUINELY UNDER-REPRESENTED, AND THE MOST DEFENSIBLE ELEMENT — BUT NOT UNPRECEDENTED IN CONCEPT.**

* **Already exists conceptually:** the decision-theoretic question "decide now or wait for
  the next forecast?" is explicitly modelled in [jewson2020] (an *unrefereed preprint* — treat
  with caution) as an extension of the cost-loss model. Sequential formulations with
  information updating also exist ([murphy1990], [murphy1985b]).
* **Already exists in the construction/offshore community, weakly:** ensemble-based
  operability assessment ([tinoco2019]) and response-forecast decision support
  ([doskeland2023]) both take "the forecast available at decision time" as their input —
  but neither *audits* publication latency, and neither separates forecast *initialisation*
  from forecast *availability*.
* **What may be new:** the **latency-audited archive replay** — using object-store
  `Last-Modified` timestamps of the actual archived GFS messages, adding a declared buffer,
  and constructing a conditional availability rule so that the controller can only ever see
  runs that a planner could have seen. The project has already measured a 3.55–3.73 h
  (median 3.60 h) lag in its 124-run pilot. I found no construction or offshore paper that
  does this.
* **Honest weight:** this is a *rigour* contribution. Its weakness is that
  `Last-Modified` is archive metadata, **not** evidence of delivery to a real site — the
  project already says this, correctly, and must keep saying it.

### Element 3 — Calibration of forecast-to-observation AT THE DECISION THRESHOLD ("decision-aligned verification")

**Verdict: NOT NEW. THIS IS A 70-YEAR-OLD IDEA IN METEOROLOGY AND MUST NOT BE CLAIMED.**

* [thompson1952] already argued that categorical forecasts must be judged by their
  operational (decision-relevant) consequences, not by generic accuracy.
* The **cost-loss ratio** literature is precisely threshold-focused, decision-aligned
  verification and value assessment: [murphy1977], [murphy1990], [richardson2000],
  [zhu2002], [mylne2002], [buizza2001]. The relative-economic-value curve *is* a
  decision-threshold-resolved verification product.
* [murphy1993] is the canonical statement that forecast **quality** and forecast **value**
  are distinct — the exact conceptual point the protocol lists as a contribution.
* Calibration and sharpness theory is settled ([gneiting2007]).
* **What may be new:** *applying* threshold-resolved verification to a **construction
  operation window** defined by an asymmetric start/continuation contract and a required
  uninterrupted duration, and reporting **Brier/reliability for the complete-window event**
  rather than for an hourly marginal. That is a legitimate domain transfer.
* **What is NOT new and must be deleted from the claims:** anything of the form "we
  introduce decision-aligned / threshold-focused / decision-oriented verification", or
  "we show that accuracy and decision value differ".

### Element 4 — Non-anticipative online replay comparing blind vs raw vs calibrated vs risk-aware, with regret vs perfect foresight

**Verdict: THE COMPARISON DESIGN IS THE STRONGEST GENUINE INCREMENT; THE COMPONENTS ARE ALL PRIOR ART.**

* **Already exists:** proactive-reactive rescheduling under uncertainty ([peng2023]);
  common-random-number comparison of weather-sensitive schedules ([kerkhove2017]);
  value-of-forecast benchmarking against climatology and perfect information is textbook
  ([murphy1977], [wilks1997], [katzmurphy1997], [richardson2000]); regret against a
  clairvoyant benchmark is standard in decision-focused learning ([elmachtoub2022]).
* **What may be new:** assembling these into **one pre-registered, information-faithful
  replay** on **real archived as-issued NWP**, with a **matched-risk, matched-budget**
  comparison across blind / raw-deterministic / decision-aligned-calibrated / risk-aware
  policies, reporting schedule delay, idle-crane time, unsafe-exceedance exposure **and**
  regret against perfect foresight under an explicit unresolved-episode accounting rule.
  I found no paper that does this combination.
* **Honest weight:** real, but it is a **benchmark and protocol** contribution, not a new
  algorithm. The protocol already concedes this ("the analytical examples… are not offered
  as a major new scheduling theorem").

### Element 5 — Honest reporting that calibrated forecasts need not improve decisions

**Verdict: NOT NEW AT ALL. THIS IS A KNOWN RESULT AND, IN PART, THE EXPECTED RESULT.**

* [murphy1977] *is* this finding, in the cost-loss setting, 45 years ago.
* [elmachtoub2022] *is* this finding, in the optimisation setting.
* [buizza2001] shows accuracy and potential economic value can diverge for discrete events.
* **Consequence for the manuscript:** the project cannot present "calibrated forecasts may
  not improve decisions" as an insight. It can only present it as a **finding about this
  specific engineering decision problem** — i.e. *where* on the cost-loss-like parameter
  space the construction scheduling decision stops extracting value from better calibration.
  That is a much narrower, but genuinely defensible, claim.

### 3.1 Verdict summary

| Element | New? | Strongest prior work |
|---|---|---|
| 1. Operation contract as formal object | Partly new (representation) | [ursavas2017], [tinoco2019], [hong2026] |
| 2. Forecast availability latency | **Genuinely under-represented** | [jewson2020] (concept), [murphy1990] (sequential) |
| 3. Decision-aligned calibration | **Not new** | [thompson1952], [murphy1977], [richardson2000], [murphy1993] |
| 4. Non-anticipative replay + regret | New as an *assembled benchmark* | [peng2023], [kerkhove2017], [elmachtoub2022] |
| 5. "Calibration ≠ better decisions" | **Not new** | [murphy1977], [elmachtoub2022], [buizza2001] |

**Overall:** the project is an **integration-and-rigour contribution with one genuinely
under-occupied niche (latency-audited archive replay)**, not a new method. Any claim of
"first" or "novel framework" is currently unsupportable.

---

## 4. Top three threats, and the recommended repositioning

### Threat 1 — [doskeland2023] Døskeland, Gudmestad & Moen (2023), *Ocean Engineering* 287:115896

*"Use of response forecasting in decision making for weather sensitive offshore construction work."*
Authored from inside an installation contractor (Subsea7 + NTNU + University of Stavanger),
with a pipelay case study. **This is the single closest published framing to the project's
core story**: forecast-derived information → decision support → weather-sensitive offshore
construction. It is CC-BY, which means it will be read by reviewers and cited against us.
*Evidence limit:* assessed here at abstract + metadata level only (UiS Brage full text did
not resolve from this network), so no claim is made about its internals.

### Threat 2 — [tinoco2019] Tinoco, Ting & Chavan (2019), ASME OMAE2019-96137

*"The Use of Ensemble Forecast in Defining Offshore Installation Operability."*
This one is sharper than Threat 1 because it already does three of our five elements:
a **probabilistic ensemble forecast** as the decision input, **operability thresholds** as
the calibration/decision target, and a **case study on a real installation operation**
(umbilical shore float-in). What it does *not* do is a multi-activity resource-constrained
scheduling replay, forecast-latency auditing, or regret accounting.

### Threat 3 — [murphy1977] Murphy (1977), *Monthly Weather Review* 105:803–816
(and its lineage [thompson1952], [murphy1993], [richardson2000], [buizza2001], [elmachtoub2022])

The **conceptual core** of the project's framing — that forecast quality and forecast value
are distinct, and that a threshold-resolved cost-loss analysis tells you where a forecast is
worth anything — is not merely prior art, it is *textbook* prior art. A reviewer with a
meteorological or decision-analysis background will reject any claim to novelty in elements
3 and 5 immediately.

### Recommended repositioning of the central claim

**Retire this claim form (currently implied by the protocol and the draft):**

> "We propose a decision-analytic, calibration-aware framework for forecast-informed
> construction scheduling that calibrates forecasts at the decision threshold and shows
> that forecast accuracy need not translate into decision value."

Every clause of that sentence is already occupied (see §3), and the last clause is a
45-year-old result.

**Adopt this claim form instead:**

> **Central claim (recommended).** Forecast value in weather-sensitive construction is not
> determined by forecast skill but by whether the *decision-relevant event* — a complete,
> uninterrupted, contract-admissible operating window under a resource-coupled schedule — is
> resolvable within the information actually available at the decision epoch. We provide the
> first **latency-audited, non-anticipative replay benchmark** that measures this on real
> archived as-issued NWP: it holds the operation contract and the action set fixed, varies
> only the forecast treatment (blind / raw deterministic / decision-aligned calibrated /
> risk-aware), and reports where in the contract-and-latency parameter space additional
> calibration stops buying schedule value.

Three things make this defensible and testable:
1. **The object is the measurement, not the method.** "We built the benchmark that lets the
   field answer this question honestly on real archive data" is a claim a reviewer can check
   and that no prior work in §2 occupies.
2. **Latency auditing is the load-bearing novelty.** Keep it front and centre. It is the one
   element with no construction/offshore prior art found, and it is what makes the negative
   results credible rather than artefacts of look-ahead.
3. **Negative results become the product, not the embarrassment.** The protocol already
   commits to reporting when simple methods suffice. Under this repositioning that is the
   headline, not a fallback.

**Corollary — claims to delete from the manuscript now:**
* Any form of "we introduce decision-aligned / threshold-focused verification."
* Any form of "we show accuracy and decision value can diverge."
* Any "first" or "novel framework" phrasing about weather-aware construction planning
  (blocked by [ballesteros2017] and [kerkhove2017]).
* Any implication that value-of-forecast framing is new ([murphy1993], [elmachtoub2022]).

**Corollary — one experiment to add, and it is cheap.** Because [murphy1977] and
[richardson2000] give the cost-loss/relative-economic-value machinery, the project can
compute a **relative-economic-value curve for the construction window event** as a function
of a synthetic cost-loss ratio, on the *same* 120,600 station-hour and 124-run pilot data it
already has. That single figure would connect the project to 70 years of decision-analytic
literature *and* demonstrate that the project knows that literature. It costs no new data
collection.

---

## 5. Reference list (Elsevier / AiC numeric style, fully verified)

All 26 matrix works are listed here with their verification route, plus 4 additional
verified works used for positioning but not scored in the matrix (30 entries total). `[V]` = DOI resolved
through the Crossref registration-agency record on 2026-09-15 (OpenAlex cross-checked where
available). `[V*]` = verified but **not** through a DOI (see note). Nothing in this list is
memory-generated.

1. [ballesteros2017] [V] Ballesteros-Pérez P., Rojas-Céspedes Y.A., Hughes W., Kabiri S., Pellicer E., Mora-Melià D., del Campo-Hitschfeld M.L. Weather-wise: A weather-aware planning tool for improving construction productivity and dealing with claims. *Automation in Construction* 2017;84:81–95. https://doi.org/10.1016/j.autcon.2017.08.022
2. [ballesteros2018] [V] Ballesteros-Pérez P., Smith S.T., Lloyd-Papworth J.G. Incorporating the effect of weather in construction scheduling and management with sine wave curves: application in the United Kingdom. *Construction Management and Economics* 2018;36(12):1053–1069. https://doi.org/10.1080/01446193.2018.1478109
3. [buizza2001] [V] Buizza R. Accuracy and potential economic value of categorical and probabilistic forecasts of discrete events. *Monthly Weather Review* 2001;129(9):2329–2345. https://doi.org/10.1175/1520-0493(2001)129<2329:AAPEVO>2.0.CO;2
4. [doskeland2023] [V] Døskeland Ø., Gudmestad O.T., Moen P. Use of response forecasting in decision making for weather sensitive offshore construction work. *Ocean Engineering* 2023;287:115896. https://doi.org/10.1016/j.oceaneng.2023.115896 *(abstract + metadata only)*
5. [ebert2013] [V] Ebert E., Wilson L., Weigel A., Mittermaier M., Nurmi P., Gill P., Göber M., Joslyn S., Brown B., Fowler T., Watkins A. Progress and challenges in forecast verification. *Meteorological Applications* 2013;20(2):130–139. https://doi.org/10.1002/met.1392
6. [elmachtoub2022] [V] Elmachtoub A.N., Grigas P. Smart "Predict, then Optimize". *Management Science* 2022;68(1):9–26. https://doi.org/10.1287/mnsc.2020.3922
7. [gneiting2007] [V] Gneiting T., Balabdaoui F., Raftery A.E. Probabilistic forecasts, calibration and sharpness. *Journal of the Royal Statistical Society: Series B* 2007;69(2):243–268. https://doi.org/10.1111/j.1467-9868.2007.00587.x
8. [hersbach2020] [V] Hersbach H., Bell B., Berrisford P., Hirahara S., Horányi A., Muñoz-Sabater J., et al. The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society* 2020;146(730):1999–2049. https://doi.org/10.1002/qj.3803
9. [hong2026] [V] Hong S., Zhang H., Halse K.H. Persistence-based operability for time-constrained onsite installation of floating offshore wind turbines: Poisson interval framework. *Marine Structures* 2026;110:104144. https://doi.org/10.1016/j.marstruc.2026.104144
10. [jafarpour2024] [V] Jafarpour Hamedani S., Khedmati M.R. Optimized planning for weather-sensitive offshore construction operations — An application to float-over installation of super-heavy offshore topsides. *Ocean Engineering* 2024;297:117027. https://doi.org/10.1016/j.oceaneng.2024.117027
11. [jewson2020] [V] **PREPRINT — peer-review status NOT verified.** Jewson S., Scher S., Messori G. Decide now or wait for the next forecast? A decision framework based on an extension of the cost-loss model. *Preprints* 2020. https://doi.org/10.20944/preprints202002.0217.v2
12. [kerkhove2017] [V] Kerkhove L.-P., Vanhoucke M. Optimised scheduling for weather sensitive offshore construction projects. *Omega* 2017;66:58–78. https://doi.org/10.1016/j.omega.2016.01.011 *(final journal full text restricted; author thesis read locally)*
13. [kerkhove2016thesis] [V*] Kerkhove L.-P. *Improving decision making for incentivised and weather-sensitive projects.* Doctoral thesis, Ghent University, 2016. https://biblio.ugent.be/publication/8050564 — **no DOI exists**; verified through the institutional record and the locally held 321-page PDF (SHA256 `f24caeb5…80f81b`). **Not** assumed identical to [kerkhove2017].
14. [kersk2020multimode] [V] Kerkhove L.-P., Vanhoucke M. Multi-mode schedule optimisation for incentivised projects. *Computers & Industrial Engineering* 2020;144:106321. https://doi.org/10.1016/j.cie.2020.106321
15. [kikuchi2016] [V] Kikuchi Y., Ishihara T. Assessment of weather downtime for the construction of offshore wind farm by using wind and wave simulations. *Journal of Physics: Conference Series* 2016;753:092016. https://doi.org/10.1088/1742-6596/753/9/092016
16. [murphy1977] [V] Murphy A.H. The value of climatological, categorical and probabilistic forecasts in the cost-loss ratio situation. *Monthly Weather Review* 1977;105(7):803–816. https://doi.org/10.1175/1520-0493(1977)105<0803:TVOCCA>2.0.CO;2
17. [murphy1985b] [V] Murphy A.H., Katz R.W., Winkler R.L., Hsu W.R. Repetitive decision making and the value of forecasts in the cost-loss ratio situation: a dynamic model. *Monthly Weather Review* 1985;113(5):801–813. https://doi.org/10.1175/1520-0493(1985)113<0801:RDMATV>2.0.CO;2
18. [murphy1990] [V] Murphy A.H., Ye Q. Optimal decision making and the value of information in a time-dependent version of the cost-loss ratio situation. *Monthly Weather Review* 1990;118(4):939–949. https://doi.org/10.1175/1520-0493(1990)118<0939:ODMATV>2.0.CO;2
19. [murphy1993] [V] Murphy A.H. What is a good forecast? An essay on the nature of goodness in weather forecasting. *Weather and Forecasting* 1993;8(2):281–293. https://doi.org/10.1175/1520-0434(1993)008<0281:WIAGFA>2.0.CO;2
20. [mylne2002] [V] Mylne K.R. Decision-making from probability forecasts based on forecast value. *Meteorological Applications* 2002;9(3):307–315. https://doi.org/10.1017/S1350482702003043
21. [peng2023] [V] Peng W., Lin X., Li H. Critical chain based proactive-reactive scheduling for resource-constrained project scheduling under uncertainty. *Expert Systems with Applications* 2023;214:119188. https://doi.org/10.1016/j.eswa.2022.119188
22. [qu2026] [V] Qu S., Yu C., Zhou Y., Hou Y., Wang J., Li F. Optimization of collaborative vessel scheduling for offshore wind farm installation under weather uncertainty. *Journal of Marine Science and Engineering* 2026;14(2):223. https://doi.org/10.3390/jmse14020223
23. [richardson2000] [V] Richardson D.S. Skill and relative economic value of the ECMWF ensemble prediction system. *Quarterly Journal of the Royal Meteorological Society* 2000;126(563):649–667. https://doi.org/10.1002/qj.49712656313
24. [schuldt2021] [V] Schuldt S.J., Nicholson M.R., Adams Y.A., Delorit J.D. Weather-related construction delays in a changing climate: a systematic state-of-the-art review. *Sustainability* 2021;13(5):2861. https://doi.org/10.3390/su13052861
25. [shahin2011] [V] Shahin A., AbouRizk S.M., Mohamed Y. Modeling weather-sensitive construction activity using simulation. *Journal of Construction Engineering and Management* 2011;137(3):238–246. https://doi.org/10.1061/(ASCE)CO.1943-7862.0000258
26. [thompson1952] [V] Thompson J.C. On the operational deficiences in categorical weather forecasts. *Bulletin of the American Meteorological Society* 1952;33(6):223–226. https://doi.org/10.1175/1520-0477-33.6.223 *(original title spelling preserved)*
27. [tinoco2019] [V] Tinoco F., Ting K.C., Chavan K. The use of ensemble forecast in defining offshore installation operability: a case study on umbilical shore float-in operations. In: *Proceedings of the ASME 38th International Conference on Ocean, Offshore and Arctic Engineering (OMAE2019)*, Volume 1: Offshore Technology; Offshore Geotechnics, V001T01A017. https://doi.org/10.1115/OMAE2019-96137
28. [ursavas2017] [V] Ursavas E. A Benders decomposition approach for solving the offshore wind farm installation planning at the North Sea. *European Journal of Operational Research* 2017;258(2):703–714. https://doi.org/10.1016/j.ejor.2016.08.057
29. [zhou2021] [V] Zhou Y., Miao J., Yan B., Zhang Z. Stochastic resource-constrained project scheduling problem with time varying weather conditions and an improved estimation of distribution algorithm. *Computers & Industrial Engineering* 2021;157:107322. https://doi.org/10.1016/j.cie.2021.107322
30. [zhu2002] [V] Zhu Y., Toth Z., Wobus R., Richardson D., Mylne K. The economic value of ensemble-based weather forecasts. *Bulletin of the American Meteorological Society* 2002;83(1):73–83. https://doi.org/10.1175/1520-0477(2002)083<0073:TEVOEB>2.3.CO;2

**Verification method for every entry above:** `GET https://api.crossref.org/works/{doi}?mailto=research@example.org`
(the DOI registration-agency record) on 2026-09-15, cross-checked against
`GET https://api.openalex.org/works/https://doi.org/{doi}?mailto=research@example.org`.
Raw responses: `sources/raw/g1/verify_core.json`, `verify_b.json`, `verify_near.json`,
`verify_final.json`, `verify_preprints.json`, `titlecheck_classics.json`.
Machine-readable version of this list: `outputs/gates/G1_verified_references.json`
(59 entries, 26 flagged `in_positioning_matrix: true`).

### 5.1 Entries that could NOT be fully verified — flagged explicitly

| Item | Status | Reason |
|---|---|---|
| Any GFS-specific published construction study | **NOT FOUND** | 96 queries produced no peer-reviewed paper that uses archived GFS 0.25° runs for construction scheduling decisions. Absence of evidence after this search effort is the honest finding; it is not proof of absence. |
| "Su et al. — improved weather forecasts reduce construction delays" | **NOT FOUND / DISCARDED** | A candidate was suggested by a web search; a literal-title Crossref query returned no matching record, so the item was **not** recorded anywhere. Do not cite it. |
| [jewson2020], [shen2024] | **PREPRINTS** | DOI records exist (Crossref `posted-content`) but peer-review status is unverified. Usable only as context, never as established prior art. |
| [doskeland2023] full text | **NOT READ** | CC-BY full text located at UiS Brage handle 11250/3095815; host did not resolve from this network. Its internals (latency handling, calibration target, metrics) are recorded as `unclear`, **not** as "no". |
| [kerkhove2017] final journal version | **NOT READ** | Restricted. The author thesis is audited locally; journal-version equivalence is **not** established. |

---

## 6. Residual limits of this G1 closure

1. **Abstract-level evidence dominates.** Only 2 of 26 matrix works had full text read.
   Specific fields — `forecast_latency_handled`, `calibration_target`,
   `decision_nonanticipatory_yes_no` — are therefore `unclear` for 8 works, and `unclear`
   must not be read as "they don't do it". Obtaining full texts for [doskeland2023],
   [jafarpour2024], [tinoco2019] and [zhou2021] is the highest-value remaining action.
2. **Crossref query-API throttling** forced discovery onto OpenAlex. OpenAlex indexing is
   broad but incomplete for very new conference proceedings, so a genuinely novel 2025–2026
   conference paper could have been missed.
3. **No replication.** None of the closest methods was reimplemented, so all
   "what it does NOT do" statements are based on abstracts and metadata, except where a local
   full text exists.

These limits are consistent with the project's own gate note that
"PASS on the constructed kernel cannot close empirical or novelty gates": G1 is closed
**for the searchable literature**, and the three items above are the explicit boundary.

---

## 7. Files produced and ledger policy

| File | Contents |
|---|---|
| `outputs/gates/G1_novelty_and_positioning_2026-09-15.md` | This report (tasks 1, 3, 4 + matrix) |
| `outputs/gates/G1_positioning_matrix.csv` | 26 works × 16 columns; CSV written with `QUOTE_ALL` |
| `outputs/gates/G1_verified_references.json` | 59 verified entries with verification method + evidence level |
| `sources/raw/g1/*.json` | Raw Crossref/OpenAlex responses and query specs (audit trail) |
| `scripts/g1_*.py` | Reproducible retrieval, verification, triage, matrix and reference builders |

**`sources/source_ledger.csv` was NOT modified.** Its schema is
`source_id,title,doi,url,authority,purpose,access_status_as_of_2026_09_15,critical_limit`.
It is **project-input-oriented** (it describes datasets and tools the project *uses*, with an
`authority` and `critical_limit` field), and it has **no field for verification method, DOI
evidence level, or a "not used as evidence" flag**. Appending 30+ literature records would
either force overloaded values into `authority`/`purpose` or make the ledger internally
inconsistent. Per the task instruction, these sources therefore live **only** in
`outputs/gates/G1_verified_references.json`, and the two existing literature rows already in
the ledger (S01 Weather-wise, S02 Kerkhove & Vanhoucke, S03 Zhou, S04 Elmachtoub, S21
Kerkhove thesis) are already correctly registered there and need no change.

⚠️ **Note for whoever extends the ledger later:** several verified DOIs in this body of
literature contain a literal semicolon (legacy AMS `2.0.CO;2` / `2.3.CO;2` suffixes). Any
naive comma/semicolon-splitting pipeline will corrupt them. Use a real CSV/JSON parser. The
matrix CSV is written with `QUOTE_ALL` for exactly this reason, and
`scripts/g1_build_matrix.py` carries a validation step.
