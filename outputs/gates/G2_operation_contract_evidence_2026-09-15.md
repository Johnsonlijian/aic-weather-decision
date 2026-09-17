# G2 operation-contract evidence audit — 2026-09-15

**Project:** `2026-AiC-Weather-Decision\AiC_Weather_Decision_Project_v1`
**Gate:** G2 (complete operation contract) — previously `OPEN`
**Verdict after this round:** **G2 moves from `OPEN` to `PARTIAL_CLOSED_FOR_TWO_OPERATIONS_TWO_OPEN_FIELDS`**

What closed: both chosen operations now have a citable numeric threshold, a stated physical
quantity, a named measurement location, a documented exceedance response, a documented safe
terminal state, and a documented resource-hold rule. For OP02 the required uninterrupted
duration, the interruption prohibition and the recovery duration are all documented. In addition,
a **mandatory full-text Chinese code** (GB 55034-2022) was found that sets a code-level numeric
crane wind limit with a **stated height** — so the contract can now cite a code number, not only
a manufacturer rating.

What did **not** close: (a) **no crane source anywhere states the averaging interval** attached
to a crane wind limit (though the Chinese chain documents that the alarm quantity is
*instantaneous*); (b) **no published duration exists for one segmental lifting cycle**. Both are
carried as explicit swept parameters, not as asserted values.

Date every locator below was checked: **2026-09-15**.

---

## 1. The two operations chosen, and why

### OP01 — Tower-crane lifting and placement of a precast concrete deck segment

Chosen because this is the operation the project already used and it is the weakest gate. It is
now supported by a **primary manufacturer manual** for the number rather than by a media account,
and — importantly — by **two independent jurisdictions that document the absence of a code
number**:

| Role | Source | What it establishes |
|---|---|---|
| Numeric limit | S23 Yongmao STT293 Operation & Service Manual | in-service max **20 m/s**, out-of-service max **50 m/s** |
| Conservative alternative | S24 CPA TIN 101 | UK industry recommended out-of-service point **16.5 m/s** for tower cranes |
| Why no code number exists | S25 DGUV Vorschrift 52 § 30(6)1 + DA | German regulation **delegates** the numeric limit to the crane manufacturer's *Betriebsanleitung* |
| Why no code number exists | S26 29 CFR 1926.1435(b)(4)(iii) | US federal rule **delegates** to manufacturer, else a qualified person; 1926.1417(n) makes it a competent-person duty |

That triad is the defensible answer to "why 20 m/s and not some code value": **there is no code
value.** Recording that explicitly converts the project's biggest apparent weakness into a
documented finding.

### OP02 — Match-cast precast segment epoxy jointing (material-cure operation)

Chosen because it is the **only** operation found whose contract is fully published, and it
supplies exactly the fields OP01 lacks: a numeric **non-preemptive duration**, a documented
**interruption prohibition**, a documented **24-hour recovery**, a documented **resource hold**
and a documented **safe terminal state**. It also replaces a fabricated lift duration with a real
material constraint (S27 VDOT IIM-S&B-91, incorporating FDOT Specifications 452/453).

A third operation, **OP03 concrete placing/delivery** (S28 GB 50666-2011), is *reported as
evidence* but **not proposed as a simulated operation**: its governing quantity is the mixture
temperature at placing, measured *inside the material*, which no weather forecast can supply.
Only its multi-day ambient regime trigger is ex-ante forecastable.

---

## 2. Task 1 — tower-crane / lifting wind limits: what is actually citable

### 2.1 Documented numeric limits

| # | Value | Refers to | Whose requirement | Locator |
|---|---|---|---|---|
| 1 | **20 m/s** | max wind speed for **operating** (in-service) | **manufacturer** rating, one model | S23 Ch. 2.1 item 4; restated S23 Ch. 3.4; alarm duty S23 § 3.4.1(h), § 3.4.2, § 10.7.3.2 |
| 2 | **50 m/s** | max wind speed **out of service** (storm) | **manufacturer** design state | S23 Ch. 2.1 item 4 |
| 3 | **13 m/s** | limit for **slewing-brake use / precision hoisting** and for **releasing rail clamps** | **manufacturer**, crane-function specific | S23 § 2.4 item 1(c); § 3.4.1(c); § 10.7.3.2; § 10.7.4.1 (potentiometer W1) |
| 4 | **16.5 m/s** (38 mph) | **UK industry recommended** speed at which tower cranes must be taken out of service | **trade-body recommendation**, produced with crane suppliers, major contractors and HSE | S24 CPA TIN 101 Issue A (04.12.09) p.1 |
| 5 | **~20 m/s** (45 mph) | **in-service design** wind speed normally assumed for tower cranes | industry statement, used as the design baseline | S24 p.1 |
| 6 | **14 m/s** (31 mph) | **mobile-crane duty-chart** maximum, "frequently well below this value" | manufacturer duty chart, per make/model/rig | S24 p.1 |
| 7 | **7 m/s** (16 mph) | max wind for **personnel carriers (man-riding baskets)**, all crane types | reported by S24 as a **BS 7121-1:2006** provision | S24 p.1 note — **SECONDARY**: BS 7121-1 was NOT obtained; the 2016 edition is not confirmed |
| 8 | **9.0 m/s** at the **highest point of the machine** | crane **installation and dismantling** must stop | **mandatory full-text Chinese code** (强制性工程建设规范 — every clause mandatory, prevails over older JGJ/GB standards) | S35 GB 55034-2022 § 3.4.7 |
| 9 | **12.0 m/s** | **open-air lifting** must stop (露天起重吊装作业) | Chinese industry standard | S36 JGJ 33-2012 § 4.1.15 |
| 10 | **10.8 m/s** | **concrete placing boom** (布料机) must stop | Chinese industry standard | S36 JGJ 33-2012 § 8.10.8 |
| 11 | **12.0 m/s** at max (installation) height | tower-crane **installation/dismantling** and **normal use** | Chinese industry standard | S37 JGJ 196-2010 § 3.4.8, § 4.0.9 |
| 12 | **13.0 m/s** at max installation height | tower-crane **installation / dismantling / section change** | Chinese national standard, **superseded by #8** | S38 GB 5144-2006 § 10.2 |
| 13 | **force 6 and above** = the code's own **10.8–13.8 m/s** | **all open-air climbing and suspended work at height** | Chinese industry standard; **mean-defined** (Beaufort) | S40 JGJ 80-2016 § 3.0.8 + its own 条文说明 |

**Rows 8–13 are new in this round and they change the picture materially: there *is* a code-level
numeric wind limit in at least one jurisdiction, and it is mandatory.** GB 55034-2022 is a
full-text mandatory technical code; the Chinese model of 强制性工程建设规范 makes every clause
mandatory and gives it precedence over the older JGJ/GB standards. Anyone who claims "no code
anywhere sets a crane wind number" would now be wrong — the correct statement is narrower:
**no European, UK or US code sets one; the Chinese chain does, and it governs installation and
dismantling (9.0 m/s) and open-air lifting (12.0 m/s) separately.**

**Crucially, this does NOT give the paper a clean start/continuation pair.** JGJ 33-2012's
9.0 m/s (installation/dismantling) and 12.0 m/s (open-air lifting) are two **adjacent activities**,
not two phases of one continuous activity. This must be written up as *state-dependent wind
contracts are real and code-level*, **not** as *here is a code start/continuation asymmetry*.

### 2.2 The critical distinction: in-service vs out-of-service (storm)

This is not a footnotes matter; it is the difference between a work decision and an asset state.

* **In-service** = the crane is lifting. Governing values: 20 m/s (S23), or 16.5 m/s as the
  conservative UK industry recommendation (S24).
* **Out-of-service / storm** = the crane is parked, hook raised, trolley at the jib foot,
  weathervane effect engaged so the jib slews freely (S23 § 3.4.3; corroborated in a second
  jurisdiction by S25 DGUV 52 § 30(6)2). Governing value: 50 m/s (S23).
* The securing **duty** is also documented: secure the crane *in good time, at the latest on
  reaching the crane-critical wind speed and at the end of work* (S25 § 30(6)1).
* The out-of-service value **must never authorise a work start.** In the machine-readable
  contract it is encoded as a boolean crane-asset state with `authorises_work_start: false`.

### 2.3 What is a hard code requirement, and what is not

**In Europe, the UK and the US, no numeric crane wind limit was found in any national
construction-safety regulation.** Two independent confirmations:

* S25 DGUV Vorschrift 52 § 30(6)1 requires the crane not to be operated beyond *"die vom
  Kranhersteller festgelegten Grenzen"* — the limits **set by the crane manufacturer**. The
  associated *Durchführungsanweisung* states those limits are given in the manufacturer's
  operating manual, possibly in the load chart. **No number appears in the regulation.**
* S26 29 CFR 1926.1435(b)(4)(iii): *"Wind must not exceed the speed recommended by the
  manufacturer or, where manufacturer does not specify this information, the speed determined by
  a qualified person."* 29 CFR 1926.1417(n) makes it a competent-person duty to *"adjust the
  equipment and/or operations to address the effect of wind, ice, and snow on equipment stability
  and rated capacity."* **No number appears in the regulation.**
* S39 GB 6067.1-2010 § 17.1 k) does the same in China for in-service operation: it prohibits
  operation above the manufacturer's maximum working wind speed and fixes **no code number**.

**But China does set numbers, and they are mandatory** (table rows 8–13 above). The precise
statement is therefore:

> No European, UK or US code sets a numeric crane wind limit; all three delegate it to the crane
> manufacturer. The Chinese mandatory code and industry standards **do** set numeric limits, at a
> **stated height**, and set them **differently for installation/dismantling (9.0 m/s) than for
> open-air lifting (12.0 m/s)**.

So: **20 m/s is a manufacturer's in-service rating, 16.5 m/s is a UK industry recommendation, and
9.0 / 12.0 m/s are Chinese code values for different activities. None of them is "the" limit**,
and the paper must not present any single one as such. Anyone writing "no code anywhere sets a
crane wind number" would now be wrong; anyone writing "the code requires 20 m/s" would also be
wrong.

This spread is not a weakness to hide — it is the argument for sweeping the threshold. The
cross-jurisdiction table (9.0 → 20 m/s) is a first-class object in the spec JSON under
`cross_jurisdiction_wind_limit_spread`, explicitly annotated *do not pool into one mean*.

**One scope trap to avoid.** JGJ 33-2012's 9.0 m/s (installation/dismantling) and 12.0 m/s
(open-air lifting) look like a start/continuation pair but are two **adjacent activities**, not
two phases of one continuous activity. Write it up as evidence that *state-dependent wind
contracts are real and code-level*, never as *a code start/continuation asymmetry*.

Secondary corroboration that the familiar 20–22 mph figure is practice, not law: S34 (ASCC,
Nov 2025) states there is *"no substitute for reviewing the actual manufacturer recommendations"*
and that manufacturers may specify different maximum allowable wind speeds by model, size and
operation. S33 (ASME B30.5) is cited by two secondary sources as requiring crews to lower,
retract and secure the boom when the manufacturer's or site-specific limit is met — recorded as
**SECONDARY ONLY**; the standard was not obtained.

Secondary corroboration that the familiar 20–22 mph figure is practice, not law: S34 (ASCC,
Nov 2025) states there is *"no substitute for reviewing the actual manufacturer recommendations"*
and that manufacturers may specify different maximum allowable wind speeds by model, size and
operation. S33 (ASME B30.5) is cited by two secondary sources as requiring crews to lower,
retract and secure the boom when the manufacturer's or site-specific limit is met — recorded as
**SECONDARY ONLY**; the standard was not obtained.

### 2.4 Standards that could NOT be read

`EN 13001-2`, `ISO 4302`, `FEM 1.001`, `FEM 1.005`, `BS 7121-1:2016` and `BS EN 14439` are
paywalled. **No clause number, table value or numeric threshold from any of them appears
anywhere in this contract.** The only statement attributable to that family is S24's: that
mobile-crane duty-chart maxima are normally around 14 m/s and *frequently well below*, i.e. that
manufacturer limits sit below the design in-service wind speed. That is attributed to **S24**, a
trade-body note, **not** to EN 13001-2. Do not upgrade this attribution later without reading
the standard.

---

## 3. Task 2 — material-related weather restrictions: what is actually citable

### 3.1 OP02 epoxy jointing (S27 VDOT IIM-S&B-91, 13 Dec 2016) — the complete operation

| Field | Documented value | Locator |
|---|---|---|
| Substrate temperature window | **40 °F to 115 °F**, both mating surfaces | § 453-5.3 |
| Hot-weather stop | substrate **> 115 °F → do not proceed**; shade/wet permitted but no free moisture at application | § 453-5.7.1, § 453-5.2 |
| Cold-weather route | artificial enclosure; raise **entire** joint surface to **≥ 40 °F**; cap **95 °F** at any point; no direct flame heating | § 453-5.7.2 items 2–3 |
| Air-temperature gate | may proceed if air temperature **above 45 °F and rising** | § 453-5.7.2 closing sentence |
| Post-join hold | substrate **40–95 °F for at least 24 hours after joining** | § 453-5.7.2 item 4 |
| Non-preemptive window | elapsed mixing→contact-pressure must not exceed **70 % of the open time** | § 453-5.1, § 453-5.6 |
| Open time | normal-set **60 min minimum**; slow-set **6 h minimum** | § 453-4.5.2 |
| Application limit | batch applied to the joint face within **20 min** of combining components | § 453-5.4 |
| Contact pressure | **≈ 40 psi**, uniform, maintained through cure; must not be reduced until cured | § 453-5.1, § 453-5.6 |
| Surface dryness | no free moisture — "a dry rag, after being wiped over the surface, becomes damp" | § 453-5.2 |
| Failure response | exceeding the 70 % limit **or** an incompletely filled joint ⇒ **separate the segments** and remove all epoxy | § 453-5.6, § 453-5.8 |
| **Recovery duration** | **24 hours** before epoxy may be re-applied | § 453-5.8 |

**Derived value, flagged:** the usable window **42 minutes = 70 % × 60 minutes**. This is *our
arithmetic on two documented numbers*, tagged `DOCUMENTED_LIMIT_OUR_ARITHMETIC`, with both
parents printed beside it. The slow-set analogue is 4.2 h from the documented 6 h minimum.

### 3.2 OP03 concrete placing (S28 GB 50666-2011) — reported, not simulated

| Field | Documented value | Locator | Forecastable? |
|---|---|---|---|
| Mixture temperature at placing (入模温度) | **≥ 5 °C and ≤ 35 °C** | § 8.1.2, invoked again by § 10.3.5 | **No** — measured in the material |
| Discharge temperature, winter (出机温度) | should not be **< 10 °C**; **< 15 °C** for ready-mixed / long-haul | § 10.2.7 | No |
| Winter regime trigger | outdoor **daily mean** air temp steadily **< 5 °C for 5 consecutive days** (exit: > 5 °C for 5 days) | § 10.1.1 | **Yes — with hysteresis** |
| Hot-weather regime trigger | outdoor **daily mean** air temp **≥ 30 °C** | § 10.1.2 | Yes |
| Rain gate | 小雨/中雨: open-air placing **should not** proceed and large-area open-air placing **shall not start**; 大雨/暴雨: open-air placing **shall not** proceed | § 10.4.4 | Categorical only — **no mm/h boundary in this code** |
| Standing water | drain before placing | § 10.4.6 | — |
| Layer temperature | already-placed layer **≥ 2 °C** before covering | § 10.2.10 | No |
| Striking criteria | surface temp **not above 5 °C** and freezing-critical strength reached; insulation immediately if surface−ambient **> 20 °C** | § 10.2.15, § 10.2.16 | Partly |
| Curing duration driver | **strength** criterion (30 % / 40 % of design strength, or 4.0 / 5.0 MPa by temperature band) — **not a time** | § 10.2.12 | No |

**Important honest statement:** GB 50666-2011 winter concreting is governed by a **strength**
criterion, not a duration. Converting § 10.2.12 into a task duration requires a maturity model
that the current event engine does not implement. This is recorded as an open issue, not papered
over.

**The 冬期施工 definition** the project needs as a date-window trigger is documented precisely
at **§ 10.1.1**: *outdoor daily mean air temperature steadily below 5 °C for 5 consecutive days*.
Its commentary notes the phrase was imported from meteorological practice. The code does **not**
fix the station or the spatial averaging of the daily mean — that is our choice and is declared
as such.

### 3.3 Cross-check on the lower temperature bound

S27 gives **40 °F (4.4 °C)** for epoxy substrate; S28 § 8.1.2 gives **5 °C (41 °F)** for concrete
placement. Two independent sources land within about 0.6 °C of each other on a lower material
temperature bound. That is a genuine corroboration and worth one sentence in the manuscript.
It is **not** a claim that the two limits are the same physical requirement — they govern
different materials and different failure modes.

### 3.4 ACI — what was and was not obtained

ACI preview PDFs were fetched (ACI 305R-20, 306R-16, 301-20) but the **numeric clauses fall
outside the free preview**. The only ACI facts used are from the readable front matter of
**ACI 305R-20**:

* Notation defines **V** as average wind speed measured at **20 in. (0.5 m) above the concrete
  surface**, and **W** as mass of water evaporated in **lb/ft² (kg/m²) per hour**. (ACI 305R-20,
  Ch. 2.1 Notation, preview p. 5.)
* § 1.1 states a maximum as-placed concrete temperature is often specified, and that placement in
  hot weather is too complex to be handled by such a maximum alone. (ACI 305R-20 § 1.1, p. 2.)

**No ACI numeric limit (e.g. any evaporation-rate threshold) is recorded**, because none was
read in a source. S28's commentary independently reports ACI 305R-99's 100 °F (38 °C) 24-hour
initial-curing figure and its 10–15 % 28-day strength penalty — that is a **secondary** citation
inside the Chinese code, and is labelled as such.

---

## 4. Task 3 — duration and temporal support: the averaging-interval problem

### 4.1 What the meteorological standard actually says (S29, WMO CIMO Guide)

| Fact | Locator |
|---|---|
| Averaged quantities are averaged over a period of **10 to 60 min**; the Guide deals mainly with **10-min intervals**, "as used for forecasting purposes" | Ch. 5 § 5.1.1 |
| "Averaging periods shorter than a few minutes do not sufficiently smooth the usually occurring natural turbulent fluctuations of wind; therefore, **1 min 'averages' should be described as long gusts**" | § 5.1.1 |
| **Peak gust** is the maximum observed wind speed over a specified time interval; with hourly weather reports it refers to the wind extreme in the last full hour | § 5.1.1 |
| **Gust duration** is defined by the response of the measuring system; extremes behind a running-average filter with integration time *t*₀ are peak gusts of duration *t*₀ | § 5.1.1 |
| The standard synoptic reporting average is **10 min**; wind speed reported to 0.5 m s⁻¹ resolution | § 5.1.2 |
| The **3 s peak gust** and the standard deviation are the two routine gustiness variables | § 5.1.3 |

### 4.2 Is the gust or the 10-minute mean governing for cranes?

**Not explicitly stated by any source that fixes a crane limit.** S23, S24, S25, S26 and the
Chinese codes S35–S38 all state or delegate a *magnitude* without naming the averaging period
(the Chinese codes do state a **height**; none states an interval). But the Chinese chain does
document the *annunciated* quantity, and that is informative:

| Fact | Locator |
|---|---|
| The Chinese national lifting code requires tall outdoor cranes to carry a wind alarm that **displays the instantaneous wind speed** (瞬时风速) | S39 GB 6067.1-2010 § 9.6.1.2 |
| The anemometer must be mounted at the **windward position on the upper part** of the crane | S39 GB 6067.1-2010 § 9.6.1.1 |
| The **only** published averaging window found anywhere in the lifting chain is the mean gust speed over a **3-second** interval (3 s时距内的平均阵风速度) — and it sits in a **draft for comment** | S42 GB 6067.3-202X § 10.3.3 — **DRAFT, NOT IN FORCE, never citable as a requirement** |
| The one Chinese rule that **is** mean-based stops work at height at **Beaufort force 6**, which the code itself converts to 10.8–13.8 m/s; Beaufort force is defined on a **mean** wind speed | S40 JGJ 80-2016 § 3.0.8 + commentary; the mean definition is in S30 |

**Conclusion — resolved in the negative.** Across four crane-wind families (the Chinese code
chain, the German regulation, the US regulation, and one manufacturer manual plus one UK trade
note), **not one states the averaging interval of the limit value**. Three of the four imply or
state a *short-duration* quantity — Chinese instantaneous display, plus a 3-second draft interval
— and **none states a 10-minute mean**. This materially strengthens the conservative default of
treating the forecast gust as the governing quantity.

**But do not over-claim.** This is *inference from what the instruments display*, not a documented
equivalence. In particular:

* do **not** write that any code specifies a 3-second gust limit for cranes — S42 is a draft;
* S39 specifies an instantaneous **display**, which does not by itself define the averaging window
  of the limit;
* S40 is genuinely mean-based, so the Chinese chain is **internally inconsistent** on this point,
  which is itself worth one honest sentence in the paper.

Three honest consequences:

1. This must be written as a **measurement mismatch**, not resolved by assumption: the contract
   compares a forecast **gust** field against a crane limit whose **averaging interval is
   unknown**.
2. The defensible default is the **conservative** one — treat the forecast gust as if it were the
   governing quantity — and **sweep** the treatment as a parameter
   (`avg_interval_treatment ∈ {gust_as_governing, 10min_mean_proxy, interval_unknown_swept}`).
3. Report the **internal tension** between the Chinese instantaneous-alarm rule (S39) and the
   Chinese Beaufort-mean work-at-height rule (S40) rather than picking whichever suits the result.

### 4.3 Numerical weather prediction gust output is not a 10-minute mean

This is now backed by the project's *own* decoded metadata, which is the strongest possible
evidence because it is reproducible:

| Variable | Decoded semantics | Locator |
|---|---|---|
| KNMI **FX** | "maximum wind speed during the preceding hour" | `data/raw/knmi_260_20250101_07.txt.metadata.json`, field `warning`: *"FX is preceding-hour maximum, not instantaneous launch-time gust"* |
| NOAA GFS **GUST** | `GRIB_COMMENT = "Wind speed (gust) [m/s]"`, `GRIB_ELEMENT = GUST`, PDT 0, surface; project metadata records `temporal_support: "instantaneous forecast; not the KNMI preceding-hour maximum"` | `data/raw/gfs_pilot/gfs_20250111_06_f006_gust.grib2.metadata.json` |

So the project holds **three different temporal supports** — a preceding-hour maximum (FX), an
instantaneous gridded gust forecast (GFS GUST), and an unknown-interval crane limit — and the
smoke pair in `outputs/weather_semantics_probe.json` already shows them disagreeing
(GFS 21.11 m/s vs KNMI FX 17.0 m/s at the same valid time, a 24 % gap) on a single pair.

**What this means for the contract:**

* The GFS→limit mapping is a **calibration problem**, not a subtraction. Build and report the
  mapping (e.g. GFS gust → KNMI-FX-class preceding-hour maximum), fit it on the **training split
  only**, and **propagate its residual into the decision**. Subtracting the two fields and
  calling the difference a standard error would be wrong.
* Never present a GFS-gust exceedance as a 10-minute-mean exceedance.
* Report the three-way temporal-support mismatch as a stated limitation of the whole experiment.

### 4.4 Measurement height and the documented height correction

S24 p.2 documents both the problem and the correction:

* "most weather forecast wind speeds are for a height of **10 m above ground** and should be
  corrected for greater heights";
* in open countryside the multipliers are **1.00 (10 m), 1.10 (20 m), 1.17 (30 m), 1.22 (40 m),
  1.26 (50 m), 1.29 (60 m), 1.32 (70 m), 1.35 (80 m), 1.37 (90 m), 1.39 (100 m)** … to 1.47 (150 m);
* in city centres the **gust** wind speed at 100 m is approximately **twice** that at pedestrian
  level, excluding nearby-building effects.

S23 requires an anemoscope when working height **> 50 m** but does **not** state the sensor
height. The contract therefore applies a documented height correction and exposes the multiplier
as a sensitivity parameter — it does **not** claim to know the manufacturer's reference height.

### 4.5 Documented requirements to stop and secure when limits are approached or exceeded

| Requirement | Locator |
|---|---|
| At 20 m/s the anemoscope raises **audible and visual alarm** and **"the tower crane must stop working"** | S23 § 3.4.1(h); § 3.4.2; § 10.7.3.2 |
| The operator must **monitor wind constantly** and take the crane out of service **before** the limiting speed is reached | S24 p.2 |
| Lifts must **not be started in rising winds**; note anticipated wind speeds from site-specific forecasts during lift planning | S24 p.2 |
| The **operator's** decision to take the crane out of service **must not be overridden** by site management | S24 p.1 |
| Above 13 m/s the slewing brake must not hold the jib; it must be free to weathervane | S23 § 3.4.1(c); § 10.7.3.2 |
| Secure the crane **in good time, at the latest on reaching the crane-critical wind speed and at the end of work** | S25 § 30(6)1 |
| On a **local storm warning** the competent person must decide whether to implement the manufacturer's securing recommendations | S26 29 CFR 1926.1417(h) |
| Exceeding **70 % of the epoxy open time** triggers **immediate separation and cleaning** of the segments | S27 § 453-5.6 |
| Exceeding **115 °F** substrate ⇒ **do not proceed** with epoxy jointing | S27 § 453-5.7.1 |
| Standing water in the form ⇒ **drain before** placing concrete | S28 § 10.4.6 |

---

## 5. Task 4 — the implementable operation contract (our modelling decision)

The full machine-readable specification is **`outputs/gates/G2_operation_contract_spec.json`**,
with a provenance tag on **every** numeric field. Summary of the decision logic:

### OP01 start rule

```
may_start(OP01) at hour t  ⟺
      no rising-wind flag on the forecast window        # S24 documented procedure
  AND max(wind(t .. t + lift_duration)) ≤ L_start       # L_start = 20 m/s (S23), or 16.5 m/s (S24 variant)
  AND crane_asset_state == IN_SERVICE                   # 50 m/s out-of-service state never authorises work
```

* `lift_duration` is **NOT_ESTABLISHED** — a swept parameter, default 1.0 h, range 0.5–4.0 h.
* The start rule is applied **only to not-yet-started tasks**.

### OP01 continuation rule

```
may_continue(OP01) at hour t  ⟺  wind(t) ≤ L_cont        # L_cont = 20 m/s (S23)
```

* **There is no start/continue asymmetry in the sources for a tower crane.** S23 gives one
  number. The HS2 11.1/20 m/s asymmetry is retained **only as motivation** and is excluded from
  the machine-readable contract.
* Exceeding `L_cont` ⇒ **load set down, task returns to NOT_STARTED with no partial credit**, and
  the documented safe terminal state is executed (hook up, trolley to jib foot, weathervane
  engaged, power off).
* Restart delay after a wind stop: **ASSUMED 0 h, swept to 2 h** (nothing documented).
* Stop margin below the limit: **ASSUMED 0 m/s, swept to 2 m/s** (S24 documents a duty to act
  early but gives no number).

### OP02 start rule and the non-preemptive window

```
may_start(OP02) at hour t  ⟺
      substrate_temp ∈ [40, 115] °F                      # S27 § 453-5.3 (documented)
  AND surfaces dry (no free moisture)                    # S27 § 453-5.2 (documented)
  AND (air_temp > 45 °F and rising)                      # S27 § 453-5.7.2 (documented, cold-weather route)
  AND segments within ~18 in of final position           # S27 § 453-5.4 (documented)
  AND a non-preemptive slot of open_window is available  # 42 min normal-set (documented × documented)
```

* Once started, **interruption is not permitted** until contact pressure is applied and held
  (S27 § 453-5.6).
* Cold-weather route adds a documented **24-hour post-join hold** at 40–95 °F during which the
  erection equipment and crew are **held** (S27 § 453-5.7.2 item 4) — a genuine multi-hour
  resource occupancy, modelled as such, not as a cost penalty.
* Failure to complete inside the window ⇒ segments separated, **documented 24-hour recovery**
  before re-application (S27 § 453-5.8).

### What "safe terminal state" means, precisely

Per operation, the terminal state is the **documented** securing/completion condition, not a
modelled convenience: for OP01 (S23 § 3.4.3, corroborated by S25 § 30(6)2) load released, hook
raised, trolley at jib foot, weathervane engaged, power off, travelling crane anchored on four
rail clamps; for OP02 (S27 § 453-5.6) joint filled, extruded epoxy bead visible along the exposed
joint edges, contact pressure maintained to cure, internal ducts swabbed. The distinction that
matters for the simulation: **OP01's interruption is recoverable from a clean state; OP02's is
not, and costs 24 documented hours.**

---

## 6. Explicit DOCUMENTED vs ASSUMED table

### 6.1 Fields that are DOCUMENTED (with locator)

| Operation | Field | Value | Locator |
|---|---|---|---|
| OP01 | in-service wind limit | 20 m/s | S23 Ch. 2.1 item 4 |
| OP01 | out-of-service wind limit | 50 m/s | S23 Ch. 2.1 item 4 |
| OP01 | precision-slew / clamp-release limit | 13 m/s | S23 § 2.4 item 1(c); § 10.7.3.2; § 10.7.4.1 |
| OP01 | UK industry out-of-service point | 16.5 m/s | S24 p.1 |
| OP01 | anemometer alarm + mandatory stop | at limit | S23 § 3.4.1(h), § 3.4.2, § 10.7.3.2 |
| OP01 | monitor constantly; act before the limit; may not start in rising wind | procedure | S24 p.2 |
| OP01 | operator's stop decision cannot be overridden | procedure | S24 p.1 |
| OP01 | numeric limit is delegated to the manufacturer | procedure | S25 § 30(6)1 + DA; S26 1926.1435(b)(4)(iii) |
| OP01 | storm-warning securing duty | procedure | S26 1926.1417(h) |
| OP01 | safe terminal state | procedure | S23 § 3.4.3; S25 § 30(6)2 |
| OP01 | forecast height correction table | 10 m reference; 1.00→1.47 | S24 p.2 |
| OP01 | forecast is 10 m; correct for height | procedure | S24 p.2 |
| OP02 | substrate temperature window | 40–115 °F | S27 § 453-5.3 |
| OP02 | hot-weather stop | > 115 °F ⇒ do not proceed | S27 § 453-5.7.1 |
| OP02 | cold-weather heated-enclosure band and cap | ≥ 40 °F, cap 95 °F | S27 § 453-5.7.2 items 2–3 |
| OP02 | air-temperature gate | > 45 °F and rising | S27 § 453-5.7.2 |
| OP02 | **post-join hold** | **≥ 24 h at 40–95 °F** | S27 § 453-5.7.2 item 4 |
| OP02 | open time | 60 min (normal) / 6 h (slow) | S27 § 453-4.5.2 |
| OP02 | 70 % rule | non-preemptive constraint | S27 § 453-5.1, § 453-5.6 |
| OP02 | application limit | ≤ 20 min after mixing | S27 § 453-5.4 |
| OP02 | contact pressure | ≈ 40 psi, held to cure | S27 § 453-5.1, § 453-5.6 |
| OP02 | failure response | separate + clean | S27 § 453-5.6, § 453-5.8 |
| OP02 | **recovery duration** | **24 h** | S27 § 453-5.8 |
| OP02 | safe terminal state | bead + cure | S27 § 453-5.6 |
| OP03 | mixture temp at placing | 5–35 °C | S28 § 8.1.2 |
| OP03 | discharge temp (winter) | ≥ 10 °C; ≥ 15 °C long-haul | S28 § 10.2.7 |
| OP03 | winter / hot-weather regime triggers | 5 °C × 5 d / 30 °C | S28 § 10.1.1, § 10.1.2 |
| OP03 | rain gate (categorical) | 小雨/中雨 vs 大雨/暴雨 | S28 § 10.4.4 |
| OP03 | layer ≥ 2 °C; striking criteria | 2 °C; 5 °C; 20 °C | S28 § 10.2.10, § 10.2.15, § 10.2.16 |
| all | 10-min mean is the standard averaged quantity; 3 s peak gust is a distinct variable | definition | S29 § 5.1.1, § 5.1.2, § 5.1.3 |
| all | KNMI FX = preceding-hour maximum; GFS GUST = instantaneous gridded gust | definition | project metadata files (`knmi_260_*.metadata.json`, `gfs_*_gust.grib2.metadata.json`) |

**Derived (documented parents, our arithmetic):** OP02 usable window **42 min = 70 % × 60 min**
(S27 § 453-5.6 + § 453-4.5.2); slow-set analogue **4.2 h = 70 % × 6 h**.

### 6.2 Fields that remain ASSUMED (with sensitivity range)

| # | Operation | Assumed field | Baseline | Sensitivity range | Justification |
|---|---|---|---|---|---|
| A1 | OP01 | `lift_cycle_duration_h` | 1.0 h | 0.5 / 1.0 / 2.0 / 4.0 h | **No published duration exists** for one segmental lift cycle. Biggest single gap. |
| A2 | OP01 | `lift_restart_delay_h` | 0.0 h | 0.0 / 0.5 / 1.0 / 2.0 h | No documented restart delay after a wind stop. |
| A3 | OP01 | `wind_stop_margin_ms` | 0.0 m/s | 0.0 / 1.0 / 2.0 m/s | S24 documents a duty to act early but gives no number. |
| A4 | OP01 | `hold_crew_during_wind_pause` | true | true / false | No source states whether the crew stands by. Conservative default. |
| A5 | OP01 | exclusive ground exclusion zone | true | true / false | Lift-plan practice, not a documented numeric constraint. |
| A6 | OP01 | `avg_interval_treatment` | gust as governing | gust / 10-min proxy / swept | **No crane source states the averaging interval.** |
| A7 | all | `height_correction_multiplier` (site terrain class) | 1.10 (20 m, open) | 1.00–1.47 from the S24 table | The *table* is documented; **which row applies to the site is our choice**. |
| A8 | all | `gfs_gust_to_observed_mapping` | fitted on train split only | identity / fitted / quantile-mapped | The mapping is a research contribution, not a documented relation. |
| A9 | OP02 | `substrate_temp_lower_bound_degF` sweep | 40 °F | 35 / 40 / 45 °F | 40 °F is documented; the sweep only tests sensitivity. |
| A10 | OP02 | `epoxy_open_window_min` stress values | 42 min | 30 / 42 / 60 min | 60 min documented, 70 % documented; 30 min is a stress test only. |
| A11 | OP02 | `post_join_hold_h` stress values | 24 h | 12 / 24 / 36 h | 24 h documented; 12 and 36 h are stress tests only. |
| A12 | OP03 | rain intensity in mm/h | — | **none — deliberately not swept** | The code's gate is categorical; **any mm/h number would be invented**. |
| A13 | OP03 | transport cooling law (discharge→placing) | — | 0 / 2.5 / 5 °C | The code gives the endpoints (10 °C → 5 °C in its commentary) but **no decay law**. |
| A14 | OP03 | daily-mean temperature station / spatial averaging | site nearest grid | station set | The code does not fix the station or the averaging footprint. |

Every row above is exposed as a named parameter with a range in
`G2_operation_contract_spec.json → sensitivity_parameters_register`. **None is buried inside
code as a constant.**

---

## 7. Task 5 — failure and adaptation path for the unresolved items

For each unresolved item, the fallback chosen. None is filled with a confident invented number.

| Unresolved item | Fallback class | Concrete action |
|---|---|---|
| Averaging interval of crane wind limits (A6) | **Swept parameter** | Three treatments; primary result reported for the conservative one, sensitivity for the others. |
| Duration of one segmental lift (A1) | **Analogue range + swept parameter** | The only *documented* operation durations found are OP02's (42 min window, 24 h hold). OP01's duration is therefore swept 0.5–4.0 h and the paper reports whether any conclusion flips across that range. |
| Restart delay and stop margin (A2, A3) | **Explicitly labelled assumption with sensitivity range** | 0 baseline with an upper sweep; results reported as a frontier, not a point. |
| Crew hold during a wind pause (A4) | **Redesign so it is swept, not claimed** | Boolean swept axis; the ablation "crew released vs crew held" becomes a reported axis. |
| Which height-correction row applies (A7) | **Swept parameter from a documented table** | Sweep the documented multipliers; never assert a terrain class. |
| GFS-gust-to-observed mapping (A8) | **Redesign: the unresolved value becomes the swept/estimated parameter** | The mapping is fitted on the training split only and reported with residuals; it is a *result*, not an input assumption. |
| Rain mm/h boundary (A12) | **Redesign: keep the gate categorical** | The gate is binary rain/no-rain, declared ASSUMED; the main experiment runs with rain disabled and enabled to demonstrate the result does not depend on it. |
| GB 50666 § 10.2.12 strength criterion (striking) | **Exclude from the weather-sensitive task set** | Either implement a documented maturity model or state explicitly that formwork striking is out of scope for the weather contract. Do not fake a duration. |
| Numeric code wind limit for lifting | **Not available; use manufacturer + industry recommendation** | Report the delegation finding (S25, S26) as the reason. This is a *result*, not a gap. |
| EN 13001-2 / ISO 4302 / FEM / BS 7121 clause values | **Not obtained; do not cite** | Listed in § 9. The contract is complete without them because the numeric limit is delegated to the manufacturer anyway. |
| Actual project erection manual for OP02 | **Owner-specification default with a stated caveat** | Use VDOT IIM-S&B-91 clause values, state that the project manual governs on a real site, and sweep the window. |
| Chinese crane codes (JGJ 33, JGJ 196, GB 5144) | **Open; parallel search track** | A parallel evidence track was still running when this contract was written. **Nothing from those codes is asserted here.** If it returns usable clause-level values they are appended to the ledger and the contract as new rows — they are not used to change any number above. |

---

## 8. Residual-risk list (what a reviewer will attack, and the mitigation)

Ordered by severity. The **full machine-readable list is R1–R17** in the spec JSON; the twelve
highest-severity items are restated here, and R13–R17 (introduced by the Chinese-code finding)
are given at the end of this section.


1. **R1 — HIGH — No crane source states the averaging interval.** *Any* reviewer can say the
   project compares a forecast gust to an unknown reference quantity.
   **Mitigation:** declare it `NOT_ESTABLISHED`, sweep it, and report the three-way mismatch
   (FX preceding-hour maximum / GFS instantaneous gust / unknown crane interval) as a stated
   limitation rather than a solved problem.
2. **R5 — HIGH — The GFS→limit mapping is a calibration problem and its residual must reach the
   decision.** **Mitigation:** fit on train only, report residuals, propagate them, and never call
   the GFS−KNMI difference a standard error.
3. **R2 — HIGH — No published duration for one segmental lift.** **Mitigation:** swept parameter;
   the defensible duration evidence lives in OP02, not OP01.
4. **R3 — HIGH — 20 m/s is one crane model's manual, not a code requirement.**
   **Mitigation:** S25 and S26 both document that the code delegates the number; S24 supplies a
   conservative alternative; both values are run.
5. **R8 — HIGH — The rain gate has no mm/h boundary.** **Mitigation:** keep it categorical; run
   with rain off and on.
6. **R12 — HIGH — Out-of-service wind values must never authorise work.** **Mitigation:** encoded
   as an asset state with `authorises_work_start: false`, asserted in code.
7. **R4 — MEDIUM — Measurement height mismatch (10 m forecast vs jib).** **Mitigation:**
   documented S24 multiplier table, swept.
8. **R6 — MEDIUM — OP02 rests on a US state DOT specification.** **Mitigation:** clause-level
   locators, explicit "the project manual governs" statement, and a cross-reference to the
   independent GB 50666-2011 lower bound.
9. **R9 — MEDIUM — No documented restart delay after a crane wind stop.** **Mitigation:** zero
   baseline swept to 2 h, declared ASSUMED.
10. **R10 — MEDIUM — GB/T 28591-2012 retrieved but image-only.** **Mitigation:** Met Office
    Beaufort table used instead, mapping labelled as ours.
11. **R11 — MEDIUM — EN 13001-2, ISO 4302, FEM 1.001/1.005, BS 7121-1, BS EN 14439 not read.**
    **Mitigation:** recorded as not obtained; nothing from them is cited.
12. **R7 — LOW — The 42-minute window is our arithmetic.** **Mitigation:** both documented
    parents printed beside the derived value; tagged `DOCUMENTED_LIMIT_OUR_ARITHMETIC`.

**R13–R17 — introduced by the Chinese-code finding (see § 2.1 rows 8–13).**

13. **R13 — HIGH — Scope error.** The mandatory 9.0 m/s limit (S35 GB 55034-2022 § 3.4.7) governs
    crane **installation and dismantling**, not ordinary lifting. Using it as a lifting threshold
    would be a misattribution. **Mitigation:** its own phase `INSTALL_DISMANTLE_LIMIT`, kept
    strictly out of the main-lift start rule, and used in the paper only as independent
    code-level evidence that state-dependent wind contracts are real.
14. **R14 — MEDIUM — Over-claiming the asymmetry.** JGJ 33-2012 gives 9.0 m/s for
    installation/dismantling and 12.0 m/s for open-air lifting inside one code, which *looks* like
    a start/continuation asymmetry but is two **adjacent activities**. **Mitigation:** stated
    explicitly here and in the CSV row that it must **not** be described as a start/continuation
    asymmetry of one operation. The HS2 11.1/20 m/s case remains motivation only.
15. **R15 — HIGH — Cross-source numeric conflict.** 9.0 (S35, mandatory) / 12.0 (S36, S37) /
    13.0 (S38) / 16.5 (S24) / 20.0 (S23) m/s. A reviewer can call this cherry-picking.
    **Mitigation:** present the **full spread** as the *reason* the threshold is swept; state the
    code hierarchy (GB 55034-2022 is the later mandatory full-text code and prevails); lead the
    results with a threshold-sensitivity frontier rather than a single headline number.
16. **R16 — MEDIUM — Draft-standard misuse.** The only printed averaging window found
    (3-second mean gust) sits in GB 6067.3-202X, a **draft for comment**. **Mitigation:** source
    S42 is labelled DRAFT FOR COMMENT ONLY / NOT IN FORCE in both the ledger and the spec, and a
    `do_not_claim` field forbids citing it as a code requirement.
17. **R17 — LOW — Secondary-only citation for GB 50164-2011 § 6.4.4.** The clause text was seen
    only as a quotation inside a provincial guidance document. **Mitigation:** the 5 °C value is
    corroborated by GB 50666-2011 § 8.1.2 (S28) and JGJ/T 104-2011 § 6.2.6 (S41), both read
    directly; S43 must not be cited for its clause number.

### The single biggest reviewer attack, stated plainly

> "Your contract turns on a 20 m/s number from one crane's manual. The manual never says whether
> that is a 3-second gust, a 1-minute mean or a 10-minute mean, and it never says at what height
> the anemometer sits. Your weather input is a numerical-model **gust** field at a **10 m**
> reference height. So your entire G2 gate is a comparison between two quantities you have not
> shown to be commensurable."

**Mitigation, in the order the paper should present it:** (1) state the mismatch explicitly as a
limitation; (2) report the three-way temporal-support evidence from the project's own decoded
metadata; (3) report the Chinese chain's *instantaneous* alarm requirement (S39) as the strongest
available indication of what practitioners actually watch — while stating that it is a display
requirement, not a documented averaging window for the limit; (4) sweep the averaging-interval
treatment and the height multiplier as declared sensitivity axes; (5) run the main experiment
across the **whole cross-jurisdiction spread** (9.0 / 12.0 / 16.5 / 20 m/s), not just at two
values; (6) show that the qualitative conclusion (whether forecast information has decision
value) is stable across those axes — or report honestly that it is not.

**A second, newer attack to expect** (created by the Chinese-code finding): *"You cite a 9.0 m/s
mandatory code limit and a 12.0 m/s code limit and then run your main experiment at 20 m/s. Which
do you actually believe?"* The mitigation is to stop treating the choice as a belief: present the
spread as the reason the threshold is swept, and lead the results with a threshold-sensitivity
frontier rather than a single-number headline.

---

## 9. Fetch log — what was actually obtained (all 2026-09-15 unless noted)

| Source | URL | HTTP | What was seen | Usable numbers? |
|---|---|---|---|---|
| S23 Yongmao STT293 manual | `cranemanuals.com/.../Yongmao-STT293-Tower-Crane-Operating-Service-Manual.pdf` | 200 | full 157-page PDF, text-extracted | **Yes** — 20 / 50 / 13 m/s |
| S24 CPA TIN 101 | `ritchiestraining.co.uk/.../TheEffectofWindonMobileCranesIn-service.pdf` | 200 | full 2-page PDF, text-extracted | **Yes** — 16.5 / 20 / 14 / 7 m/s + height table |
| S25 DGUV Vorschrift 52 § 30 | `bgbau-medien.de/handlungshilfen_gb/daten/dguv/52/30.htm` | 200 | full § 30 text + Durchführungsanweisungen | **No number by design** |
| S26 29 CFR 1926.1417 / .1435 | `law.cornell.edu/cfr/text/29/1926.1417` and `/1926.1435` | 200 | full current e-CFR text of both sections | **No number by design** |
| S27 VDOT IIM-S&B-91 | `snowplowing.vdot.virginia.gov/.../SBIIM91.pdf` | 200 | full 204-page PDF, text-extracted to `sources/extracted/vdot_iim_sb91.txt` | **Yes** — 40/115/95/45 °F, 60 min, 70 %, 20 min, 40 psi, 24 h ×2 |
| S28 GB 50666-2011 | `gf.cabr-fire.com/m/article-17761.htm` (+ 17800, 17801, 17802, 16635) | 200 | Chinese normative text + commentary, § 8.1.2 through § 10.4.10 | **Yes** — 5/35 °C, 10/15 °C, 2 °C, 20 °C, 5 °C×5 d, 30 °C |
| S29 WMO CIMO Guide Ch. 5 | `old.wmo.int/.../8_I_5_en_MR_tc.pdf` | 200 | full 19-page PDF, text-extracted | **Yes** — 10-min mean, 3 s gust definitions |
| S30 Met Office Beaufort scale | `weather.metoffice.gov.uk/guides/coast-and-sea/beaufort-scale` | 200 | full table | **Yes** — force 6 = mean 12 m/s, limits 11–14 m/s |
| S31 GB/T 28591-2012 | `cmastd.cmatc.cn/u/cms/www/201602/01152025b4yb.pdf` | 200 | 1,887,481-byte PDF, **all pages extract empty** (image-only) | **No** |
| S32 CIM 5710-2016 | `irc.gov.mo/.../CIM%205710-2016.pdf` | — | **never fetched** | **No** |
| S33 ASME B30.5 | (no URL) | — | **not obtained**; two secondary descriptions seen | **No** |
| S34 ASCC wind-shutdown article | `ascconline.org/Home/News/.../articleId/568/...` | 200 | full article text (posted 2025-11-14) | Industry commentary only |
| **S35 GB 55034-2022 § 3.4.7** | `gf.cabr-fire.com/m/article-62620.htm` | 200 | **Chinese mandatory code text read verbatim by the parent session** | **Yes — 9.0 m/s with a stated height** |
| **S36 JGJ 33-2012** | `gzhxaq.com/mydata/law/202102/04/16123986714443.htm` | 200 | full text; § 4.1.14, § 4.1.15, § 8.10.8 and Table 4-2 verified verbatim from the saved extract | **Yes — 9.0 / 12.0 / 10.8 m/s + Beaufort table** |
| **S37 JGJ 196-2010** | `zgjjzyjy.org/newss.asp?id=1259` (+ 2 mirrors) | 200 | § 3.4.8, § 4.0.9, § 4.0.16 and scope commentary across 3 mirrors | **Yes — 12 m/s at max height** |
| **S38 GB 5144-2006** | `zhuoligk.com/Inews/1565.html` (+ mirror, + preview PDF) | 200 | § 10.2, § 6.7, § 6.3.4, § 6.8, § 3.6a | **Yes — 13 m/s; non-working state qualitative only** |
| **S39 GB 6067.1-2010** | `gzhxaq.com/mydata/law/202102/04/16124058093350.htm` | 200 | § 9.6.1.1, § 9.6.1.2, § 17.1 k) verified verbatim from the saved extract | **Yes — 瞬时风速 (instantaneous) alarm** |
| **S40 JGJ 80-2016** | `gf.cabr-fire.com/m/article-46638.htm` | 200 | § 3.0.8 + commentary read | **Yes — force 6 = 10.8–13.8 m/s** |
| **S41 JGJ/T 104-2011** | `max.book118.com/try_down/425021344210011200.pdf` | 200 | 53-page text-layer PDF; § 1.0.3 and § 6.2.6 read | **Yes — 5 d / 5 °C verbatim** |
| S42 GB 6067.3-202X **DRAFT** | official SAMR draft-for-comment PDF | 200 | § 10.3.3 and § 14.1.2.3 | **3-second mean gust — DRAFT, NOT BINDING** |
| S43 GB 50164-2011 § 6.4.4 | — | 500 | only a quotation inside a provincial guidance PDF | **SECONDARY only** |
| ACI 305R-20 preview | `concrete.org/Portals/0/Files/PDF/Previews/305R-20_preview.pdf` | 200 | 5-page free preview | Notation only (V at 0.5 m; W in kg/m²/h) |
| ACI 306R-16 / 301-20 previews | `concrete.org/.../Previews/` | 200 | front matter + contents | **No numeric clause** |
| EN 13001-2:2021 | standards-store product pages | 200 | scope/abstract only | **No** |
| ISO 4302:2016 | standards-store product page | 200 | scope only | **No** |
| BS 7121-1:2016 | normadoc preview | **404** | nothing | **No** |
| FDOT Spec 453 / 452 | FDOT blob URLs | **404** | nothing | **No** |

**Paywall / access statement:** no paywalled standard was downloaded, and no substantial
copyrighted text is reproduced in this audit or in the contract files. All quotations above are
short factual extracts needed to fix a threshold to its locator.

---

## 10. What evidence could NOT be obtained

Stated plainly, because an honest gap list is worth more than a filled-in guess.

1. **EN 13001-2:2021** — full text, clause numbers, table values, and therefore the standard's
   in-service and out-of-service wind states. Paywalled. The vendor abstract was readable, but
   the abstract contains no wind value.
2. **ISO 4302:2016** — full text and any wind-load value. Paywalled.
3. **FEM 1.001 and FEM 1.005** — full text. Paywalled.
4. **BS 7121-1:2016** — full text, and therefore confirmation of whether the personnel-carrier
   wind provision is still **7 m/s** in the 2016 edition. S24's 7 m/s note refers to the **2006**
   edition; this audit records it as SECONDARY and does not assert the 2016 edition.
5. **BS EN 14439** (tower cranes) — full text and its in-service / out-of-service wind states.
   Paywalled.
6. **Any numeric wind threshold in European, UK or US national regulation** — none exists to be
   found; all three read delegate the number to the crane manufacturer. This is a *finding*, not
   a gap. **Contrast: China does set them, and they are now in the contract (S35–S38).**
7. **A readable numeric copy of GB/T 28591-2012** — the file was retrieved but is image-only
   (7-page pure-JPEG scan, no OCR available). The Chinese Beaufort conversions are instead taken
   from the codes' **own** internal conversions: JGJ 33-2012 Table 4-2 of its 条文说明
   (force 6 = 10.8–13.8 m/s), JGJ 80-2016 § 3.0.8 commentary (same band), both read directly,
   plus the Met Office table (S30).
8. **A published duration for one precast segmental lifting cycle** — searched, not found. This is
   the reason OP01's required uninterrupted duration remains ASSUMED.
9. **Any crane-source statement of the averaging interval** attached to a crane wind *limit* —
   searched across a manufacturer manual, a UK trade note, two national regulations and six
   Chinese code documents; none states it. The Chinese chain documents that the *alarm* quantity
   is instantaneous (S39) and the only printed *interval* is a 3-second mean gust in an
   **unenforced draft** (S42), which cannot be cited as a requirement.
10. **A numeric mm/h rainfall-intensity boundary** for the GB 50666-2011 rain gate — not present
    in that code and no rainfall-intensity standard was obtained in readable form.
11. **GB 50164-2011 § 6.4.4 read directly** — only a secondary quotation inside a Chinese
    provincial government document was seen; the free full-text copy is an image-only scan with no
    text layer (S43, **SECONDARY**). The 5 °C value itself is corroborated by GB 50666-2011
    § 8.1.2 (S28) and JGJ/T 104-2011 § 6.2.6 (S41), both read directly.
12. **ACI 305R-20 numeric clauses and any ACI evaporation-rate limit** — outside the free preview.
    **No ACI number is recorded anywhere in this contract.** The only ACI facts used are the
    notation definitions (wind speed at 20 in./0.5 m above the concrete surface; evaporation in
    kg/m² per hour) and the § 1.1 statement that an as-placed temperature maximum alone is
    insufficient.
13. **FDOT Specifications 452 and 453** — the standard-specification PDFs were 404 at the URLs
    tried. Their content is therefore cited **only** through the VDOT IIM that reproduces the
    relevant requirements at clause level (S27), which is a legitimate primary locator for the
    numbers used.
14. **ASME B30.5** — not obtained; two secondary descriptions seen and labelled SECONDARY.
15. **A numeric non-working-state (storm) wind pressure or speed in the Chinese codes** —
    GB 5144-2006 § 6.3.4/6.8 and GB 6067.1-2010 § 9.4 are **qualitative** and defer to the
    manufacturer. **The widely circulated "800 Pa" figure was NOT seen in any source and is NOT
    reported here.**
16. **Cell values of GB 50666-2011 Tables 10.2.5 and 10.3.3** — the mirror HTML lost the table
    cells and both tables are images. No value from either table is used.
17. **Any numeric wind-speed or evaporation-rate threshold for concrete *material* behaviour in
    GB 50666-2011** — § 10.2.14 (防风) and § 10.3.6 (挡风、遮阳、喷雾) are **qualitative only**.
    The only numeric wind limit touching concrete placing is JGJ 33-2012 § 8.10.8 at
    10.8 m/s, which limits the placing **boom** (a machine), not the material. This is an
    important negative result for OP03.
18. **`GB/T 5144-2023` does not exist** — an official openstd search for "GB/T 5144" returns zero
    records. A government checklist writing "GBT5144-2006" is a typo; do not cite it.

---

## 11. Cross-references and files updated in this round

| File | Change |
|---|---|
| `outputs/operation_contract_details_v2.csv` | **new** — **23 rows, 31 columns**; every original column from `operation_contract_details.csv` is preserved **with its exact original name** (`equipment_scope`, `measurement_height`), and 10 columns are added: `doc_locator_as_seen`, `operation_phase`, `averaging_interval`, `threshold_basis_DOCUMENTED_or_ASSUMED`, `evidence_class`, `sensitivity_range`, `reviewer_attack_risk`, `mitigation`, `measurement_height_reference`, `date_checked`. One row per operation × variable × phase. Row mix: 17 `DOCUMENTED_LIMIT`, 1 `DOCUMENTED_LIMIT_OUR_ARITHMETIC`, 3 `DOCUMENTED_PROCEDURE`, 2 `NOT_OBTAINABLE`. No cell is empty |
| `outputs/gates/G2_operation_contract_spec.json` | **new** — machine-readable implementable contract, provenance tag on every numeric field, 13 registered sensitivity parameters, residual risks R1–R17, 10-entry cross-jurisdiction wind-limit spread |
| `outputs/gates/G2_operation_contract_evidence_2026-09-15.md` | **new** — this audit |
| `outputs/gates/G2_cn_standards_raw_2026-09-15.md` | **new** — raw evidence table and fetch log from the parallel Chinese-standards track (fetch log, evidence table, gap list) |
| `sources/source_ledger.csv` | **appended** — S23–S34 (European/UK/US/owner sources) plus S35–S43 (Chinese codes), 21 new rows; schema unchanged; **43 data rows** total, verified with `csv` |
| `code/build_contract_v2.py` | **new** — deterministic builder for the v2 CSV |
| `code/update_source_ledger_g2.py` | **new** — idempotent append-only ledger updater (S23–S34) with schema guard |
| `code/update_source_ledger_g2_cn.py` | **new** — idempotent append-only ledger updater (S35–S43) with schema guard |
| `sources/extracted/vdot_iim_sb91.txt` | **new** — 204-page VDOT IIM text extract (evidence trail) |
| `sources/extracted/g2_cn/` | **new** — 90 text extracts from the Chinese-standards track, incl. the verbatim JGJ 33-2012, GB 6067.1-2010 and JGJ/T 104-2011 clause text |
| `sources/raw/g2_wind/`, `sources/raw/g2_concrete/`, `sources/raw/g2_cn/` | **new** — fetched public PDFs and HTML retained as the evidence base |

`protocol/research_gates.json` should be updated from
`"G2_complete_operation_contract": "OPEN"` to
`"PARTIAL_CLOSED_FOR_TWO_OPERATIONS_TWO_OPEN_FIELDS"` with the two open fields named
(the averaging interval, and the lift-cycle duration). That edit is left to the parent because
the gates file is shared state.

### Gate-closing statement required by the protocol

`protocol/AiC_详细执行方案_中文.md` § 3.2 sets the G2 acceptance test: *"主实验至少一类连续作业具有
完整的变量、时域、阶段、时长和终态定义；每项未知均留痕。仅有两个风速阈值不算通过。"*

* **变量** — OP02 has a documented governing variable (substrate temperature) plus a documented
  non-preemptive time variable. OP01 has a documented governing variable (wind speed) at a crane
  anemometer.
* **时域** — OP02: a 42-minute non-preemptive window plus a 24-hour documented hold. OP01: the
  start/continuation decision horizon is defined by the forecast horizon (the project's 72 h /
  6 h re-plan setting) and the swept lift duration.
* **阶段** — OP01 phases MAIN_LIFT / POSITION_AND_RELEASE_CLAMPS / OUT_OF_SERVICE; OP02 phases
  JOINT_PREP / JOINT_MAKE / POST_JOIN_CURE_HOLD.
* **时长** — OP02 documented; OP01 `NOT_ESTABLISHED` and swept.
* **终态** — documented for both, at clause level.
* **每项未知均留痕** — 14 assumed fields, each with a stated range, plus 17 residual risks.

The test requires **one** continuous operation with a complete definition. **OP02 satisfies it on
documented evidence alone**; OP01 is materially stronger than the previous two-threshold fixture
and now has a **mandatory code-level numeric limit with a stated height** (S35) alongside the
manufacturer rating. G2 is therefore **no longer a bare two-threshold gate** — but it is
**PARTIAL**, not closed, because OP01's duration and the averaging interval remain open.

### Recommended status string for `protocol/research_gates.json`

```
"G2_complete_operation_contract": "PARTIAL_CLOSED_FOR_TWO_OPERATIONS_TWO_OPEN_FIELDS"
```

with, as `G2_evidence`:

> Two operations now carry citation-backed contracts. OP01 (tower-crane segment lift) rests on a
> manufacturer manual (20 / 50 / 13 m/s, S23), a UK industry recommendation (16.5 m/s, S24), two
> jurisdictions documenting that the numeric limit is delegated to the manufacturer (S25 DE, S26
> US), and a mandatory full-text Chinese code giving 9.0 m/s at the highest point of the machine
> for installation/dismantling (S35) plus 12.0 m/s for open-air lifting (S36/S37, S38).
> OP02 (segmental epoxy jointing) is complete on documented evidence: a 40–115 °F substrate
> window, a 42-minute non-preemptive window (70 % × 60 min), a documented interruption
> prohibition, a documented 24-hour post-join hold, a documented 24-hour recovery and a
> documented safe terminal state (S27). Two fields remain open and are swept, not asserted:
> the averaging interval of every crane wind limit, and the duration of one segmental lift cycle.
> Cross-jurisdiction wind limits legitimately span 9.0–20 m/s for different activities, which is
> itself the justification for treating the threshold as a swept parameter.
