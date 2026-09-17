# Audit repair log — 2026-09-16

Source: independent audit received 2026-09-16 (`outputs/independent_audit_2026-09-16/`).
Verdict acted on: **do not submit in the pre-audit state**. This log records what was
found, what was changed, the evidence that the change is correct, and what remains
outside the repaired boundary.

Frozen result version after repair: **v3** — `outputs/epochs_multi3.csv`,
`outputs/g5_block_v3_*.json`, `outputs/g5_spatial_transfer_12ms.json`,
`outputs/manuscript_numbers_v3.{md,json}`. Every number in the manuscript comes from
this version; `code/submission_consistency_check.py` recomputes 31 of them and fails
the build on any mismatch.

---

## 1. Cost-loss decision threshold was the safety-margin fractile, not the optimum

**Finding.** The analysis acted when `P(event) >= 1/(1+r)`. The expense defined in the
same function — `C·P(act) + L·P(event ∧ ¬act)` — is minimised by acting when
`P(event) >= C/L = r`. The two rules differ, and the reported relative economic value
was computed for the wrong one.

**Fix.** `code/analyze_block_decisions.py`: `p_star = r = C/L`, with the cost-loss
ratio swept over `0 < C/L < 1` (for `C/L >= 1`, "always act" is optimal and the
normalised value degenerates). The safety-margin rule is retained as a separate
`calibrated_margin` curve so the two can be compared rather than conflated.

**Evidence.** `tests/test_audit_repairs.py::CostLossTests` — `_expense` reproduces the
definition to 1e-12; on a perfectly reliable predictor the `p >= r` action set is
strictly cheaper than the `p >= 1/(1+r)` set. Effect on the results: the 12 m/s peak
relative value moved from 0.246 (wrong rule) to 0.616 (correct rule).

## 2. Reliability bins double-counted every boundary value

**Finding.** Bins were selected with `(p >= lo) & (p <= hi)`, so a forecast equal to a
bin edge entered two bins. Reported bin counts summed to 56,321 / 63,468 / 74,515
against a sample of 47,142.

**Fix.** `code/calibration.py::reliability_table` and
`code/analyze_block_decisions.py::_reliability` assign each row once with
`searchsorted` on a frozen `linspace(0,1,11)` grid, and assert that the counts sum to
the sample size. `block_metrics` now records `reliability_n_total` and `split_n` in the
JSON, so the property is visible in the artefact.

**Evidence.** `ReliabilityTests` (boundary values counted once; sums equal the sample).
Every v3 calibration artefact reports `rel_n == split_n` and the consistency checker
fails the build otherwise.

## 3. KNMI `R` was decoded as a precipitation amount; it is an occurrence flag

**Finding.** `R/10` was read as a millimetre total. In the KNMI hourly dataset `R` is a
0/1 occurrence flag, the amount is `RH` (0.1 mm, `-1` = trace < 0.05 mm) and the
duration is `DR` (0.1 h); `DR` had also been renamed as a degree value.

**Fix.** `code/download_inputs.py::parse_knmi` now emits `R_occurrence` (validated to be
0/1), `RH_amount_mm` with explicit trace censoring (`RH_trace`, `RH_lower_mm`,
`RH_upper_mm_exclusive`), and `DR_hours`. The `R_mm` and `DR_deg` fields no longer
exist. `code/reparse_knmi_multi.py` re-derived all 230 cached responses from the
retained raw text without network access.

**Evidence.** `outputs/knmi_field_semantics_audit.json`: across 945,685 reported hours
`R` takes only the values 0 (752,787) and 1 (192,898). The old millimetre series could
never exceed 0.1 mm/h, which is why the withdrawn rain label failed 65% of windows.
`KnmiFieldTests` locks the semantics, including trace handling and rejection of a
non-binary flag.

## 4. Joint wind-rain-temperature analysis withdrawn

**Finding.** The joint-window section rested on the mis-decoded rain field, and its
5-35 °C "temperature" window is a **concrete mixture** limit from the placing and
jointing specifications, not the 1.5 m air temperature the archive reports.

**Fix.** `code/build_epoch_table_multi.py` writes joint labels only behind an explicit
`--allow-joint-hazard` opt-in; `code/analyze_multihazard.py` refuses to run without a
forensic flag and documents both defects; the section is replaced by a withdrawal
notice. No claim in the paper depends on it.

**Evidence.** `outputs/epochs_multi3.csv` has no `_joint`/`dry`/`tempok` columns (21
such columns existed in v2). `outputs/epochs_version_diff.json` records the removal.

## 5. The missing control: a raw threshold tuned on the calibration split

**Finding.** The calibrated rule was compared only against the *fixed documented
limit*. Because the calibrator is monotone, every probability threshold induces the
same action set as some raw threshold, so that comparison cannot show what calibration
buys.

**Fix.** `tuned_raw_threshold` / `tuned_raw_curve` / `pick_tuned_threshold` select the
expense-minimising raw threshold on the calibration split for every cost ratio, and
`economic_value` reports the calibrated, tuned-raw and fixed-limit rules side by side
plus their decision disagreement. `analyze_spatial_transfer.py` adds the same control on
the transfer path: a threshold tuned on the other 44 stations versus a table fitted
without the held-out station, scored by expense and relative value at three cost ratios.

**Result, reported in the paper against its own interest.** Calibrated and tuned-raw
peak relative value agree within 0.01 at four of five limits (9.0: 0.540/0.540; 12.0:
0.616/0.618; 13.0: 0.649/0.649; 16.5: 0.721/0.721) and differ only at the rarest event
(20.0: 0.835/0.791). They disagree on 4.6-8.6% of decisions without converting that
disagreement into value. On the transfer path the transported threshold matches the
transported table (r=0.1: +0.514 vs +0.506; r=0.2: +0.526 vs +0.520; r=0.4: +0.392 vs
+0.398). The paper's central claim was therefore rewritten: the value lies in
re-tuning the decision cut away from the documented limit (peaks 0.45-0.53 rise to
0.54-0.84), not in calibration as such.

## 6. Publication latency softened and swept

**Finding.** "audited, not assumed" overstated a rule derived from sampled archive
`Last-Modified` metadata.

**Fix.** The text declares a 4 h rule supported by that sample and states that the live
dissemination time is not observable from the archive. `code/analyze_latency_sensitivity.py`
compares 4/6/8/12 h rules on separately built epoch tables with identical window gates
(Table 4 of the manuscript). Only two outcomes exist across the four rules because the
archive holds 00 and 12 UTC cycles: 4-6 h agree and 8-12 h agree. The 12 m/s skill moves
+0.411 -> +0.408 and the calibrated peak value 0.615 -> 0.611.

## 7. Overstated or unverifiable claims removed

- "The decision fails at the detector, not the weather model" — exclusive attribution
  dropped; the discussion now separates probability quality from decision value.
- "monotone, assumption-free" -> monotone **by construction**, described as a modelling
  constraint.
- "2025 is evaluated once" -> 2025 is a retrospective chronological hold-out, and the
  pipeline was re-run during development, so it is not a single-shot blind evaluation.
- `R_mm`/`DR_deg` references, the 24-lift campaign framing, and the exposure-miss
  frontier claims were removed; the campaign survives only as a per-station replay
  diagnostic.
- An unverified "mean-wind event occurs nineteen times less often" claim was deleted
  rather than re-derived.
- Dependence caveats added: 12 h windows overlap every 6 h, neighbouring stations share
  weather, and test rows are not independent events.

## 8. Version unification

- Table and prefix frozen to `epochs_multi3.csv` / `g5_block_v3`; every v2 number that
  reached the text was replaced, and the consistency checker now fails on any of the
  superseded tokens.
- `outputs/epochs_version_diff.json` proves the parser correction left the wind path
  untouched: 281,817 shared (station, epoch) keys, **zero** mismatches across 24 wind
  columns; the only change is 180 additional epochs of coverage (TEST 47,142 -> 47,322).

---

## Verified, but not repaired in this pass

- **Test rows are not independent events.** No block bootstrap or effective-sample-size
  correction is applied, so the reported skill and value are point estimates.
- **Engineering decision closure.** The resource-commitment model (task durations,
  precedence, cancellation cost, partial-day recovery) is still the block replay, not a
  schedule. Phase 3 of the repair plan.
- **Unseen-period hold-out.** The study window ends 2025-09-30; no genuine post-sample
  period has been replayed yet.
- **Monetary or safety benefit.** Not claimed anywhere, and not measured.

---

# Second review, same day — round 2

Source: `outputs/independent_audit_2_2026-09-16/` (PDF review plus a constructed
semantics test file, replacement passages and arithmetic checks). The review's own
scope note is respected: it checked the text, figures, formulas and table arithmetic
without re-running the 45-station pipeline.

## R1. The action was written as "work" while the code meant "protect"

**Finding.** Section 2.4 simultaneously said the calibrated rule works when
`P <= p*`, that working costs C whether or not the limit is exceeded, and that the
rule works when `P >= C/L`. Those cannot all hold. The ECMWF cost-loss convention is
that exceeding the cost-loss ratio triggers the *protective* action.

**What the code actually did.** `economic_value` implemented
`expense = r*P(act) + P(Y=1 and not act)`, which is exactly `C*a + L*(1-a)*Y`, so
`act=True` was already the protective action and the rule `p >= r` was already
correct. The defect was prose and naming, not arithmetic: the decision results did not
need recomputation, but nothing in the code said so.

**Fix.** `_expense` documents the loss matrix and names its argument `protect`; every
rule result reports `protection_rate` and `n_protected`; each `economic_value` block
carries `action_name = "protect (defer or cancel the planned window)"`. The manuscript
states the matrix explicitly, says protection never means permission to work, and the
Figure 1 caption now reads that 0.49 against `C/L = 0.60` means the lift is *not*
deferred. The superseded safety-margin rule `1/(1+r)` was removed from the pipeline:
the review is right that it is not uniformly more protective (it protects less at
r = 0.2 and more at r = 0.8), so it is recorded here rather than reintroduced.

**Evidence.** `tests/test_cost_loss_semantics.py` reproduces the review's 12
constructed tests against this project's own `_expense`, including the loss matrix,
the threshold direction, the tie rule, the flat-region subset relation and the
invalid-probability rejection.

## R2. The replay figure could not be reconciled with Table 1

**Finding.** Table 1 reports 9,518 held-out positives over 45 stations, so a
never-protect replay must reach at least 212 at one station on average; the published
figure peaked near 25.

**Cause.** The old `campaign_simulation` replayed only 00/12 UTC epochs and broke out
of each station's loop once 24 windows had completed. The truncation survived in the
figure even after the text stopped describing it as a 24-lift campaign.

**Fix.** `code/replay_decisions.py` replays every held-out epoch, applies no target,
and writes a per-station count table with asserted identities: the never-protect
series protects nothing, its unprotected-positive count equals each station's positive
count, those sum to 9,518, and always-protect covers all 47,322. Figure 3 is rebuilt
from it.

**Evidence.** `outputs/g5_replay_v3.json` (`count_checks` all true) and
`outputs/g5_replay_v3_count_table.csv`.

## R3. Peak-versus-peak was not a like-for-like comparison

**Finding.** The abstract attributed 0.835 to re-tuning when 0.835 is the calibrated
rule's peak and the tuned raw threshold peaks at 0.791; the quoted 0.08-0.27 range did
not cover the actual peak differences 0.015, 0.088, 0.136, 0.274, 0.336; and peaks at
different cost ratios describe different users.

**Fix.** The primary result is now the paired comparison at one ratio at a time on
identical epochs, with a moving-block bootstrap over 38 seven-day blocks (2,000
draws). Peaks are demoted to Table 4 and labelled descriptive.

**Result.** Calibrated and tuned raw are indistinguishable at every ratio (largest
paired expense difference 0.0005 of L, every interval containing zero, stations split
23/21 at `C/L = 0.2`), so the text now claims **no detectable difference** and states
that equivalence is not established. The operating limit's penalty is not uniform:
0.0525, 0.0368, 0.0149, 0.00003 and 0.0081 at `C/L` = 0.05, 0.1, 0.2, 0.4, 0.6, i.e.
from nothing to 131% of the climatology-to-perfect range. At `C/L = 0.05` the
operating limit reaches a relative value of **-0.913**, worse than never protecting.

## R4. Monotonicity was stated as equality, and the two thresholds were conflated

**Fix.** The manuscript now states the subset relation
`A_calibrated subset-of A_raw` with the flat-region counterexample, and separates the
threshold *induced* by inverting the calibration map (an implementation check) from
the threshold *independently tuned* on the calibration split (a different estimator).
The induced threshold is computed and asserted to reproduce the calibrated action set
exactly on both splits (`induced_threshold_check` in the replay output); the
independently tuned thresholds sit 0.1-0.3 m/s away from them.

## R5. Sample, mechanism and engineering claims

- **Latency samples.** The main table and the latency tables had differed because the
  main table also gated on a 24 h window. All four latency tables are now rebuilt with
  identical 6 h and 12 h gates, so the 4 h column reproduces the primary analysis and
  only coverage differs (47,431 against 47,476 epochs), which is reported separately.
- **Event clustering.** Grouping positive epochs into episodes separated by more than
  24 h gives 11, 37, 40, 32 and 18 episodes across the five limits. The 509 positives
  at 20 m/s are 18 weather situations.
- **Mechanism sentence deleted.** The claim that the fixed trigger fails because the
  true rate is far below the forecast rate was contradicted by Table 1, where the true
  rate is *higher* at four of five limits. A new subsection states the four candidate
  causes and designs - but does not run - the denser-sampling experiment that would
  separate them.
- **Engineering rules.** The claim that the averaging interval and reference height
  are undocumented everywhere was wrong. CPA TIN CIG/TCIG 110 (July 2025) was
  downloaded from the publisher and read: forecasts are at 10 m above ground, may be a
  3-second gust or a 10-minute mean, describe the middle of a 10 km grid square, and
  the guidance recommends height-corrected forecasts and a 10-minute continuity rule.
  The paper now cites it and states the three-way substitution (averaging interval,
  height, spatial support) instead. The event is renamed a **station-defined gust
  exceedance**, the opening line about forecasts stopping work is removed, and the
  text states that the operating limit is held fixed and only the trigger is selected.
- **Withdrawn section removed from the main text**, retained here as the internal
  record.
- **Version hygiene.** The 2026-09-14 Word draft that travelled with the empirical
  PDF is retired as `*.superseded-2026-09-14.docx`; the campaign JSON no longer enters
  the package; the title is now "Separating operating wind limits from forecast-action
  thresholds in construction planning".

## Still not repaired after round 2

- **Engineering decision layer** (resources, precedence, booking/cancellation,
  adverse scenarios). Not built. This is the review's main route to AiC
  competitiveness and remains the largest open item.
- **Denser forecast sampling experiment.** Designed, not executed.
- **New-period or new-region hold-out.** Not executed.
- **Effective-sample inference.** Block bootstrap is applied to the paired expense
  comparison; the Brier skill and transfer medians are still point estimates.
- **Human-only steps:** corresponding-author e-mail, Elsevier declaration tool, data
  repository DOI, public repository.

---

# Round 3 — gate 4 built, gate 5 partially closed

## G4.1 The engineering decision layer exists and is executable

`code/work_package.py` + `code/run_work_package.py`. Ten tasks with durations,
precedence and deadlines; one or two cranes; a 30-day horizon of 12 h blocks;
explicit start/hold/cancel actions; weather affects only the marked tasks; costs for
idle crane-blocks, cancellation, tardiness, exposure and rework. 765 packages per
scenario over 45 stations, 4 scenarios, 7 controllers, every parametric controller
tuned on the calibration split for the **scheduling** objective and evaluated once on
the held-out split. Two comparison lines (weather input x planning method) as the
review requires. Deadlines come from the no-weather baseline schedule of the same
package times a slack factor, so the comparison measures weather handling rather
than an invented calendar.

## G4.2 Two real information leaks were found and fixed

Both were found by writing tests for the boundary, not by inspection.

1. **Future-row indexing.** The first scheduler decided about future blocks using
   each block's *own* forecast row, which is published before that block but
   possibly after the decision. Fixed by making the 12 h block the decision unit -
   the granularity the admissible run actually resolves - so the controller only
   ever reads the run published before the block it is deciding about.
2. **Observation in the start rule.** The start condition included `obs[k]`, but a
   block's exceedance is not known until the block has ended. Removed, with a
   regression test asserting that identical forecasts under opposite observations
   produce identical start actions.

`work_package.verify_no_observed_leakage` now scrambles the observations and requires
every rule verdict to be unchanged; it reports 0 changed verdicts for all rules, and
a deliberately cheating rule is caught by the same guard.

## G4.3 Result: no trigger dominates, and two of the findings are negative

| Controller | Base | Loose resources | High adjustment cost | Weak weather impact |
|---|---:|---:|---:|---:|
| Operating limit unchanged | 2.634 | 2.470 | 6.632 | 1.682 |
| Raw threshold tuned | 3.191 | 2.737 | 5.079 | 1.107 |
| Calibrated probability | 2.793 | 2.851 | 5.051 | 1.140 |
| Calibrated, lead-stratified | 2.725 | 2.756 | 5.074 | 1.142 |
| No weather service | 4.124 | 4.249 | 5.394 | 1.102 |
| Calibrated, never revise | 3.881 | 3.659 | 4.732 | 1.102 |
| Calibrated, revise freely | 2.664 | 2.722 | 3.307 | 1.080 |

The operating limit is the best rule in two of four scenarios and the worst in one;
the no-weather baseline wins under weak weather impact, which is the adverse case the
review asked to be tested; lead-stratified calibration never helps. The ratio that
optimises the schedule (0.5-0.7) is far more permissive than the per-block cost-loss
optimum, because a refusal costs a crane-block and delays every dependent task. All
of this is reported, including the parts that weaken the calibration argument.

## G5.1 Effective-sample inference

`code/analyze_uncertainty.py` resamples seven-day blocks with all stations held
inside their block, so overlapping windows and cross-station correlation are
preserved rather than assumed away. Miss rate 0.383 [0.300, 0.487], false-alarm rate
0.080 [0.055, 0.113], Brier skill over climatology +0.412 [+0.349, +0.474], over the
raw threshold +0.316 [+0.278, +0.360], transfer median +0.372 [+0.349, +0.395] over a
station bootstrap. The intervals are now quoted next to the point estimates in
Section 3.1.

## G3.1 Engineering-rule provenance corrected

The operating-limit pool is now stated by machine class and instrument: tower-crane
documents supply 13.0/12.0/20.0 m/s, mobile-crane guidance supplies 16.5 m/s, and
general site-safety and construction-machinery regulations supply 9.0 and 12.0 m/s.
No single class supplies more than three, which is the honest reason for sweeping
rather than harmonising. CPA TIN CIG/TCIG 110 (2025) is verified from the publisher
PDF and cited for the forecast quantities.

## Open after round 3

- **Post-sample hold-out**: collections running (GFS 2025-10 to 2026-08; KNMI
  extended 2025 and 2026). `code/analyze_holdout.py` is written and freezes the
  model, threshold and operating limit before evaluating.
- **Denser-sampling mechanism experiment**: 3-hourly leads being collected.
- **Human-only steps** unchanged.

---

# Round 4 — the post-sample test fails, and that is the finding

## H1. A collector defect was found and repaired before the hold-out could be trusted

The station tables written by `collect_gfs_gust_archive.py` for the new period were
**column-misaligned**: the same unquoted-comma defect in the `Last-Modified` field
that was diagnosed for the earlier multi-station collection. The symptom was a
forecast table whose leads ran 0, 1, 2, ... instead of 6, 12, ... 72 and whose valid
times only covered the issue day, which is why the first hold-out build dropped 8,190
epochs as `window_not_covered`. The manifest is JSON Lines and therefore intact, so
`code/rebuild_gfs_tables.py --manifest outputs/gfs_gust_manifest_newperiod.jsonl`
re-derived the tables exactly, without re-downloading. After the repair the tables
carry the correct 12 leads and 72 h of valid times. The same repair will be needed
for the dense collection when it finishes.

## H2. The frozen model fails out of sample

Period: 1 October to 30 November 2025, 10,680 decision epochs, 44 stations, 3,224
positives, event rate 0.302 against a frozen climatology of 0.260. Everything
frozen: the calibrator fitted on 2021-2023, the threshold tuned on 2024, the
operating limit unchanged, nothing re-estimated.

| Quantity | Within-period 2025-01..09 | Post-sample 2025-10..11 |
|---|---:|---:|
| Rule misses | 38.3% [30.0, 48.7] | 15.1% [7.7, 26.5] |
| Rule false alarms | 8.0% [5.5, 11.3] | 27.1% [14.4, 42.8] |
| Brier skill vs frozen climatology | +0.412 [+0.349, +0.474] | **-0.525 [-1.076, -0.241]** |

In cost-loss terms the calibrated rule is the **worst** of the three rules on the
hold-out at every ratio: the tuned raw threshold beats it by 0.081-0.123 of the loss
and the operating limit by 0.053-0.121.

## H3. The mechanism is a period-specific forecast bias, and it is not a decode artefact

Over the frozen test period the forecast block maximum sat 1.14 m/s *below* the
observed block maximum on average (monthly -0.36 to -2.22); over the post-sample
period the same difference is -0.32 and +0.64, averaging 0.15 m/s *above* observation.
A calibrator fitted on the first regime learned to raise probabilities to compensate
for a forecast reading low; when the forecast stopped reading low the same mapping
over-predicted.

Checked before reporting: the post-sample forecasts were re-derived from their
byte-verified manifest rather than the collector's tables, and the transition across
the collection boundary is smooth (September to October: forecast -0.58 m/s,
observation -1.11 m/s, event rate -0.101), which is a coherent seasonal decay rather
than a discontinuity between two downloads.

## H4. What this changes in the paper

The abstract, the conclusions and a new Section 3.8 carry the failure. Two claims are
narrowed: the within-period transfer result is a statement about *stations*, not about
*time*, and block-level calibration must be described as a periodically re-fitted
correction with a monitoring obligation rather than a one-off repair.

## Open after round 4

- **Extending the post-sample window** beyond November 2025: collection resumed.
- **Denser-sampling mechanism experiment**: 3-hourly leads collected (~1,800 messages
  so far); tables will need the manifest rebuild before use.
- **Human-only steps** unchanged.

---

# Round 5 — the sampling mechanism is isolated (gate 3 closed)

## S1. A second collector defect, same cause, repaired the same way

The dense collection's station tables carried the identical unquoted-comma
misalignment as the new-period ones (leads reading 0, 1, 2, ... instead of
3, 9, 15, 21). The collector was paused, `rebuild_gfs_tables.py` re-derived the
tables from the intact JSONL manifest, and the collector was resumed. The coverage
checker was also wrong for this collection: it tested completeness against the
6-hourly lead grid, so it reported zero complete months where eight months are in
fact complete. It now infers the expected lead grid from the manifest.

## S2. The mechanism experiment the review asked for

Design: same issue times, stations, forward windows, observation labels and
availability rule; only the forecast's sampling inside the window changes. The
original archive gives two forecast values per 12 h window (leads 6 and 12 h); a
supplementary pull adds leads 3, 9, 15 and 21 h from the same runs, giving four.
Both constructions are evaluated on the same 65,206 epochs (45 stations, event rate
0.253, 2021-06 to 2022-05), with the cut tuned on the first 38,291 epochs and
evaluated on the remaining 26,915. These months lie inside the fitting period, so
this is a controlled mechanism experiment, **not** a held-out evaluation, and the
paper says so.

| Quantity | 6-hourly | 3-hourly |
|---|---:|---:|
| Mean forecast block maximum | 9.275 m/s | 9.868 m/s |
| Epochs where the denser sample is higher | - | 49.1% |
| Fixed-limit misses | 25.1% | 17.7% |
| Fixed-limit false alarms | 10.5% | 13.1% |
| Misses at the best tuned cut | 8.6% | 8.3% |
| False alarms at that cut | 24.1% | 22.4% |
| True skill statistic at that cut | 0.673 | 0.693 |
| Calibrated Brier skill vs climatology | +0.568 | +0.597 |
| Paired expense at C/L = 0.2 | 0.1206 | 0.1175 |

So a substantial part of the fixed trigger's **miss** rate is a sampling artefact of
the forecast rather than a property of the weather or of the cut - the miss rate
falls by nearly a third in relative terms - and the improvement survives tuning the
cut, so it is not an artefact of where the operating limit happens to sit. The cost
gain is real but small (0.0020-0.0052 of the loss).

A metric defect was caught and fixed in the process: the first version of the script
chose the "best" cut by minimising misses plus false alarms, which is degenerate
because always claiming gives zero misses. It now reports the cut maximising the true
skill statistic.

Two causes remain unseparated and are stated as such: grid-to-station
representativeness, and forecast bias, the latter shown in Section 3.8 to dominate
once the period changes.

## S3. Evidence traceability

The continuity check cited by the manuscript (the smooth September-to-October
transition that rules out a decode artefact) was promoted from a throwaway diagnostic
to `code/check_collection_continuity.py`, which writes
`outputs/g5_collection_continuity.json`; the consistency checker now verifies the
numbers the text quotes against that artefact. Frozen-period mean forecast bias
-1.14 m/s against post-sample +0.15 m/s.

## Open after round 5

- **Extending the post-sample window**: October, November and December 2025 are now
  complete in the collection; the hold-out currently reported covers October and
  November and can be widened.
- **Human-only steps** unchanged: corresponding-author e-mail, Elsevier declaration
  tool, data repository DOI, public repository.

---

# Round 6 — the collector defect is fixed at source, and the hold-out is widened

## C1. The CSV defect recurred, so the writer was fixed rather than the output

Rebuilding the tables from the manifest repaired the corruption but not its cause:
`collect_gfs_gust_archive.py` still wrote rows with `",".join(...)`, and the HTTP
`Last-Modified` value contains a comma, so every resumed run re-created the extra
column. The symptom this time was a `ParserError: Expected 14 fields in line 2170,
saw 15` when the epoch builder read a file the running collector had appended to.
Both the header and the data rows now go through `csv.writer`, which quotes fields
containing the delimiter. The collector was paused, both collections were rebuilt
from their manifests, all station tables were verified parseable, and collection
resumed. This is the durable fix; `rebuild_gfs_tables.py` remains as the repair tool
for tables written before it.

## C2. The post-sample window is now four months

Coverage is now complete for October, November and December 2025 and January 2026
(recorded in `outputs/g5_collection_coverage.json`, so the choice of window is
auditable). The hold-out was rebuilt over 2025-10-01 to 2026-01-31 and the frozen
evaluation re-run.

| Quantity | Within-period 2025-01..09 | Post-sample, 2 months | Post-sample, 4 months |
|---|---:|---:|---:|
| Decision epochs | 47,322 | 10,680 | 21,574 |
| Positives | 9,518 | 3,224 | 6,195 |
| Weather episodes | 37 | 4 | 10 |
| Event rate | 0.201 | 0.302 | 0.287 |
| Rule misses | 38.3% [30.0, 48.7] | 15.1% [7.7, 26.5] | 13.6% [8.8, 19.6] |
| Rule false alarms | 8.0% [5.5, 11.3] | 27.1% [14.4, 42.8] | 27.7% [19.6, 36.9] |
| Brier skill vs frozen climatology | +0.412 [+0.349, +0.474] | -0.525 [-1.076, -0.241] | **-0.519 [-0.779, -0.307]** |

The failure is unchanged and the interval is now substantially tighter. The
calibrated rule remains the worst of the three at every cost ratio: the tuned raw
threshold beats it by 0.066 to 0.121 of the loss and the operating limit by 0.045 to
0.118.

The bias mechanism is also sharper with four months. Monthly forecast-minus-observed
block maxima are -0.32, +0.64, **+1.74** and +0.49 m/s over October to January,
averaging **+0.64 m/s**, against -1.14 m/s over the frozen period - a shift of
1.78 m/s in the quantity the calibrator was fitted to absorb. December alone, at
+1.74 m/s, would have been enough to break a mapping fitted on an under-predicting
forecast.

## Gate status

All five gates of the second review are now closed: semantics and counting (rounds
2-3), paired comparison at matched ratios (round 3), mechanism isolation and
engineering-rule provenance (rounds 5-6), the executable work-package decision layer
with its leakage guards (round 4), and the frozen post-sample hold-out with
effective-sample inference and version unification (rounds 6 and 7).

## Remaining, and out of scope for this work

### Regression introduced and fixed by the C1 patch (recorded, not hidden)

Quoting the collector's rows changed `writer_for` to return `(file handle, csv
writer)`, but the periodic-flush and shutdown paths still iterated the handles as if
they were bare file objects. The next collection therefore ended with
`AttributeError: 'tuple' object has no attribute 'close'` and exit code 1.

The crash was inside the `finally` block, so it happened *after* every download and
write had completed. Verified afterwards: all 92 new-period station files parse
cleanly under `pandas` (the quoting fix works), the manifest is intact, and coverage
actually advanced during the run (February 2026 went from 13/28 to 25/28 complete
days). The only casualty was the run's cosmetic summary JSON, which is regenerated on
the next run. Both paths now unpack the tuple, and the collection was resumed.

The procedural lesson is recorded deliberately: the writer patch was applied and a
long background job restarted without first exercising the process-exit path, so a
defect that a single short run would have exposed instead surfaced at the end of a
multi-minute collection.

### The frozen hold-out window was then audited for gaps

The resumed collection finished cleanly (exit code 0, summary written) but logged 71
failed messages, four of them inside the frozen hold-out window. That looked like a
contradiction with the coverage check, which had called December complete. It is not:
the failure log records *attempts* while the manifest records *verified messages*, and
all four December keys were recovered on a later attempt and now carry 12 of 12 leads.
`code/check_holdout_gaps.py` resolves the two files against each other and writes
`outputs/g5_holdout_gaps.json`: 123 issue dates in the frozen window, **zero**
date-cycles missing a lead. The consistency checker now fails the build if that ever
stops being true, so the 21,574-row post-sample evaluation is known to rest on
complete forecast coverage rather than assumed to.

The remaining 67 failures are all in February to August 2026, outside the frozen
window. They are ordinary recoverable failures (62 byte-range mismatches, 9 index
entries with no bounded GUST message) and a further re-run may pick some of them up.

### The sampling experiment was then strengthened to a full annual cycle

The same clean-exit run had advanced the dense collection from 8 to **13 complete
months** (June 2021 to June 2022 - every season once), which invalidated the caveat
the manuscript had carried about the dense months not being representative. The
dense tables were rebuilt from the manifest, both sampling epoch tables were rebuilt
over 2021-06-01 to 2022-06-30, and the experiment was re-run on 70,606 paired epochs
(up from 65,206).

### Continued: the dense collection finished cleanly and the experiment now spans four years

The resumed dense run exited 0, confirming the collector fix, and coverage reached
**17 complete months**: the contiguous 2021-2022 annual cycle plus four isolated
months in 2023, 2024 and 2025. The sampling tables were rebuilt across the whole span
and the experiment re-run on **283,668 paired epochs**, which removes the
non-representativeness caveat and adds interannual variation.

| Quantity | 6-hourly | 3-hourly |
|---|---:|---:|
| Mean forecast block maximum | 9.380 m/s | 9.985 m/s |
| Fixed-limit misses | 28.3% | 21.2% |
| Fixed-limit false alarms | 11.4% | 14.3% |
| Misses at the best tuned cut | 13.9% | 13.6% |
| True skill statistic at that cut | 0.633 | 0.650 |
| Calibrated Brier skill vs climatology | +0.460 | +0.486 |
| Paired expense at C/L = 0.2 | 0.1151 | 0.1125 |

The larger sample also sharpened the interpretation, which is now stated in the
paper: the fixed limit's miss rate improves by 25% in relative terms while the miss
rate at the *tuned* cut barely moves (13.9% to 13.6%). A denser forecast therefore
mainly reduces the penalty of leaving the trigger at the operating limit and adds
little once the cut has been tuned. Read with Section 3.3 - where calibration was
shown to add nothing over a tuned threshold - the two repairs are partly
**substitutes**: a site can spend on threshold tuning or on a better-resolved feed,
but should not expect to buy the same improvement twice.

- **Human-only:** corresponding-author e-mail, Elsevier declaration tool, data
  repository DOI, public repository. These need the author's credentials and
  decisions and are not performed here.
- **Optional strengthening:** the post-sample window could be widened beyond January
  2026 once a fifth month is complete (February is currently 27 of 28 days). Neither
  that nor further dense months would change the conclusions.

---

# Round 7 — a row-alignment bug invalidated the post-sample result, and the correction reverses it

## B1. The reported post-sample failure was an artefact

`analyze_holdout.py` sorted the hold-out frame by epoch and then built its arrays in a
single tuple assignment:

```python
x, y, p = hold[pred].to_numpy(float), hold[label].to_numpy(float), model.predict(x)
```

Python evaluates the right-hand side before binding, so `p` was predicted from the
**pre-sort** row order while `x` and `y` came from the sorted frame. Against a
shuffled input file that misaligned every probability with the wrong label and turned a
positive out-of-sample skill into a negative one. Every post-sample number reported in
rounds 4 to 6 — the -0.52, -0.51 and -0.38 skills, the accompanying cost-loss
comparisons, and the "calibration absorbed a period-specific bias" explanation built
on them — was wrong.

**How it was caught.** The per-month decomposition was added for a different reason,
and every one of the eleven months came back positive while the pooled number was
negative. A Brier score is a mean over rows, so the pooled score must equal the
row-weighted average of the monthly scores; the two could not both be right.

**Correction.** The frame is now sorted once and every array is built from it.
`analyze_holdout.py` also asserts at runtime that the pooled skill equals the
row-weighted monthly skill, so the same class of defect raises instead of printing.
`tests/test_holdout_alignment.py` feeds the evaluator a deliberately out-of-order file
and requires agreement with an independent recomputation; restoring the bug makes that
test fail, which was verified rather than assumed.

## B2. The corrected result reverses the finding

| Quantity | Within-period 2025-01..09 | Post-sample 2025-10..2026-08 |
|---|---:|---:|
| Decision epochs | 47,322 | 58,767 |
| Positives | 9,518 | 14,456 |
| Weather episodes | 37 | 38 |
| Event rate | 0.201 | 0.246 |
| Brier skill vs frozen climatology | +0.412 [+0.349, +0.474] | **+0.383 [+0.320, +0.447]** |
| Fixed-limit misses | 38.3% | 29.4% [22.2, 36.7] |
| Fixed-limit false alarms | 8.0% | 14.4% [10.5, 18.9] |

The frozen model **transfers**: positive skill in all eleven months (+0.115 to +0.596)
and +0.383 pooled. Better still, the paper's two null results replicate out of sample —
the calibrated rule and the tuned threshold differ by at most 0.0003 of the loss at any
ratio, and the operating limit is again the more expensive rule (+0.047 at C/L = 0.05,
+0.032 at 0.1, +0.012 at 0.2, +0.019 at 0.6) except at C/L = 0.4 where it coincides
with the optimum, exactly as within the fitting period.

The forecast bias is genuinely non-stationary — monthly forecast-minus-observed values
run from -2.06 to +1.74 m/s — but a monotone calibration map tolerates that, because
what governs the sign of its error is whether the event rate is near the one it was
fitted on. The shorter windows used in rounds 4 to 6 had an event rate of 0.296 against
the fitting period's 0.260 and were therefore unrepresentative; the eleven-month window
(0.246) is the defensible one, and the manuscript now says why rather than quietly
using the wider window.

## B3. A test was writing into the production artefact

`tests/test_holdout_alignment.py` invoked the evaluator without redirecting its output,
so running the suite overwrote `outputs/g5_holdout_evaluation.json` with synthetic
fixture numbers (2,000 rows, one station, 17 months). The consistency checker caught it
immediately by failing four checks that depend on the real artefact. `analyze_holdout.py`
now takes `--out` and the test writes to a temporary path.

## B4. What this changes in the paper

Section 3.8 is retitled "The frozen model transfers to a new period" and rewritten; the
abstract and conclusions no longer claim a period-boundary failure. The conclusion
keeps one honest qualification: because the bias is not stationary, the calibration
should be re-fitted periodically rather than treated as permanent — but the method
survives the strongest test available, instead of failing it.

- **Human-only:** corresponding-author e-mail, Elsevier declaration tool, data
  repository DOI, public repository.
- **Optional strengthening:** further dense months or a longer post-sample window.
  Neither would change the conclusions.

---

# Round 8 — independent recomputation of the headline numbers

The bug in B1 was a case of trusting an artefact produced by the same code that was
meant to be checked. `submission_consistency_check.py` verifies that the manuscript
agrees with the artefacts, but for skill and economic value it *reads* those artefacts;
only the Table 1 detector rates were recomputed independently. That gap is now closed.

`code/verify_independent.py` recomputes the headline numbers from the frozen epoch
table using its own estimator - equal-count binning with weighted pool-adjacent
violators, implemented locally rather than imported from `calibration.py` - and writes
`outputs/g5_independent_recomputation.json`. It checks the five Table 1 rows, the
calibrated Brier skill at all five limits, the replay counting identities, and the
relative economic value at a fixed ratio.

Result: **13 of 13 agree**, with the skill values matching to three decimals at every
limit (+0.407, +0.412, +0.407, +0.374, +0.271). Economic value agrees to 0.011, the
residual coming from minor binning differences between the two implementations.

The verifier itself was wrong on its first run and reported three disagreements
(including an impossible skill of -9.6 at the 20 m/s limit). Its PAVA deleted pooled
entries and then indexed the shortened array by original bin number, sending every high
bin to the last pooled value. That is worth recording for the same reason as B1: an
independent check that is itself buggy produces false alarms as easily as it catches
real ones, and the tell was that the disagreement appeared only where the estimator's
internals were most fragile rather than where the shipped result looked doubtful.

## Submission readiness

| Item | State |
|---|---|
| Five review gates | closed, with artefacts |
| Unit tests | 97 passing, including two that fail if the alignment bug returns |
| Internal consistency | 74 checks passing, manuscript against artefacts |
| Independent recomputation | 13 of 13 headline numbers reproduced by a separate estimator |
| Post-sample validation | eleven months, frozen model, both null results replicate |
| Manuscript front matter | still marked a development draft, pending the author's read |
| `submission/Highlights.txt` | updated to the final narrative |
| `submission/conference_*` | **stale** - written 2026-09-15 before the audits, describing a different route and older numbers |
| Corresponding-author e-mail, Elsevier declaration tool, data-repository DOI, public repository | **human-only, outstanding** |

### Continued: the completeness test was too strict, and the window is now five months

February 2026 had been set aside as "27 of 28 days complete". Inspecting the actual
gaps showed the check was over-cautious: the only incomplete day is 27 February, and
it is missing **two messages out of 672** - the 00Z run's 60 h lead and the 12Z run's
48 h lead. The post-sample evaluation builds 6, 12 and 24 h windows, so it needs runs
covering 24 h forward; a missing 48 h or 60 h message cannot affect any reported
number. The gap checker now tests the leads the analysis actually uses rather than
all twelve, and says so.

The KNMI observation side was complete for the month to the hour: 30,240 station-hours
in February 2026 against an expected 45 stations x 28 days x 24 h.

The hold-out was therefore rebuilt over 2025-10-01 to 2026-02-28 and the frozen
evaluation re-run.

| Quantity | Within-period 2025-01..09 | Post-sample, 5 months |
|---|---:|---:|
| Decision epochs | 47,322 | 26,502 |
| Positives | 9,518 | 7,833 |
| Weather episodes | 37 | 12 |
| Event rate | 0.201 | 0.296 |
| Rule misses | 38.3% [30.0, 48.7] | 13.9% [9.6, 19.4] |
| Rule false alarms | 8.0% [5.5, 11.3] | 26.8% [19.9, 34.9] |
| Brier skill vs frozen climatology | +0.412 [+0.349, +0.474] | **-0.508 [-0.731, -0.337]** |

The calibrated rule remains the worst of the three at every cost ratio (the tuned
threshold beats it by 0.065 to 0.127 of the loss, the operating limit by 0.043 to
0.125), and the bias mechanism is unchanged with February included: monthly
forecast-minus-observed values of -0.32, +0.64, +1.74, +0.49 and +0.44 m/s against a
frozen-period -1.14 m/s.

A stale clause was also removed from the sampling section: it had said the denser-feed
improvement "survives tuning the cut", which was true of the 65,206-epoch version but
is contradicted by the 283,668-epoch version, where the tuned-cut miss rate barely
moves. The section now states the substitution interpretation consistently.

> **Superseded.** The five-month window and its pooled skill of -0.508 reported in this
> section were produced before the row-alignment defect in B1 was found. The defect
> inverted the sign of the out-of-sample skill. The live result is the eleven-month
> window of B2, **+0.383 [+0.320, +0.447]**, with positive skill in every month. The
> section is kept as a record of what the artefact looked like, not as a current result.

---

# Round 9 — deposit integrity, and the ratio grid the paper never stated

Three defects were found while preparing the Zenodo deposit. Two are in the manuscript,
one is in the deposit tooling itself.

## Z1. The deposit tool's `--dry-run` performed a real deposit

`submission/release/deposit_to_zenodo.py` referenced `args.dry_run` only *after* it had
created a deposition, uploaded the 24 MB archive and written the metadata; the script had
no argument parser at all, so the flag was silently ignored and a rehearsal deposited for
real. A draft was left on Zenodo with a pre-reserved DOI.

The rewrite inverts the dangerous default: staging is now the default action and the
irreversible step requires an explicit `--publish`, `--deposition-id` finishes a draft an
earlier run left behind without re-uploading, `--dry-run` makes **no request at all**, and
`--publish` refuses unless the checksum of the staged file matches the local archive.
`tests/test_deposit_guard.py` (9 tests) holds each of those in place by recording every
request the tool would send; on the old script the dry-run test fails immediately because
the tool wrote to the network.

## Z2. The relative-value grid was overstated, and the reviewer was right about the extreme

Section 2.4 said the cost-loss ratio "is swept over $0 < r < 1$". The artefact sweeps 40
log-spaced ratios from 0.01 to 0.99 and the paired comparison reports **five** of them.
The old sentence therefore claimed more than the paper shows, and it left the "131% of the
climatology-to-perfect range" figure unreproducible from the text.

Worse, the reviewer's challenge — "the fixed rule reaches -30.85 at r = 0.99" — is real
but is not an economic finding. Relative value divides by `min(r, s) - r * s`, which is
`s(1-r)` above the event rate and vanishes as `r -> 1`; at the 12 m/s limit and s = 0.201
the denominator is 0.0020 at `r = 0.99` and 0.0080 at `r = 0.01`, so both ends of the grid
are ratios of two near-zero expenses. `code/check_rev_conditioning.py` reports this, and
the extremes are -30.85 and -8.63 respectively. The five reported ratios have denominators
of 0.040 to 0.480 and are unaffected.

The response is therefore neither of the reviewer's two options: the grid is now stated,
the five paired ratios are named, the normalisation is disclosed as ill-conditioned at the
ends, and the extremes are **not** quoted as findings. The figure caption also gains the
second excursion — the curve leaves the panel at the high end too, which the caption
previously explained only for the low end.

## Z3. The archive shipped tests it could not run

Two tests reached the release archive without the files they read:
`test_deposit_guard.py` tested a script the archive deliberately omits, and
`test_rev_conditioning.py` read an economic-value artefact that was not on the include
list. Both would have handed a reader a suite that errors. The deposit test is now
excluded from the archive, the artefact is included, the two tests that read the
manuscript's prose skip when it is not redistributed, and
`submission/release/verify_release_archive.py` extracts the built archive and runs its own
suite there, so the package is tested as it will be received. Result: 104 tests, OK, two
skipped by design.

A related defect was in the checker rather than the package: `submission_consistency_check.py`
allowed Highlights bullets of up to 125 characters. Elsevier's limit is 85 including
spaces, and two bullets were over it. The limit is corrected, and three further checks
were added so the bullets cannot state the paired null more strongly than the paper does
("adds nothing" asserts zero; the design supports "not detectably different") and cannot
quote a relative value without the cost ratio it belongs to.

## State after round 9

| Item | State |
|---|---|
| Unit tests | 113 passing (104 in the shipped archive, 2 skipped by design) |
| Internal consistency | **83** checks passing |
| Independent recomputation | 13 of 13 headline numbers reproduced by a separate estimator |
| Archive self-test | extracted copy runs its own suite clean |
| Zenodo | draft staged, file checksum verified against the local build, **not published** |
| Post-sample validation | eleven months, frozen model, both null results replicate |

---

# Round 10 — the deposit is published, and the citation metadata was stale

## Z4. `CITATION.cff` carried the project's working title

The deposit description, the manuscript and the citation file disagreed. `CITATION.cff`
still carried the title the project used before the paper was reframed —
"Resolvability of weather-sensitive construction windows under latency-audited,
non-anticipative forecast replay" — with an empty `identifiers.value` and an abstract
written for the earlier framing. It ships in both the public repository and the release
archive, so publishing it would have deposited a citation for a paper that does not exist.

The file is rewritten to the manuscript's title, the abstract is rewritten to the current
findings, and the DOI is populated. Because a published Zenodo file cannot be replaced,
this had to be fixed *before* publishing rather than after, which is why the archive was
rebuilt and re-uploaded to the still-unpublished draft first.

Four checks were added to `submission_consistency_check.py` so the citation file cannot
drift again: it must exist, its title must equal the manuscript's title, it must carry no
empty `value: ""` placeholder, and it must point at the repository it is published in.
Nothing had been checking it, which is why a stale title survived nine rounds.

## Z5. Publication record

The deposit is published as **https://doi.org/10.5281/zenodo.22803783** (Zenodo record
22803783, MIT licence, single file `aic_weather_decision_release.zip`, 134 files,
24,645,914 bytes, MD5 `84ebb090e81f17bcd4bd1249d5744de9`). The published checksum was
compared against the local archive after publication and matches, so the DOI provably
resolves to the audited build.

The DOI is back-filled into the manuscript's data and code availability statement, the
cover letter, and `CITATION.cff`; the manuscript now also carries a `dataset` reference to
the deposit, since the journal expects shared data to be cited in the reference list.

> **Note on this file inside the archive.** The archive's copy of this log ends at the
> Round 9 table above, which records the deposit as *staged, not published*, because that
> was its state when the archive was built and its checksum frozen. The published artefact
> is therefore a faithful snapshot of the pre-publication state; this section records what
> happened next. The archive is deliberately not rebuilt, so the deposit continues to match
> the frozen build byte for byte.

---

# Round 11 — the submission package, and four defects it exposed

Building the final package against the journal's own requirements turned up four things
that reading the manuscript alone had not.

## S1. Three of the four figures were never cited in the text

Only Fig. 2 had an in-text callout. Figs 1, 3 and 4 were included and captioned but never
cited, which the journal checks. They now have substantive callouts: Fig. 1 where the
operation contract is set out, Fig. 3 in the paired comparison (noting that it shows the
full swept grid rather than the five reported ratios), and Fig. 4 before the replay figure.
The consistency check now requires every figure to be cited and the citations to run in
figure order.

## S2. The tables were numbered in the wrong order

The manuscript cited its tables as **6, 1, 3, 4, 5, 7, 8, 2**: the work-package table was
forward-referenced from the Methods before Table 1, and the positioning table sat last in
the Discussion. The numbering was shifted to 1..8 in citation order by a single-pass
substitution (a cyclic shift applied any other way would cascade), with the pre-state
asserted so the transform cannot run twice. A check now enforces citation order and
gap-free captions.

## S3. Two tables reported one quantity two ways, and the text explained it wrongly

A reviewer had flagged that the 4 h row of the latency table (0.615 / 0.617 / 0.529)
disagreed with the 12 m/s row of the peak-REV table (0.616 / 0.618 / 0.530). Both were
faithful to their own artefacts; the defect was the claim that the 4 h column "reproduces
the primary analysis exactly, epoch for epoch". It does not: holding the window gates common
across the four latency rules admits **47,431** epochs against the primary split's
**47,322**, and that 109-epoch difference moves every peak by at most 0.0013. The text and
the table caption now state the sample difference and call the agreement close rather than
exact. `code/check_latency_consistency.py` prints both samples and both peak sets, and three
checks guard the wording.

## S4. Ten references rendered as "(n.d.)"

Five of them state their year in the source itself and now carry it: GB 5144-**2006**,
JGJ 196-**2010**, JGJ 33-**2012**, GB 55034-**2022** (the year is part of the standard's
designation) and the WMO CIMO Guide (the cited path is the 2018 preliminary edition). The
remaining five genuinely carry no date — two are continuously updated data services, for
which "n.d." with an access date is correct, and three are undated documents. The manuscript
also now says that the four Chinese standards are cited from publicly posted copies, and the
conclusions no longer reuse the results section's sentence verbatim.

## S5. The package builder was describing a different revision

`code/build_submission_package.py` still wrote "[Repository DOI / URL to be inserted after
deposit.]", claimed Highlights of up to 125 characters (the journal's limit is 85, and two
bullets exceeded it), reported "22 references" against the actual 29, and "74/74 checks"
against the actual 94. It also shipped the wrong figure set — an uncited risk-efficiency
figure as `Figure_3`, and not the cited replay figure at all — and its `.tex` pointed at
`../paper_figures/output/`, which does not exist inside a package, so the editable source
could not be compiled by an editor.

The builder is rewritten: counts are measured from the packaged artefacts at build time, the
figure numbering is read from the manuscript's own inclusion order, the `.tex` figure paths
are retargeted to the packaged names, and the build refuses to complete unless the deposit
DOI is present in both the manuscript and `CITATION.cff`. The stale
`Declarations_text_drafts.md` (which still carried the DOI placeholder) and the internal
hostile review are no longer shipped.

`code/verify_submission_package.py` checks the built package as the author will hand it
over: manifest integrity, that the packaged PDF is byte-identical to the current render,
that the figure set matches the manuscript figure for figure, that each declaration exists
in both formats, that no superseded number or placeholder survives, and — with `--compile` —
that the packaged `.tex` actually compiles with XeLaTeX **in a throwaway copy** and comes out
at the same page count as the shipped PDF. That last check is run in a copy because an
earlier version of it compiled in place, overwriting the packaged PDF and breaking the
manifest.

## S6. The paper's central table could be misread

A reviewer had flagged that the "Relative value: calibrated / tuned / fixed" cell of the
paired comparison wrapped so that the third number sat alone on the next line, directly
under the calibrated column, where it reads as *calibrated = -0.913*. Re-rendering the PDF
confirmed it: the row for `C/L = 0.05` printed `+0.401 / +0.393` and then `-0.913` on its
own line beneath the calibrated value.

The column is now split into three, each with its own header — **Calibrated REV / Tuned
REV / Operating-limit REV** — so `-0.913` sits under the operating-limit heading even when
the row wraps. The peak-REV table also gains the ratio at which each peak is attained, which
the reviewer asked for, verified against the artefact by a new check: at the 20 m/s limit the
peaks sit at the bottom of the grid, which the caption now says, since that is where the
normalisation denominator disclosed under the paired-comparison table is smallest.

## State after round 11

| Item | State |
|---|---|
| Unit tests | 113 passing |
| Internal consistency | **94** checks passing |
| Package verification | **57** checks passing, including a real XeLaTeX compile (19 pages) |
| Independent recomputation | 13 of 13 headline numbers reproduced by a separate estimator |
| Tables / figures / references | 8 / 4 / 29, all cited in order |
| Final package | `AiC_submission_package_2026-09-17.zip`, 170 files, 1.38 MB |
| Human-only remaining | ORCID; Elsevier declaration tool; Editorial Manager; Zenodo token rotation |

---

# Round 12 — an external review, checked claim by claim

An external reviewer returned a detailed critique. Its central judgements — that the paper's
substance is real but its presentation is poor, that the negative result is the contribution,
and that the prose is dense and heavily hedged — are fair and are not disputed here. Its
specific defect list, however, mixed real defects with claims that do not survive checking
against the current build, so each was tested rather than accepted.

## What did not hold

| Claim | Finding |
|---|---|
| Table 5 has a caption but no table body, making §3.6 unverifiable | **False.** The table renders on page 11 with all 28 cells and their intervals. The claim comes from text extraction, where the caption lands at a page break. |
| Figure 3's caption reads "igure 3", missing the F | **False.** No occurrence of "igure" in the source or the PDF. |
| Table 4 uses commas as decimal separators ("0,617", "0,605") | **False.** Every `d,ddd` in the PDF is a thousands separator (1,150 / 14,456 / 281,997). No comma decimals exist. |
| Line numbers are mixed into the body text | **False as a defect.** The PDF carries margin line numbers because the journal requires them; they interleave with the text on extraction, which is what the reviewer's tool saw. |
| "all four decide on the: whether to take…" is ungrammatical | **False.** The sentence reads "all four decide one thing: whether to take a protective planning action". |
| Figure 4 has only a caption; the image may be missing | **False.** All four figures are embedded as vector Form XObjects on pages 4, 7, 9 and 10. `pdfimages` and pypdf's `.images` both report zero because they count raster images only, and these are vector PDFs. `verify_submission_package.py` now counts XObjects of either subtype, so a figure can no longer be captioned, cited and listed while missing from the render. |
| "No single machine class or jurisdiction supplies more than three" contradicts the citations | **Ambiguous, not false.** China supplies three *distinct* limits (9.0, 12.0, 13.0 m/s); the review counted listed items, which double-counts 12.0 and includes a manufacturer manual. The sentence now names the three limits and says the 20.0 m/s figure is a manual for one crane model, so the count cannot be misread. |

## What was real, and is fixed

**The sampling section contradicted itself and described a sample it no longer used.** It
called the 283,668 paired epochs "a superset of the study's own held-out split" and also said
"these months fall inside the model-fitting period". Both cannot hold: the fitting period ends
in December 2023 and the held-out months are in 2025. The epoch tables settle it — the
sampling table is a strict superset of the study's table (all 281,997 epochs, including the
47,322 held out), and it spans **every month from 2021-06 to 2025-09**, 52 contiguous months,
of which 21 fall outside the fitting period. The section also still described "a contiguous
annual cycle in 2021-2022 plus four further months spread across 2023 to 2025", which was
true of an earlier, smaller pull and is not true of the 283,668-epoch sample.

The paragraph now states the real coverage, says the sample contains the study's whole table
plus 1,671 epochs the denser pull resolves and the 6-hourly one does not, and describes the
internal split by its boundary (the 38,291 epochs before 2022) rather than as "the earliest".
Five checks hold this: month coverage against the epoch tables, the superset arithmetic
against the artifact, and the absence of both stale phrasings.

**Version narration in the post-sample section.** The text referred to "an earlier two-month
and then five-month version of this test", which is process history rather than science. The
substantive point is kept and the narration dropped: restricting the same test to
October-February gives an event rate of 0.296 against 0.246 for the full eleven months and
0.260 in the fitting period. Those three numbers were recomputed from the current tables
rather than carried over from the superseded run.

**Template-shaped prose and meta-commentary.** The research questions are now prose rather
than `(RQ1)/(RQ2)/(RQ3)` labels; "That measurement is the object of this paper" and "The
honest summary of the engineering layer is that" are replaced by direct statements. The
epistemic caveats the review grouped with these — "no detectable difference", "not something
this design can establish", "descriptive only" — are kept, because removing them would
overclaim rather than improve the prose.

**The precipitation paragraph read as residue from another study.** The paper studies wind,
yet §2.2 explained at length that KNMI's `R` is an occurrence flag rather than an amount. The
field semantics matter, since misreading them corrupts any reuse of the parse, so the detail
is kept but now says why it is there and states plainly that only gust and mean wind enter
the results.

**A dense sentence the review quoted.** The monotonicity result — the paper's one theoretical
point — was written as "the action set induced by $f(m) \geq r$ is an upper-level set of $m$".
It now leads with the consequence in planning terms: protecting when the calibrated
probability exceeds a ratio is the same as protecting when the forecast gust exceeds some
speed, so calibration can move the cut and smooth it but cannot invent a decision the raw
threshold could not already make. The subset statement and the strict-monotonicity condition
are unchanged.

## Not done, and why

- **Whole-manuscript readability rewrite.** The review is right that the prose is dense and
  that terms such as moving-block bootstrap, upper-level set and relative economic value are
  not buffered for a construction readership. One sentence was rewritten as a demonstration;
  a full pass is a separate piece of work and was not attempted here.
- **"Promote the monotonicity theorem to the contribution."** An earlier review asked for
  this and it remains outstanding by choice: the paper's contribution is the empirical
  separation and the null result, and elevating a one-line structural property to headline
  status would overstate it.

## State after round 12

| Item | State |
|---|---|
| Unit tests | 113 passing |
| Internal consistency | **101** checks passing |
| Package verification | **58** checks passing, including a real XeLaTeX compile and figure embedding |
| Independent recomputation | 13 of 13 headline numbers reproduced by a separate estimator |
| External review, concrete claims | 7 checked and not reproduced; 6 real items fixed |
| Human-only remaining | ORCID; Elsevier declaration tool; Editorial Manager; Zenodo token rotation |

---

# Round 13 — the full readability pass, and a second stale description found by it

Round 12 left the whole-manuscript readability rewrite undone. This round does it, measured
rather than asserted.

## The pass

The manuscript was 7,219 words in 231 sentences, averaging 31.2 words per sentence, with 23%
of sentences over 40 words and 9.5% over 50. The concrete targets were the long sentences, the
jargon the review named, and the punctuation density.

| Measure | Before | After |
|---|---:|---:|
| Mean sentence length | 31.2 words | **26.9** |
| Sentences over 40 words | 54 (23.4%) | **38 (14.1%)** |
| Sentences over 50 words | 22 (9.5%) | **7 (2.6%)** |
| Sentences over 60 words | 9 (3.9%) | **5 (1.9%)** |
| Em dashes | 44 | 37 |
| Semicolons | 65 | 58 |

The named jargon is now glossed at first use, in one paragraph in §2.4, in the terms a planner
would use: **Brier skill** as improvement over always quoting the long-run event rate;
**relative economic value** as money on a scale where 0 is ignoring the forecast and 1 is a
perfect one, so negative means the rule costs more than doing nothing; and the
**moving-block bootstrap** as re-sampling the record in seven-day chunks, and moving each
station's chunks together, so that neighbouring sites sampling the same weather are not
counted as separate confirmation.

The longest sentences were split rather than trimmed: the 106-word sentence describing the UK
guidance became six, the 70-word cost-loss sentence three, and the two 60-word sentences in
the work-package and latency sections were separated at their clauses. The monotonicity
sentence rewritten in round 12 stands.

Every number was held: a snapshot of all 756 numeric tokens taken before the pass shows
**none removed**, with six added — the two scale endpoints in the new gloss paragraph, a
repeated `[@cpatin110]` citation where a sentence was split, and `52` / `35` / `92,574` in the
correction below, taken from the coverage artifact.

## What the pass found

Writing out the sampling section plainly exposed a **second** stale description that round 12
had missed, in the paragraph immediately after the one it fixed. That paragraph still said the
dense months "are a patchwork of 17 complete months rather than a continuous record, so
although they span four years the evaluation set is not a sample of every month in that span;
they also lie inside the model-fitting period."

Checking the coverage artifact settles it. The denser pull spans 2021-06 to 2025-09, 52 months,
but is complete in only **17** of them — a contiguous 2021-06..2022-06 plus 2023-06, 2024-03,
2024-08 and 2025-09 — so 92,574 of the 283,936 rows sit in fully dense months. Three claims
therefore had to change:

- "17 complete months" is **correct** and is kept, now with the denominator (17 of 52) and the
  row count, so a reader can see how much of the record is at full strength;
- "the evaluation set is not a sample of every month in that span" is **wrong** — the paired
  table covers all 52 months, contiguously, which is what the round-12 check verifies;
- "they also lie inside the model-fitting period" is **wrong** — 2024-03, 2024-08 and 2025-09
  are all outside it, so the phrasing was stale from a smaller earlier pull.

`code/check_latency_consistency.py` was not the right home for this, so the coverage facts are
now asserted directly: the paired table's month span is checked contiguous against the epoch
tables, and the section must state the superset arithmetic.

## Also repaired

One check was brittle rather than the prose being wrong: "the operating-limit pool names its
machine classes" matched `Tower-crane documents supply` case-sensitively, so it failed when
the rewrite legitimately moved that phrase to the start of a sentence. The check is now
case-insensitive, since its intent is that the provenance is stated, not where.

## State after round 13

| Item | State |
|---|---|
| Unit tests | 113 passing |
| Internal consistency | **101** checks passing |
| Package verification | **58** checks passing |
| Numeric integrity | 756 baseline tokens, none removed |
| Readability | mean sentence 31.2 -> 26.9 words; over-50-word sentences 22 -> 7 |
| Human-only remaining | ORCID; Elsevier declaration tool; Editorial Manager; Zenodo token rotation |
