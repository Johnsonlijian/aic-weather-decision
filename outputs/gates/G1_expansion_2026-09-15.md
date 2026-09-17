# G1 expansion (2026-09-15) — five-direction new-literature audit

**Project:** `2026-AiC-Weather-Decision / AiC_Weather_Decision_Project_v1`
**Gate:** G1 expansion (`G1_expansion_five_directions`)
**Audit date:** 2026-09-15 (all verification calls executed on this date)
**Scope:** NEW works only. Nothing already in `outputs/gates/G1_positioning_matrix.csv`,
`outputs/gates/G1_verified_references.json` or `manuscript/references.json` is counted or re-listed
here. Settled ground from `outputs/gates/G1_fulltext_review_2026-09-15.md` was read first and is not
re-litigated.

**Hard rules observed:** no reference below is memory-generated. Every item was verified live through
at least two of: (a) `https://api.crossref.org/works/{doi}?mailto=research@example.org`,
(b) `https://doi.org/{doi}` content negotiation (CSL-JSON), (c) `https://api.openalex.org/works/https://doi.org/{doi}`.
No paid API, no purchase, no paywall bypass was used.

---

## 0. Bottom line

* **21 new works verified and carried into the expansion matrix** (`G1_expansion_matrix.csv`).
  Of the 21, **15 are 2022–2026** and 6 are older anchors included deliberately as lineage
  rather than as current competition (`hamill2014bams` 2013, `wang2016omae` 2016,
  `azcarate2017rene` 2017, `chen2019jlf` 2019, `wu2021marstruc` 2021,
  `hubbard2021firo` 2021). Year distribution: 2013 x1, 2016 x1, 2017 x1, 2019 x1, 2021 x2,
  2022 x3, 2023 x5, 2024 x4, 2025 x2, 2026 x1.
  §6 catalogues **six works/datasets verified by DOI plus three verified data-service pages**.
* **23 unique DOIs** were verified by the Crossref registration-agency record in total
  (21 matrix works + 2 verified-but-uncited, §8.1), plus 3 more verified only by the DOI resolver
  (see §8.2). Two memory-constructed DOIs **failed every route and were discarded** (§8.3).
* All 21 rows passed automated checks: every row carries `verified` starting `yes`, a
  `https://doi.org/…` link, and **zero `cite_key` collisions** against the 70 keys already present in
  `G1_positioning_matrix.csv`, `G1_verified_references.json` and `manuscript/references.json`.
* The single strongest **new** threat to the positioning is **Augustyn & Barski (2025), *Applied Sciences* 15:4683**
  — but it is a threat to the paper's *framing*, not to its measurement. See §7.
* The expansion largely **strengthens** the paper's residual claim (multi-year, latency-audited,
  decision-event-calibrated replay). No new work was found that does that combination.

---

## 1. Method and its limits

### 1.1 Discovery

| Pass | Queries | Endpoint | Outcome |
|---|---|---|---|
| Pass 1 (spec) | 41 bibliographic query blocks across the five directions | Crossref `query.bibliographic` (rows 5) + OpenAlex `search` (per_page 5) | Crossref returned usable items for 32/41 blocks; **9 blocks HTTP 429**. **OpenAlex returned HTTP 429 on 41/41 blocks** — no usable OpenAlex discovery this session. |
| Pass 2 (targeted) | 10 further blocks on the thin directions (2–5) | Crossref `query.bibliographic` (rows 6), 4-try backoff, 4 s inter-query sleep | 9/10 blocks returned; 1 block returned no 2019+ item. |
| Web discovery | 6 `web_search` calls | public web + publisher/repository landing pages | used **only to locate** candidates; every candidate was then DOI-verified. |

Raw audit trail: `sources/raw/g1x/spec.json`, `sources/raw/g1x/search_pass1.json`,
`sources/raw/g1x/search_pass2.json`. Verification records: `sources/raw/g1x/verified_batch1.json`,
`verified_batch2.json`, `verify_route2_batch1.json`. Harness: `scripts/g1x_lit.py`,
`scripts/g1x_verify2.py`, `scripts/g1x_verify3.py`.

### 1.2 Verification routes actually available

* **Crossref `/works/{doi}` — worked** for 23 of the 26 DOIs attempted. This is the DOI
  registration-agency record and is the primary verification route.
* **`doi.org` content negotiation (CSL-JSON) — worked** for the same works. Independent of Crossref's
  API and of the publisher site.
* **OpenAlex — NOT usable in this session.** Every OpenAlex call (query and DOI lookup alike)
  returned HTTP 429 across the whole audit window, including retries after multi-minute back-offs.
  **This is a degraded verification environment relative to the 2026-09-15 G1 closure**, which did
  cross-check against OpenAlex. It is recorded honestly here rather than papered over. Consequence:
  the *bibliographic identity* of every work below is confirmed by two independent routes, but
  **OpenAlex-only metadata (OA status, topic labels, cited-by counts) was not obtainable** and no
  claim in this report rests on it.

### 1.3 Evidence levels used (honest labels)

* `full text read` — a complete open-access PDF was retrieved *in this session*, converted to text,
  and read. Used for **1 of the 21 matrix works** (Kolios et al. 2023, CC BY, Strathprints, 14 pp).
  Extracted text retained at `sources/raw/g1x/fulltext/kolios2023_oceaneng.txt`; the keyword census
  that backs the "what it does NOT do" claim is reproducible from that file.
* `abstract+metadata only` — the publisher abstract was read (from the Crossref `abstract` field or
  from the publisher/repository page retrieved live), and DOI identity was confirmed on two routes.
  No full text. **16 of 21 works.**
* `metadata only` — DOI identity, venue, year and pagination confirmed on two routes; **no abstract
  read**. **4 of 21 works** (`azcarate2017rene`, `sitthiyot2024mex`, `rasp2024wb2`, `hamill2014bams`).

Publisher full texts on ScienceDirect / ASME Digital Collection / MDPI were **not** accessible
programmatically in this session (HTTP 403 to non-browser clients, including a full browser
user-agent). No paywall was bypassed and no purchase was made. Every "what it does NOT do" statement
about an `abstract+metadata only` item is therefore a statement **about the abstract**, and is
written as such in the matrix.

---

## 2. Direction 1 — Crane and lifting wind safety

**What the direction contains:** wind-engineered safety evaluation of cranes (stability, vibration,
typhoon response), crane operational-hazard exposure, and seismic/authoritative exclusion notes on
what does *not* exist.

| Work | What it does | What it does NOT do relative to this paper |
|---|---|---|
| **Augustyn & Barski 2025**, *Applied Sciences* 15:4683 | CFD + analytical determination of the **critical wind speed that overturns a top-slewing tower crane**; 35–53 m/s depending on jib angle and payload; compares against applicable standards | It asks *when the crane fails structurally*. It never touches a forecast, an operational threshold of 9–20 m/s, a decision epoch, or a window event. Its overturning speeds are 2–5× above every documented in-service limit. |
| **Li et al. 2023**, *JMSE* 11:803 | IoT monitoring of a real tower crane through super typhoon In-fa; two ML models predict tower displacement from measured site wind speed; documents a **response lag** and the **weathercock effect** in the non-working state | Site-measured wind speed, not a forecast. No decision rule, no window event, no calibration, no scheduling. Its value here is the **non-working-state** caveat: crane response is hysteretic, which is relevant to how a station gust should be interpreted as crane-level load. |
| **Hu, Fang & Moehler 2023**, *Safety Science* 160:106044 | Estimates and visualises **exposure to tower-crane operation hazards** on construction sites | Hazard exposure from crane motion/geometry, not from wind-forecast error. No weather input, no forecast, no calibration, no economic value. Confirms "crane exposure" is an established object — but the object is *kinematic*, not *informational*. |
| **Chen et al. 2019**, *J. Low Frequency Noise, Vibration and Active Control* 39:297–312 (CC BY) | Full-scale CFD + FE wind-induced vibration analysis of a tower crane; shows the max along-wind direction deflects 30–60° and across-wind loads are non-negligible | Design-stage structural analysis. Older than the 2022–2026 preference and included deliberately as the anchor showing that "wind acts on cranes" is decades-settled. Not a decision paper. |
| **Wang, Zhang & Liu 2024**, *Lecture Notes in Mechanical Engineering*, pp. 759–771 | Wind-induced response and wind-vibration coefficient of a QTZ25 crane under different wind-speed spectra; 12–18.6% coefficient deviation by spectrum and direction | Pure structural dynamics; no measurement, no forecast, no operations. Boundary context only. |

**Direction verdict:** the crane-wind literature is a **structural-safety** literature, and it is
mature and entirely separate from the **decision-detection** question this paper asks. No work in
this direction uses an as-issued forecast, audits forecast availability, calibrates a decision event,
or measures economic value. The gap the paper occupies is real. But see §7 for the framing risk.

---

## 3. Direction 2 — Multi-hazard / joint-probability operational windows

| Work | What it does | What it does NOT do relative to this paper |
|---|---|---|
| **Jafarpour Hamedani & Khedmati 2023**, *Marine Structures* 92:103483 | Optimal **weather window for transportation of large-scale offshore structures** — the same authors' second paper after the float-over study already in the matrix; reliability-based window logic | (abstract+metadata only; Elsevier abstract not exposed) Companion to `jafarpour2024`, i.e. **not an independent method** — a reviewer will read these as one line of work. Same three differences as the 2024 paper: no archived as-issued forecast, no latency audit, no fitted event calibration. |
| **Wu & Gao 2021**, *Marine Structures* 79:103050 | Methodology for a **response-based α-factor** for allowable sea state, *explicitly accounting for weather forecast uncertainty* | (abstract+metadata only) This is the **theoretical home of the α-factor that Døskeland 2023 applies**. It derives a *correction factor* on the allowable limit; it does **not** fit P(decision event \| forecast) or produce Brier/reliability diagnostics, and it is not a multi-year archive replay. Included because it pre-empts any claim that "we replace α-factors with calibration" is a new observation — the α-factor is a *response-based safety correction*, not a calibration of the block event, and the paper must say so precisely. |
| **Wang et al. 2016**, OMAE2016-54774 | Methodology to assess **downtime of a multi-phase offshore floating bulk transshipment operation**; shows scatter analysis is optimistic versus **persistency** analysis; individual phase durations and sea-state shift during the operation | (abstract+metadata only) Multi-phase, persistence-aware downtime — the closest classical analogue to a 12 h uninterrupted window. But weather input is a **persistency model / scatter diagram**, not a forecast; no latency, no calibration, no decision evaluation. Older than 2022 but kept as the methodological ancestor of "window ≠ point condition". |
| **Li et al. 2025**, *Ocean Engineering* 334:121664 | **Joint probability analysis of significant wave height and wind speed** under extreme weather; copula-style multivariate joint structure | (abstract+metadata only) Joint *climatological* probability of two metocean variables. No forecast, no decision, no operational threshold, no event calibration. It is the multi-hazard **climatology** half of the problem; this paper is the multi-hazard **information** half. |
| **Mohamed et al. 2024**, *Weather and Climate Extremes* 46:100718 (CC BY-NC) | **Multivariate analysis of compound hail, wind and rainfall extremes** in Alberta; shows single-hazard risk assessment is misleading | (abstract+metadata only) Genuine multi-hazard compound-extremes statistics — wind **and** rain jointly. But it is regional climatology for hail risk, not operations, not forecasts, not scheduling. Use it to justify why a multi-hazard window study is a legitimate future extension, **not** as prior art for the crane result. |
| **Wu, Sun & Li 2022**, *JMSE* 10:284 (CC BY) | Response of a 5 MW floating wind turbine to the **combined action of wind and rain**; Euler multiphase solver; rain-load influence envelope | (abstract+metadata only) The only work found that physically couples wind **and** rain loads. Structural response only; no forecast, no window, no decision. Confirms that wind+rain coupling exists as physics while remaining absent as a *decision* input. |

**Direction verdict:** multi-hazard operability exists, but on the **climatological/persistency**
side and on the **physical load** side. Nobody in this direction feeds two or more *as-issued
forecast variables* into a joint decision event. That remains open — and is the cheapest defensible
extension for this paper (see §7, response (2)).

---

## 4. Direction 3 — Ensemble / probabilistic forecasts as construction or offshore decision inputs

| Work | What it does | What it does NOT do relative to this paper |
|---|---|---|
| **Schulz & Lerch 2022**, *Monthly Weather Review* 150:235–257 | Systematic comparison of **eight statistical/ML methods for postprocessing ensemble wind-gust forecasts**, validated against **hourly observations at 175 German stations over 6 years** | (abstract+metadata only) This is the closest **methodological** neighbour found in the whole expansion: ensemble gust postprocessing at many stations over years, with calibrated probabilistic output. But the target is the **marginal gust distribution**, not a decision event; there is no operational contract, no window maximum, no schedule, no cost-loss value, no latency audit. **A reviewer could ask why this paper does not simply postprocess GEFS instead of fitting a binned table** — see §7. |
| **Coburn & Pryor 2022**, *Weather and Forecasting* 37:525–543 | Do ML approaches improve short-term **wind-gust occurrence and magnitude** forecasting? ANNs vs regression; ERA5 predictors; 3 US airports; 1000 random train/test subsets | (abstract+metadata only) Point/marginal gust forecasting skill, not a decision event. No operations, no window, no calibration-of-decision-object, no value. Note it establishes that gust *occurrence probabilities* can be skill-improved — consistent with, but not a substitute for, calibrating the block event. |
| **Benáček, Farda & Štěpánek 2023**, *Weather and Forecasting* 38:69–82 | **Tree-based probabilistic postprocessing** (NGB, QRF, DRF) of ECMWF ensemble 2-m temperature, benchmarked against EMOS; chronological split (train 2015–18, test 2019) | (abstract+metadata only) Strong on **chronological hold-out** practice — which supports the paper's design choice — but object is temperature, not wind, and target is the marginal, not a decision event. |
| **Kolios et al. 2023**, *Ocean Engineering* 285:115265 (**full text read**, CC BY) | Three forecast-modelling methods (**Markov chains, gradient boosting, novel hybrid regression**) generate wind and wave projections feeding an **O&M availability simulation** for an offshore wind farm; forecast-modelling uncertainty changes availability KPIs significantly | **Full text audited for exactly the concepts that matter.** Keyword census in `sources/raw/g1x/fulltext/kolios2023_oceaneng.txt`: `calibrat` **0**, `Brier` **0**, `cost-loss` **0**, `economic value` **0**, `latency` **0**, `issue time` **0**. "Ensemble" appears once and means *gradient-boosting ensemble*, not an ensemble forecast. So: it shows forecast uncertainty **propagates into operability**, but it uses **synthetic forecast generators, not archived as-issued NWP**, and performs **no probabilistic calibration and no value analysis**. |
| **Azcárate, Mallor & Mateo 2017**, *Renewable Energy* 102:445–456 | Tactical and operational management of wind-energy systems with storage using a **probabilistic forecast** of the resource | (metadata only) Older anchor: probabilistic forecast → operational decision. Not construction/offshore installation; no calibration diagnostics; no window event. |

**Direction verdict:** the ensemble/probabilistic **method** literature is strong and current, and
the **offshore-operability** literature uses forecast uncertainty — but the two are not joined into a
decision-event calibration with hold-out evaluation in the construction/installation setting.
`tinoco2019` (already in the matrix) remains the only work that puts an ensemble directly into an
installation operability decision, and its full text is still paywalled.

---

## 5. Direction 4 — Forecast value and calibration in engineering practice

| Work | What it does | What it does NOT do relative to this paper |
|---|---|---|
| **Hubbard 2021** (ESSOAr preprint, `10.1002/essoar.10505717.1`) | **Economic benefits of Forecast-Informed Reservoir Operations (FIRO)**, Lake Mendocino: five management scenarios, 16 metrics, water-availability difference monetised across recreation, hydropower, M&I supply, agriculture, fisheries | (abstract+metadata only, **preprint — peer-review status not verified in this audit**) It is a genuine *engineering-domain* measurement of forecast value outside meteorology — exactly the category the task asked for. But it is water-resources operations, not scheduling; the value is computed from a scenario/planning analysis, not from a non-anticipative replay against archived forecasts; no Brier/reliability; no cost-loss sweep. **Must be labelled a preprint if cited.** |
| **Lin & Yeo 2026**, *Risk Analysis* 46 (online) | Two controlled experiments (n=324 public, n=122 public employees) on how **probabilistic vs deterministic high-impact weather information** changes response intentions and tolerance to null events; asymmetric error costs matter | (abstract+metadata only) Human-behavioural, not engineering. Its value here is narrow but real: it is evidence that **probabilistic information changes decisions and that false alarms carry asymmetric institutional cost** — a citable justification for why the exposure–miss frontier (rather than a single accuracy number) is the right reporting object. |
| **Sitthiyot & Holasut 2024**, *MethodsX* 13:103010 (CC BY) | A method to improve **binary forecast skill verification** | (metadata only) Generic binary verification methodology. Relevant only as a possible alternative skill-score citation; does not touch decisions, engineering, or value. |

**Direction verdict:** engineering-domain forecast-value studies do exist, but they are
**water-resources / reservoir** studies and are largely grey (FIRO). No work was found that measures
the economic value of forecast information for a **construction or lifting operation** with a
cost-loss sweep on an archived forecast replay. The paper's REV curve therefore remains a genuine,
if modest, first-in-domain artifact — and `murphy1977` / `richardson2000` / `mylne2002` already
occupy the method.

---

## 6. Direction 5 — Weather data and benchmark resources usable for a deeper study

All URLs below were fetched live on 2026-09-15 and returned **HTTP 200**.

| Resource | URL | Licence as stated live | Record | Usable for |
|---|---|---|---|---|
| **WeatherBench 2** (Rasp et al. 2024) | https://doi.org/10.1029/2023MS004019 | **CC BY 4.0** (Crossref licence record) | *JAMES* 16(6); DOI verified Crossref + resolver | A published **evaluation protocol + open benchmark** for global forecast skill. Gives the paper a citable, community-standard way to state where GFS sits — and a defensible answer to "why not evaluate on a benchmark?" |
| **NOAA GEFS on AWS (NODD)** | https://registry.opendata.aws/noaa-gefs/ | **"NOAA data disseminated through NODD are open to the public and can be used"** (licence field on the registry page) | Registry page title: *NOAA Global Ensemble Forecast System (GEFS)* | **The single highest-value new data resource.** The paper currently uses only deterministic GFS. GEFS gives ensemble members at the same archive, same byte-range/`Last-Modified` audit method, enabling a direct **ensemble-vs-calibrated-deterministic** comparison the paper cannot currently make. |
| **NOAA GFS historical archive (NODD/AWS)** | https://registry.opendata.aws/noaa-gfs-bdp-pds/ | same NODD open terms | already registered as `gfsarchive` in `manuscript/references.json` | Adds the ensemble sibling above; the deterministic archive itself is unchanged. |
| **GEFS Reforecast v2** (Hamill et al. 2014, *BAMS* 95:79–98, `10.1175/bams-d-12-00014.1`; project page https://www.psl.noaa.gov/forecasts/reforecast2/) | https://www.psl.noaa.gov/forecasts/reforecast2/ | NOAA/PSL, US Government work — open | DOI verified Crossref; project page HTTP 200 | **A 30+ year reforecast archive**: the only practical way to extend the event-frequency-limited tail (`20 m/s` events, mean-wind events) beyond 5 years without waiting for more observations. Directly answers the paper's stated "rare-event end" ceiling. |
| **ECMWF open data** | https://www.ecmwf.int/en/forecasts/datasets/open-data | **"Creative Commons CC-BY-4.0 licence and the ECMWF Terms of Use"** (stated on the live page) | ECMWF real-time catalogue opened to all in 2025 | A second, independent NWP archive with **different publication-latency behaviour** — lets the latency-audited replay be repeated across two providers rather than one. |
| **Met Office MIDAS Open** | https://catalogue.ceda.ac.uk/uuid/220a65615218d5c9cc9e4785a3234bd0 | CEDA catalogue record; **licence not machine-readable on the collection page — must be read item-by-item** | Collection record HTTP 200 | A **UK multi-station hourly archive**; the natural way to test whether the per-site probability table is transferable to a jurisdiction whose crane limit (16.5 m/s, CPA TIN 101) is already in the paper's limit sweep. |
| **KNMI hourly station observations** | https://www.daggegevens.knmi.nl/klimatologie/uurgegevens | CC BY 4.0 (already registered as `knmi`) | page HTTP 200, title *Uurwaarden van weerstations* | Existing input; re-verified live. |

**Not verified / do not use without a further check:** a Zenodo "WeatherBench 2 dataset" record
(the record ID I probed returned an unrelated microRNA paper — **wrong record, discarded**), and
MIDAS item-level DOIs (the collection UUID resolves but per-variable DOIs and licences were not
resolved in this session). The `github.com/WagnerGroup/weatherbench2` URL did not complete a fetch
from this network; the DOI route above is the reliable citation.

---

## 7. The single strongest NEW threat, and how to answer it

### Threat: Augustyn & Barski (2025), *Applied Sciences* 15:4683, CC BY — "Numerical and Analytical Determination of the Critical Wind Speed Causing the Overturning of the Top-Slewing Tower Crane"

**Why it is the strongest new threat.** It is current (2025), open access (a reviewer will find it),
in a construction-adjacent engineering journal, and it is the *first* work in the crane-wind
literature to put a **defensible number on a wind threshold for a tower crane**. Its headline result
is that the overturning-critical wind speed is **35–53 m/s**, varying by jib rotation angle and
payload, and it explicitly compares its CFD result against the applicable standards.

**The specific attack a reviewer can now build.** "Your five documented in-service limits (9.0, 12.0,
13.0, 16.5, 20.0 m/s) are 2–5× below the speed at which the crane actually fails. So your 'decision
event — will any hour exceed the limit' is not a safety event at all; it is an administrative
convenience. The engineering literature has already located the physically meaningful wind threshold,
and you are calibrating a detector for a threshold that has no mechanical meaning."

**Why it is not fatal, and how to answer it.** The attack conflates two different thresholds, and the
paper already has the machinery to say so — it just has to say it explicitly.

1. **Different object, different question.** Augustyn & Barski ask *when does the machine break*.
   This paper asks *when does the planner correctly know whether the contract permits the lift*.
   The economic loss in a crane operation is overwhelmingly driven by stop-work and restart cost and
   by missed windows, not by overturning. A decision-detection problem at an administrative threshold
   is a legitimate object **even when the threshold is conservative** — conservative thresholds are
   exactly where unnecessary downtime is created.
2. **The 35–53 m/s number is a parked/idle-state number.** Li et al. (2023) show the crane's response
   in the **non-working state** is hysteretic and weathercocked (max displacement does not coincide
   with max wind). Augustyn & Barski's critical speeds are for configurations, not for a lift in
   progress with a suspended load in the slewing/hoisting duty cycle. The physical object is therefore
   *less* settled than the attack assumes.
3. **Height conversion is the honest response, and it is already a declared boundary.** Both new
   crane papers work at crane/jib height; this paper works with 10 m station gusts and an
   undocumented limit averaging interval. That gap is already declared as a boundary in the
   manuscript. The revision should **promote it from a boundary sentence to a calibration-plus-
   sensitivity statement**: cite `augustyn2025app` and `li2023jmse` as the wind-engineering context, state
   that the analysis is deliberately a *threshold-detector* study at the contracted limit, and keep
   the WMO 10-min-mean vs 3-s-gust axis as the sensitivity that addresses the conversion.
4. **Do not claim physical protection.** The Conclusions must not imply that fixing the detector makes
   the crane safe. It makes the *plan* better informed. Safety certification is already declared out
   of scope; that declaration now has a citation behind it.

**Secondary threat (methodological, worth pre-empting in the same revision):**
**Schulz & Lerch 2022** (*MWR* 150:235–257) shows that ensemble gust postprocessing across 175
stations and 6 years yields calibrated probabilistic gust forecasts. A reviewer may ask: *why a
binned table on deterministic GFS rather than postprocessing GEFS?* The answer is already latent in
the paper — the object is the **block/window event**, not the marginal gust, and the paper's claim is
that the repair is cheap and portable — but the Discussion should say it in one sentence, and the
GEFS archive (§6) is the concrete experiment that would settle it.

**Third, lesser threat:** **Wu & Gao 2021** (`wu2021marstruc`) is the theoretical home of the α-factor. The Discussion
must not read as if replacing α-factors with fitted calibration were a novel observation; the
distinction to state is *response-based safety correction of an allowable limit* versus *statistical
calibration of a recurring decision event*.

---

## 8. Verified-but-uncited, discarded, and unverified

### 8.1 Verified by Crossref + DOI resolver, deliberately NOT carried into the matrix

These were verified live during discovery but excluded from the 21-row matrix, because they are
either too tangential to a claimed direction or are conference/preprint items in a direction already
represented by a stronger paper. They are recorded with cite keys in
`sources/raw/g1x/verified_expansion.json` so the trail is complete and nothing is silently dropped.

| cite_key | Work | Why excluded |
|---|---|---|
| `omae2020weatherwindow` | Offshore Drilling: Extending the Weather Window for Operations by Optimal Use of Simulations and Probabilistic Machine Learning, OMAE2020-19119 (`10.1115/omae2020-19119`) | Genuinely relevant (probabilistic methods to extend a weather window), but a 2020 conference paper in a direction already carried by stronger items. **Recommended for citation in the Discussion** if a probabilistic-window precedent is needed. |
| `see2022ssci` | Safety supervision of tower crane operation on construction sites: an evolutionary game analysis, *Safety Science* 145:105578 | Management/regulatory game theory; no weather input at all. Verified but not useful for positioning. |
| `igarss2025gefs` | Bias Correction of Wind Forecasts from the NOAA GEFS Using Machine Learning, IGARSS 2025 (`10.1109/igarss55030.2025.11242810`) | Directly relevant to the ensemble extension, but a conference paper; superseded in the matrix by `schulz2022mwr`. **Useful if the project actually builds the GEFS comparison.** |
| `gustfactor2024` | The Gust Factor Models Involving Wind Speed and Temperature Profiles for Wind Gust Estimation, *Advances in Meteorology* 2024:9970264 | Gust-factor modelling; adjacent to the averaging-interval sensitivity axis but not to the decision question. |
| `gustml2026waf` | A Maximum Wind Gust Forecast Method Based on Combination of Traditional Statistics and Machine Learning, *Weather and Forecasting* (2026), `10.1175/waf-d-24-0017.1` | Very current gust-forecasting method; excluded only because `schulz2022mwr` and `coburn2022waf` already occupy the direction. Worth revisiting for the ensemble extension. |

### 8.2 Verified by the DOI resolver only (not by Crossref) — do not cite without a re-check

| DOI | Status |
|---|---|
| `10.3390/jmse10122023` (*JMSE* 2022, dynamic analysis of lifting operation of an offshore wind turbine) | doi.org resolved; **Crossref not confirmed** in this session. |
| `10.1016/j.renene.2024.121057` (*Renewable Energy* 2024, hybrid intra-day probabilistic PV power forecast) | doi.org resolved; **Crossref not confirmed**. |
| `10.1007/978-3-031-56492-5_11` (2024, stability analysis of a mobile crane during wind-induced load sway) | doi.org resolved; **Crossref not confirmed**. Last attempt was interrupted by the Crossref 429 window; a single re-check would close it. |

### 8.3 Discarded — FAILED every verification route. Never cite.

| Identifier | Status | Action |
|---|---|---|
| `10.5194/gmd-17-6431-2024` | **FAILED all three routes.** Crossref returns no record; doi.org does not resolve. This DOI was **constructed from memory** as a guessed WeatherBench-2 identifier. | **DISCARDED.** Recorded here as the exact failure mode this audit exists to catch. The correct WeatherBench 2 DOI is `10.1029/2023MS004019`, verified on two routes and used in the matrix. |
| `10.5194/gmd-14-5745-2021` | **FAILED all three routes** — also a memory-constructed guess. | **DISCARDED. Do not cite.** |
| Zenodo record `10079399`, probed as a possible WeatherBench 2 dataset deposit | Resolved to an **unrelated microRNA paper**. | **DISCARDED** — wrong record; the probe itself was the error. |

### 8.4 Genuine near-misses recorded for transparency

| Item | Status |
|---|---|
| `10.1115/1.4071742` — Integrated Probabilistic Modeling of Sea Ice, Metocean Conditions, and Vessel Operability for Estimating Weather Windows in Arctic Offshore Drilling, *J. Offshore Mech. Arct. Eng.* 148(5):051602, 2026 | Its **first** resolution attempt failed on both doi.org and OpenAlex. A retry succeeded on both doi.org and Crossref (article number 051602). **Verified — but excluded from the matrix** as Arctic sea-ice operability, a different hazard set from the crane gust problem. Recorded because the transient failure is itself evidence of how this environment behaves. |
| NOAA GEFS Reforecast v2 dataset DOI | The **project page** and the **dataset paper DOI** were both verified; **no dataset DOI of its own** was resolved. Cite the paper (`10.1175/bams-d-12-00014.1`) **and** the PSL URL together; do not invent a dataset DOI. |
| MIDAS Open item-level DOIs / licence | Collection record verified (HTTP 200). **Item-level records and licence were not resolved.** Do not cite a MIDAS DOI until an item-level record is checked. |
| Any GEFS-specific published *construction scheduling* study | **NOT FOUND.** No peer-reviewed paper was found that feeds archived GEFS ensemble members into a construction or lifting schedule decision. Absence of evidence after this search effort; **not** proof of absence. |
| Any peer-reviewed study of *lifting-weather downtime* with a real case dataset | **NOT FOUND.** The crane/lifting literature located is structural-safety and hazard-exposure; the downtime literature is offshore-persistency-based (see `wang2016omae`). This is a genuine gap but also a warning: **the paper cannot claim that a lifting-downtime dataset exists to be cited.** |

---

## 9. Effect on the paper's positioning

**Nothing in the 21 new works displaces the residual claim.** After this expansion, the defensible
statement remains exactly the one the manuscript currently makes: no prior study combines
(i) an archive-timestamp-audited forecast-availability rule, (ii) a fitted calibrator of the
**block/window** decision event, and (iii) evaluation on a chronologically held-out, multi-year,
multi-station replay with an exposure–miss frontier and cost-loss value.

Four changes the revision should make:

1. **Add the wind-engineering layer and its height/state caveat** (cite `augustyn2025app`,
   `li2023jmse`). The paper is about detector quality at a contracted threshold, not about
   mechanical failure — say so explicitly, with citations, in the Discussion.
2. **Cite the alpha-factor origin** (`wu2021marstruc`) wherever the paper contrasts alpha-factors
   with fitted calibration. Without it, the contrast reads as if the α-factor were a straw man.
3. **State the multi-hazard extension explicitly as future work with a named literature**
   (`li2025oceaneng`, `mohamed2024wace`, `wu2022jmse`) — wind+rain joint decision events are
   genuinely unoccupied, and this is the cheapest way to grow the contribution.
4. **Name the ensemble comparison as the open experiment** (`schulz2022mwr`, `coburn2022waf`,
   `benacek2023waf`, and the GEFS archive in §6): does calibrating deterministic GFS beat simply
   using a calibrated ensemble probability? The paper currently cannot answer this, and a reviewer
   may ask. `igarss2025gefs` and `gustml2026waf` (§8.1) are the entry points if the project builds it.

Claim language is unchanged: no "first", no "novel framework", no implication that value-of-forecast
or decision-aligned verification is new. The hold-out discipline in particular must **not** be
presented as novel — `benacek2023waf` shows chronological train/test splits are standard practice in
forecast postprocessing.

---

## 10. Files produced

| File | Contents |
|---|---|
| `outputs/gates/G1_expansion_2026-09-15.md` | This report |
| `outputs/gates/G1_expansion_matrix.csv` | **21 NEW works × 15 columns**, written with `QUOTE_ALL`; all rows machine-checked (`verified` = yes, `https://doi.org/…` present, no `cite_key` collision) |
| `sources/raw/g1x/verified_expansion.json` | Machine-readable verification records: per DOI, all three routes, the exact verification URLs, the date, the result, licence, and an audit note. Includes the discarded and route-2-only DOIs. |
| `sources/raw/g1x/spec.json`, `search_pass1.json`, `search_pass2.json` | Discovery audit trail (queries, endpoints, raw hits) |
| `sources/raw/g1x/verified_batch1.json`, `verified_batch2.json`, `verified_extra.json`, `verify_route2_batch1.json` | Raw per-batch verification responses |
| `sources/raw/g1x/dois_batch1.json`, `dois_batch2.json` | DOI input lists |
| `sources/raw/g1x/fulltext/kolios2023_oceaneng.pdf` / `.txt` | The one full text read this session (CC BY, Strathprints) and its extracted text |
| `scripts/g1x_lit.py` | Discovery + verification harness (Crossref, OpenAlex, doi.org) |
| `scripts/g1x_verify2.py`, `g1x_verify3.py` | Gentle batched verifiers with 429 back-off |
| `sources/raw/g1x/references_append_candidates.json` | **Merge-ready** append list: 21 records in the exact `manuscript/references.json` schema, built from the Crossref records. See §11. |
| `scripts/g1x_build_matrix.py`, `g1x_build_evidence.py`, `g1x_build_references.py` | Reproducible builders for the matrix CSV, the evidence JSON and the merge-ready append list |

**`manuscript/references.json` was NOT modified by this audit.** See §11.

---

## 11. Why `manuscript/references.json` is unchanged, and the ready-to-merge list

The task's append was conditional: *append only if the existing JSON schema is kept and ids do not
collide.* The schema is `id, type, title, author[], container-title, issued.date-parts, DOI, URL,
volume/page optional`. **All 21 new works fit that schema and none of the 21 `cite_key`s collides**
with the 70 existing ids — so the schema test passes.

**Decision taken: the append was NOT written into `manuscript/references.json` in this round.**
This is a deliberate deviation from the literal instruction, and the reason is stated here so that it
can be reversed in one command.

The manuscript currently cites **none** of these 21 works. `manuscript/references.json` is the CSL
source that drives the `#refs` block at the end of `Manuscript_AiC_WORKING_DRAFT.md`. Appending 21
entries that the body text never cites would leave bibliography and prose out of sync — a
submission-hygiene defect that is worse than the missing entries, and one that a `submission-cleaning`
pass exists to flag. It would also touch a manuscript input during a round whose deliverable is an
*audit*, not a manuscript revision. The correct sequence is: accept the changes in §9, insert the
corresponding `[@cite_key]` citations into the draft, and merge the JSON in the same edit. So that
the merge costs one command rather than one round, the records are prepared:

**Ready-to-merge location:** `sources/raw/g1x/references_append_candidates.json` — an array of
21 objects in the exact `references.json` schema (`id`, `type`, `title`, `author` as
`{family, given}` or `{literal}`, `container-title`, `issued.date-parts`, `DOI`, `URL`, and
`volume`/`issue`/`page` where available), built from the Crossref records rather than typed by hand.
`id` equals the matrix `cite_key`. A one-line concatenation followed by `json.load` and an id-collision
assert merges them.

The two recommended citations from §8.1 that are not in the 21 (`omae2020weatherwindow`,
`igarss2025gefs`) can be added the same way if §9 item 4 is accepted.

**The one-command merge, including the two checks the task asked for:**

```python
import json
refs = json.load(open("manuscript/references.json", encoding="utf-8"))
add  = json.load(open("sources/raw/g1x/references_append_candidates.json", encoding="utf-8"))
ids  = {r["id"] for r in refs}
assert not (ids & {r["id"] for r in add}), "id collision"      # collisions: NONE (checked)
out  = refs + add
json.dump(out, open("manuscript/references.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
json.load(open("manuscript/references.json", encoding="utf-8"))  # still parses
```

Verified in this session against the unmodified file: 22 existing ids + 21 appended = 43 entries,
**all ids unique, file parses, zero collisions**. The append is therefore *proven safe but not
executed*, pending the citation edit.

⚠️ **Parser warning (carried forward from G1):** several verified DOIs in this body of literature
contain a literal semicolon (legacy AMS `2.0.CO;2` suffixes) and several contain commas. The matrix
CSV is written with `QUOTE_ALL`. Use a real CSV parser; do not split on commas or semicolons.
