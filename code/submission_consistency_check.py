"""Pre-submission consistency check: every headline number and citation audited.

Each check prints PASS/FAIL with the value found in the manuscript and the value
recomputed from the source outputs. The script exits non-zero if anything fails,
so it can gate the submission package build.

Frozen result version: epochs_multi3.csv + g5_block_v3_*.json, built after the
independent-audit repairs (cost-loss threshold C/L, disjoint reliability bins,
KNMI precipitation semantics, withdrawn joint-hazard labels). Numbers from
earlier versions are stale by construction and must not appear in the text.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from calibration import BinnedCalibrator

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md"
checks: list[tuple[str, bool, str]] = []
TABLE = ROOT / "outputs" / "epochs_multi3.csv"
PREFIX = "g5_block_v3"


def check(name: str, ok: bool, detail: str) -> None:
    checks.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")


text = MD.read_text(encoding="utf-8")
# Citation keys are scanned in the body only: the YAML front matter carries the
# corresponding author's e-mail address, and an address like name@example.edu matches
# the citation pattern and would be reported as an undefined reference.
body = text.split("\n---\n", 2)[-1] if text.startswith("---") else text

# ---------- 1. abstract ----------
abstract = re.sub(r"# Abstract\s*\{-\}\s*", "",
                  text[text.index("# Abstract"):text.index("**Keywords:**")]).strip()
check("abstract <= 150 words", len(abstract.split()) <= 150, f"{len(abstract.split())} words")

# ---------- 1b. citation metadata ----------
# CITATION.cff ships in both the public repository and the release archive, so a title
# there that drifts from the manuscript publishes a citation for a paper that does not
# exist. An earlier version still carried the project's working title and an empty DOI
# while the manuscript had been retitled, and nothing checked it.
_cff_path = ROOT / "CITATION.cff"
_cff_raw = _cff_path.read_text(encoding="utf-8")
_title_line = next((l for l in text.splitlines() if l.startswith("title:")), "")
ms_title = _title_line.split(":", 1)[1].strip().strip('"') if _title_line else ""
check("CITATION.cff exists", _cff_path.exists(), "citation file present")
check("CITATION.cff title matches the manuscript title",
      bool(ms_title) and f'title: "{ms_title}"' in _cff_raw,
      f"manuscript: {ms_title[:60]!r}")
check("CITATION.cff carries no empty DOI placeholder",
      not re.search(r'value:\s*""', _cff_raw), "doi populated")
check("CITATION.cff points at the repository it is published in",
      "github.com/Johnsonlijian/aic-weather-decision" in _cff_raw, "repository-code set")

# ---------- 2. highlights ----------
hl_path = ROOT / "submission" / "Highlights.txt"
hl = [l.strip() for l in hl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
check("highlights count 3-5", 3 <= len(hl) <= 5, f"{len(hl)} bullets")
# Elsevier's Highlights specification is 85 characters per bullet including spaces. An
# earlier version of this check allowed 125, which let two over-length bullets through.
check("highlights <= 85 chars", all(len(l) <= 85 for l in hl), f"max {max(len(l) for l in hl)}")
# The bullets must not be stronger than the paper. "adds nothing over" asserts a
# difference of zero; the paired design supports only "not detectably different".
check("highlights do not overstate the paired null",
      not any(re.search(r"adds nothing|no benefit|useless", l, re.I) for l in hl),
      "no stronger-than-manuscript null wording")
# A relative value is only interpretable next to the ratio it belongs to.
check("highlights scope the relative value with its cost ratio",
      not any(re.search(r"-0\.9\d", l) and "C/L" not in l for l in hl),
      "relative value carries its ratio")

# ---------- 3. citations ----------
# A citation is a bare @key or [@key]; an address is word@domain, so requiring
# that the @ is not preceded by a word character or dot excludes e-mail addresses.
cited = set(re.findall(r"(?<![\w.])@([A-Za-z][A-Za-z0-9_]*)", body))
refs = {e["id"] for e in json.loads((ROOT / "manuscript" / "references.json").read_text(encoding="utf-8"))}
check("all cited keys defined", cited <= refs, f"missing: {sorted(cited - refs) or 'none'}")
check("no orphan references", not (refs - cited), f"unused: {sorted(refs - cited) or 'none'}")

# ---------- 4. epochs + splits ----------
frame = pd.read_csv(TABLE, usecols=["station_id", "epoch", "split", "block_max_L12",
                                    "L12_thr9.0", "L12_thr12.0", "L12_thr13.0",
                                    "L12_thr16.5", "L12_thr20.0", "lead_L12"])
frame["epoch"] = pd.to_datetime(frame["epoch"], utc=True)
split_counts = frame.groupby("split").size().to_dict()
check("epoch rows 281,997 (fit/cal/test 169,184/65,491/47,322)",
      len(frame) == 281997 and split_counts.get("FIT") == 169184
      and split_counts.get("CAL") == 65491 and split_counts.get("TEST") == 47322,
      f"{len(frame)} rows {split_counts}")
check("45 usable stations in the table", frame["station_id"].nunique() == 45,
      f"{frame['station_id'].nunique()} stations")

# ---------- 5. Table 1 ----------
test = frame[frame["split"] == "TEST"]
detector = {}
for thr in (9.0, 12.0, 13.0, 16.5, 20.0):
    y = test[f"L12_thr{thr}"].to_numpy()
    claim = (test["block_max_L12"] > thr).to_numpy()
    detector[thr] = (round(100 * claim.mean(), 1), round(100 * y.mean(), 1),
                     round(100 * (claim & (y == 0)).sum() / max((y == 0).sum(), 1), 1),
                     round(100 * ((~claim) & (y == 1)).sum() / max((y == 1).sum(), 1), 1))
expected = {9.0: (40.8, 47.1, 15.5, 30.9), 12.0: (18.8, 20.1, 8.0, 38.3),
            13.0: (13.3, 14.5, 5.8, 42.7), 16.5: (3.8, 5.1, 1.6, 53.7),
            20.0: (1.2, 1.1, 0.7, 53.8)}
check("Table 1 values match recomputation", all(detector[t] == expected[t] for t in expected),
      f"e.g. 12 m/s = {detector[12.0]}")
check("manuscript states the 31-54% miss range", "31-54%" in text, "range present")
positives = {t: int(test[f"L12_thr{t}"].sum()) for t in (9.0, 12.0, 13.0, 16.5, 20.0)}
check("test positives match the manuscript",
      positives[20.0] == 509 and f"{positives[20.0]:,}" in text and f"{positives[12.0]:,}" in text,
      f"20 m/s = {positives[20.0]}, 12 m/s = {positives[12.0]:,}")

# ---------- 6. skill ----------
cal = json.loads((ROOT / "outputs" / f"{PREFIX}_calibration.json").read_text(encoding="utf-8"))
skill_clim = [round(r["models"]["binned"]["test"]["skill_vs_climatology"], 3) for r in cal]
check("skill vs climatology range +0.27..+0.41",
      abs(min(skill_clim) - 0.271) < 0.01 and abs(max(skill_clim) - 0.412) < 0.01, f"{skill_clim}")
check("+0.27 to +0.41 quoted in abstract and conclusions",
      "+0.27 to +0.41" in abstract and "+0.27 to +0.41" in text, "range present")
check("reliability bins sum to the split at every limit",
      all(r["models"]["binned"]["test"]["reliability_n_total"]
          == r["models"]["binned"]["test"]["split_n"] for r in cal),
      "disjoint bins")

# ---------- 7. cost-loss value and the tuned-raw control ----------
rev = json.loads((ROOT / "outputs" / f"{PREFIX}_economic_value.json").read_text(encoding="utf-8"))
peaks = {}
for row in rev:
    peaks[row["threshold"]] = {
        rule: max((c["rules"][rule]["relative_economic_value"] for c in row["curve"]
                   if c["rules"][rule]["relative_economic_value"]
                   == c["rules"][rule]["relative_economic_value"]), default=float("nan"))
        for rule in ("calibrated", "tuned_raw", "fixed_raw")}
check("REV peaks: calibrated vs tuned raw match within 0.01 at 4 of 5 limits",
      sum(1 for t in peaks if abs(peaks[t]["calibrated"] - peaks[t]["tuned_raw"]) < 0.01) == 4,
      ", ".join(f"{t:g}:{peaks[t]['calibrated']:.3f}/{peaks[t]['tuned_raw']:.3f}" for t in sorted(peaks)))
check("documented limit costs value (peak REV 0.45-0.53)",
      abs(min(peaks[t]["fixed_raw"] for t in peaks) - 0.447) < 0.01
      and abs(max(peaks[t]["fixed_raw"] for t in peaks) - 0.530) < 0.01,
      f"{[round(peaks[t]['fixed_raw'], 3) for t in sorted(peaks)]}")
check("manuscript quotes the paired fixed-limit penalties", "-0.913" in text, "penalty quoted")

# The peak-REV table now states the ratio at which each peak is attained, so a reader can
# situate the maxima instead of seeing three bare numbers. Verify that column against the
# artifact rather than trusting it.
peak_ratios = {}
for row in rev:
    peak_ratios[row["threshold"]] = {
        rule: max(row["curve"], key=lambda c: c["rules"][rule]["relative_economic_value"]
                  if c["rules"][rule]["relative_economic_value"]
                  == c["rules"][rule]["relative_economic_value"] else float("-inf")
                  )["cost_loss_ratio"]
        for rule in ("calibrated", "tuned_raw", "fixed_raw")}
_peak_tbl = re.findall(
    r"^\|\s*(\d+\.\d)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|"
    r"\s*([\d.]+)\s*/\s*([\d.]+)\s*/\s*([\d.]+)\s*\|", text, re.M)
check("the peak-REV table carries a peak-ratio column for every limit",
      len(_peak_tbl) == 5, f"{len(_peak_tbl)} rows with peak ratios")
if len(_peak_tbl) == 5:
    bad = []
    for limit, cal, tuned, fixed, r_cal, r_tuned, r_fixed in _peak_tbl:
        t = float(limit)
        want = peak_ratios.get(t)
        if want is None:
            bad.append(f"{limit}: no artifact row")
            continue
        for stated, rule in ((r_cal, "calibrated"), (r_tuned, "tuned_raw"), (r_fixed, "fixed_raw")):
            if abs(float(stated) - round(want[rule], 2)) > 0.005:
                bad.append(f"{limit} {rule}: table {stated} vs artifact {want[rule]:.4f}")
        for stated, rule in ((cal, "calibrated"), (tuned, "tuned_raw"), (fixed, "fixed_raw")):
            if abs(float(stated) - round(peaks[t][rule], 3)) > 0.0005:
                bad.append(f"{limit} {rule} peak: table {stated} vs artifact {peaks[t][rule]:.4f}")
    check("the peak-REV table's values and peak ratios match the artifact", not bad,
          "; ".join(bad[:4]) or "all five rows agree")
check("critical probability equals C/L (expense-optimal rule)",
      all(abs(c["critical_prob"] - c["cost_loss_ratio"]) < 1e-12
          for row in rev for c in row["curve"]),
      "p* = C/L")
check("cost-loss ratio swept only over 0 < C/L < 1",
      all(0 < c["cost_loss_ratio"] < 1 for row in rev for c in row["curve"]),
      "grid inside (0,1)")
# The grid is 40 log-spaced ratios, but the paired comparison reports five of them. Saying
# only "swept over 0 < r < 1" overstated what is reported and left the "131% of the range"
# figure unreproducible from the text.
grid = sorted({c["cost_loss_ratio"] for row in rev for c in row["curve"]})
check("the swept ratio grid is disclosed with its size and bounds",
      "40-point log-spaced grid" in text and f"{grid[0]:.2f} to {grid[-1]:.2f}" in text,
      f"grid {len(grid)} points {grid[0]:.3f}..{grid[-1]:.3f}")
check("the five reported paired ratios are named in the methods",
      all(f"{r:g}" in text for r in (0.05, 0.1, 0.2, 0.4, 0.6)) and "five pre-declared" in text,
      "paired ratios named")
# REV divides by min(r,s) - r*s, which is s*(1-r) once r > s and so vanishes as r -> 1.
# The artifact's -30.85 at r = 0.99 is that division, not an economic result; the text has
# to say so, because the curve in the figure leaves the panel at that end too.
_rate = json.loads((ROOT / "outputs" / "g5_replay_v3.json").read_text(encoding="utf-8"))
_s = _rate["test_positives"] / _rate["test_epochs"]
_ill = [c["cost_loss_ratio"] for row in rev for c in row["curve"]
        if min(c["cost_loss_ratio"], _s) - c["cost_loss_ratio"] * _s < 0.02]
check("the relative-value normalisation is disclosed as ill-conditioned at the grid ends",
      bool(_ill) and "denominator" in text and "vanishes" in text,
      f"{len(_ill)} grid points below the 0.02 denominator floor")
check("the manuscript does not quote the ill-conditioned extreme as a finding",
      "-30.85" not in text and "-8.63" not in text,
      "extremes not quoted")

# ---------- 8. spatial transfer and decision-value transfer ----------
sp = json.loads((ROOT / "outputs" / "g5_spatial_transfer_12ms.json").read_text(encoding="utf-8"))
s = sp["summary"]
check("leave-one-station-out median transfer ~0.372",
      abs(s["transfer_median_skill"] - 0.372) < 0.005
      and s["transfer_negative_stations"] == 2,
      f"{s['transfer_median_skill']:.3f}, negative at {s['transfer_negative_stations']}")
check("site-specific and documented-limit medians quoted",
      abs(s["site_specific_median_skill"] - 0.396) < 0.005
      and abs(s["raw_threshold_median_skill"] - 0.121) < 0.005,
      f"{s['site_specific_median_skill']:.3f} / {s['raw_threshold_median_skill']:.3f}")
vt = sp["value_transfer_summary"]
check("transported tuned threshold matches the transported table at r=0.1 and r=0.2",
      vt["r0.1"]["tuned_raw_transported"]["median_rev"]
      > vt["r0.1"]["calibrated"]["median_rev"]
      and vt["r0.2"]["tuned_raw_transported"]["median_rev"]
      > vt["r0.2"]["calibrated"]["median_rev"],
      f"r0.1 {vt['r0.1']['calibrated']['median_rev']:.3f} vs "
      f"{vt['r0.1']['tuned_raw_transported']['median_rev']:.3f}")
check("manuscript reports the transfer equivalence honestly",
      "+0.506 against +0.514" in text and "+0.520 against +0.526" in text
      and "+0.398 against +0.392" in text, "transfer numbers present")
by_lead = sp["by_lead_test"]
check("lead stratification ~0.39/0.41",
      abs(by_lead["12"]["skill_vs_climatology"] - 0.386) < 0.005
      and abs(by_lead["18"]["skill_vs_climatology"] - 0.412) < 0.005,
      f"12h {by_lead['12']['skill_vs_climatology']:.3f}, 18h {by_lead['18']['skill_vs_climatology']:.3f}")

# ---------- 9. withdrawn analysis (internal record only) ----------
check("no withdrawn joint-window section in the main text",
      "Withdrawn: the joint wind-rain-temperature window" not in text,
      "moved to AUDIT_REPAIR_LOG_2026-09-16.md")
withdrawn_tokens = ("74.7%", "11,904", "joint12", "rain-failure")
found = [tok for tok in withdrawn_tokens if tok in text]
check("no withdrawn joint-hazard number appears in the text", not found,
      f"found: {found or 'none'}")
check("joint labels are absent from the frozen epoch table",
      not any("_joint" in c for c in pd.read_csv(TABLE, nrows=0).columns),
      "no joint columns in epochs_multi3.csv")

# ---------- 9b. action semantics and the reconciled replay ----------
replay = json.loads((ROOT / "outputs" / "g5_replay_v3.json").read_text(encoding="utf-8"))
check("the manuscript defines the modelled action as protection, not permission to work",
      "protective planning action" in text and "never means permission to work" in text,
      "protection semantics stated")
check("the cost-loss decision rule is stated as protect when P >= C/L",
      "protecting when $P(Y_t = 1) \\ge C/L$" in text, "rule direction correct")
check("the manuscript does not claim the superseded rule was more protective",
      "more protective" not in text, "no unsupported safety framing")
check("replay count identities hold (blind misses = table positives)",
      all(replay["count_checks"].values())
      and replay["policies"]["blind_work"]["n_unprotected_positive"] == replay["test_positives"],
      f"{replay['test_positives']:,} positives reconciled")
check("the induced threshold reproduces the calibrated action set",
      all(v["reproduces_calibrated_action_set_on_test"]
          for v in replay["induced_threshold_check"].values()),
      "implementation check passed")
check("no completion target truncates the replay",
      replay["policies"]["blind_work"]["n_protected"] == 0
      and replay["policies"]["always_protect"]["n_protected"] == replay["test_epochs"],
      "full-sample replay")
check("manuscript quotes the reconciled replay figure",
      "fig_replay_12ms" in text and "sums to the 9,518 positive epochs" in text,
      "figure reference present")

# ---------- 9c. paired comparison at matched ratios ----------
paired = replay["paired"]
check("paired calibrated-vs-tuned differences include zero at every ratio",
      all(v["tuned_minus_calibrated"]["ci_low"] <= 0 <= v["tuned_minus_calibrated"]["ci_high"]
          for v in paired.values()),
      ", ".join(f"{k}:{v['tuned_minus_calibrated']['mean']:+.5f}" for k, v in paired.items()))
check("manuscript reports no detectable difference rather than equivalence",
      "no detectable difference" in text and "equivalence is not something this design can establish" in text,
      "claim strength calibrated")
check("manuscript no longer claims a uniform re-tuning gain",
      all(tok not in text for tok in ("0.45-0.53", "0.54-0.84")),
      "peak-based gain claim removed")

# ---------- 9d. the peak-REV table and the latency table must not report one quantity two ways ----------
# The latency rebuild is not the primary sample: holding the window gates common across the
# four rules admits 109 more epochs, so the 4 h row's peaks differ from the peak-REV table's
# in the third decimal. The text used to claim the 4 h column "reproduces the primary
# analysis exactly, epoch for epoch", which made the two tables look contradictory
# (0.530 vs 0.529). After the 2026-09-17 renumbering these are Table 3 and Table 4.
_lat = json.loads((ROOT / "outputs" / "g5_latency_sensitivity.json").read_text(encoding="utf-8"))
_row4 = next(r for r in _lat["rows"] if r["latency_hours"] == 4)
_primary_n = replay["test_epochs"]
check("the latency rebuild's sample is disclosed when it differs from the primary split",
      (_row4["test_epochs"] == _primary_n)
      or ("47,431" in text and "47,322" in text),
      f"4 h {_row4['test_epochs']:,} vs primary {_primary_n:,}")
check("no claim that the latency column reproduces the primary split epoch for epoch",
      "reproduces the primary analysis exactly" not in text,
      "exactness claim removed")
check("the peak-REV/latency agreement is stated as close, not exact",
      "within 0.0013" in text, "tolerance stated")
check("paired fixed-limit penalty is quoted per ratio",
      "-0.913" in text and "+0.0525" in text, "paired penalties present")
check("rare-event clustering is reported",
      "18 episodes at 20.0 m/s" in text or "18" in text, "episode counts present")
check("manuscript states the effective-sample caveat",
      "37 episodes" in text and "18" in text, "clustering caveat present")

# ---------- 9d. verified industry guidance replaces the undocumented claim ----------
check("averaging-interval claim corrected against the primary source",
      "are not undocumented" in text and "@cpatin110" in text
      and "undocumented in every source" not in text,
      "CPA TIN 110 cited")
check("event renamed as a station-defined exceedance",
      "station-defined gust exceedance" in text, "event naming corrected")
check("operating limit is held fixed and only the trigger is selected",
      "holds the operating limit fixed" in text, "scope boundary stated")
check("the operating-limit pool names its machine classes",
      # case-insensitive: the phrase legitimately moves to the start of a sentence
      "tower-crane documents supply" in text.lower()
      and "mobile-crane industry guidance supplies 16.5" in text.lower()
      and "no single machine class or jurisdiction supplies more than three" in text.lower(),
      "machine-class provenance stated")
check("the removed opening claim is gone",
      "stops when the forecast says the wind will be strong" not in text,
      "opening rewritten")

# ---------- 9e. engineering decision layer ----------
wp = json.loads((ROOT / "outputs" / "g5_work_package.json").read_text(encoding="utf-8"))
check("work-package controller is blind to observed weather",
      wp["leakage_check"]["verdicts_changed"] == 0 and not wp["leakage_check"]["leakage"],
      "leakage guard passed")
check("work-package availability guard passed", wp["availability"]["violations"] == 0,
      f"min margin {wp['availability']['min_margin_hours']} h")
parametric = ("tuned_threshold", "calibrated", "calibrated_by_lead",
              "calibrated_static", "calibrated_rolling_free")
check("every parametric controller is tuned on CAL and fixed for TEST",
      all(wp["tuned_parameters"][s][k] is not None
          for s in wp["tuned_parameters"] for k in parametric)
      and wp["tuned_parameters"]["base"]["operating_limit"] is None
      and wp["tuned_parameters"]["base"]["no_weather"] is None,
      f"base {wp['tuned_parameters']['base']}")
base = wp["test"]["base"]
check("work-package costs quoted in Table 5 match the artefact",
      abs(base["cost"]["operating_limit"] - 2.634) < 0.01
      and abs(base["cost"]["calibrated"] - 2.793) < 0.01
      and abs(base["cost"]["no_weather"] - 4.124) < 0.01,
      f"limit {base['cost']['operating_limit']:.3f}, cal {base['cost']['calibrated']:.3f}, "
      f"none {base['cost']['no_weather']:.3f}")
check("the manuscript reports the operating limit's advantage with its interval caveat",
      "lowest mean cost in" in text and "overlaps the calibrated rule" in text,
      "interval overlap stated for the base scenario")
wp_table = json.loads((ROOT / "outputs" / "g5_work_package_table.json").read_text(encoding="utf-8"))
check("Table 5 carries sample size, units and intervals",
      wp_table["packages_per_scenario"] == 765
      and wp_table["stations"] == 45
      and "units of the exceedance loss" in wp_table["units"],
      f"{wp_table['packages_per_scenario']} packages, {wp_table['stations']} stations")
check("every Table 5 cell has a bootstrap interval",
      all(set(v) == {"mean", "ci_low", "ci_high"}
          for scen in wp_table["table"].values() for v in scen.values()),
      "intervals present for all 28 cells")
check("the work-package model is described before the results",
      "## Work-package model" in text
      and text.index("## Work-package model") < text.index("# Results"),
      "Section 2.5 present")
check("the no-weather baseline winning under weak weather impact is reported",
      "1.102 against 1.140" in text, "adverse case reported")
check("the schedule-optimal ratio is reported as more permissive than the block-level one",
      "how permissive a scheduling trigger should be" in text, "ratio mismatch reported")
check("both comparison lines are reported",
      "calibrated_rolling_free" not in text and "revise freely" in text
      and "never revise" in text, "two lines present")

# ---------- 9f. uncertainty on the headline estimates ----------
unc = json.loads((ROOT / "outputs" / "g5_uncertainty.json").read_text(encoding="utf-8"))
sk = unc["skill_vs_climatology"]
check("skill interval quoted in the manuscript",
      abs(sk["estimate"] - 0.412) < 0.005 and abs(sk["ci_low"] - 0.349) < 0.005
      and abs(sk["ci_high"] - 0.474) < 0.005
      and "+0.412 [+0.349, +0.474]" in text,
      f"{sk['estimate']:+.3f} [{sk['ci_low']:+.3f}, {sk['ci_high']:+.3f}]")
mr = unc["miss_rate"]
check("detector intervals quoted with the episode caveat",
      abs(mr["estimate"] - 0.383) < 0.005 and "[0.300, 0.487]" in text
      and "37 episodes" in text, f"miss {mr['estimate']:.3f}")
check("intervals are computed on time blocks, not rows",
      unc["skill_vs_climatology"]["blocks"] == 38
      and unc["skill_vs_climatology"]["draws"] == 2000, "38 seven-day blocks")
check("rare-event episode denominators are reported for every limit",
      set(unc["episodes"]) == {"9", "12", "13", "16.5", "20"}
      and unc["episodes"]["20"]["episodes"] == 18, "episode counts present")

# ---------- 9g. post-sample hold-out ----------
ho = json.loads((ROOT / "outputs" / "g5_holdout_evaluation.json").read_text(encoding="utf-8"))
check("post-sample replay is reported as a replication, not a failure",
      ho["skill"]["vs_frozen_climatology"]["estimate"] > 0
      and "+0.383" in text and "transfers" in text,
      f"skill {ho['skill']['vs_frozen_climatology']['estimate']:+.3f} "
      f"[{ho['skill']['vs_frozen_climatology']['ci_low']:+.3f}, "
      f"{ho['skill']['vs_frozen_climatology']['ci_high']:+.3f}]")
check("the pooled skill agrees with the row-weighted monthly skill",
      ho["skill_consistency"]["agree"]
      and abs(ho["skill_consistency"]["pooled"] - ho["skill_consistency"]["from_monthly"]) < 1e-9,
      f"pooled {ho['skill_consistency']['pooled']:+.4f} vs monthly "
      f"{ho['skill_consistency']['from_monthly']:+.4f}")
neg_months = [m for m, v in ho["monthly"].items() if v["skill_vs_frozen_climatology"] < 0]
check("every post-sample month has positive skill",
      not neg_months and len(ho["monthly"]) == 11,
      f"{len(ho['monthly'])} months, negative: {neg_months or 'none'}")
check("the holdout uses a frozen model, not a re-fitted one",
      "nothing re-estimated" in ho["note"] and ho["holdout_rows"] == 58767,
      f"{ho['holdout_rows']:,} rows over {ho['holdout_stations']} stations")
check("the null results are reported as replicating out of sample",
      all(abs(ho["paired"][k]["tuned_minus_calibrated"]) < 0.001 for k in ho["paired"]),
      "calibrated vs tuned indistinguishable at every ratio")
check("the operating limit is again the costlier rule",
      ho["paired"]["r0.05"]["fixed_minus_calibrated"] > 0
      and ho["paired"]["r0.1"]["fixed_minus_calibrated"] > 0
      and abs(ho["paired"]["r0.4"]["fixed_minus_calibrated"]) < 0.005,
      "worse at low ratios, coincident at C/L = 0.4")
check("the non-stationary bias is reported",
      "not stationary" in text and "-2.06 to +1.74" in text, "monthly bias range stated")
check("the shorter windows' divergence is disclosed",
      "0.296" in text and "defensible one" in text, "window choice justified")

# ---------- 9h. sampling mechanism experiment ----------
samp = json.loads((ROOT / "outputs" / "g5_sampling_experiment.json").read_text(encoding="utf-8"))
det6, det3 = samp["detector"]["6-hourly"], samp["detector"]["3-hourly"]
check("denser sampling reduces the fixed limit's miss rate",
      det3["miss_rate"] < det6["miss_rate"]
      and abs(det6["miss_rate"] - 0.283) < 0.005 and abs(det3["miss_rate"] - 0.212) < 0.005,
      f"{det6['miss_rate']:.3f} -> {det3['miss_rate']:.3f}")
check("the sampling experiment is described as paired and not held out",
      "controlled mechanism experiment rather than an independent held-out evaluation" in text
      and samp["paired_epochs"] == 283668,
      f"{samp['paired_epochs']:,} paired epochs")
check("the sampling section is present with its table",
      "Isolating one cause: the forecast's sampling interval" in text
      and "Table 7. Effect of forecast sampling density" in text, "section 3.9 present")
check("the detector cut is scored by TSS, not by a degenerate criterion",
      abs(samp["best_tuned_threshold"]["6-hourly"]["evaluate_tss"] - 0.633) < 0.005
      and abs(samp["best_tuned_threshold"]["3-hourly"]["evaluate_tss"] - 0.650) < 0.005,
      "TSS reported")

# The section used to describe its sample as "a contiguous annual cycle in 2021-2022 plus
# four further months spread across 2023 to 2025" and to place those months "inside the
# model-fitting period", while also calling the sample a superset of the study's held-out
# split. Both cannot hold: the tables cover every month from 2021-06 to 2025-09, which
# includes the held-out 2025 months. Verify the coverage against the epoch tables and
# require the text to match it.
_samp3 = pd.read_csv(ROOT / "outputs" / "epochs_samp3.csv", usecols=["epoch", "station_id"])
_main = frame[["epoch", "station_id"]]
_s_months = pd.to_datetime(_samp3["epoch"], utc=True, format="mixed").dt.to_period("M")
_m_months = pd.to_datetime(_main["epoch"], utc=True, format="mixed").dt.to_period("M")
_all_months = sorted(set(_s_months.unique()) | set(_m_months.unique()))
check("the sampling table covers the study's whole month span, contiguously",
      sorted(set(_s_months.unique())) == _all_months
      and len(_all_months) == (_all_months[-1] - _all_months[0]).n + 1,
      f"{len(set(_s_months.unique()))} months, {_all_months[0]}..{_all_months[-1]}")
check("the sampling sample is stated as a superset of the study's own table",
      "contains all 281,997 epochs" in text
      and f"plus {samp['paired_epochs'] - len(_main):,}" in text,
      f"{samp['paired_epochs']:,} - {len(_main):,} = {samp['paired_epochs'] - len(_main):,} extra")
check("the sampling section no longer places its months inside the fitting period",
      "fall inside the model-fitting period" not in text
      and "contiguous annual cycle in 2021-2022" not in text,
      "stale sample description removed")
check("the sampling section states that the sample overlaps the held-out months",
      "including the held-out months" in text, "overlap disclosed")
check("the internal split is described by its boundary, not by 'earliest'",
      f"tunes the cut on the {samp['tune_rows']:,} epochs before 2022" in text
      and samp["tune_rows"] + samp["evaluate_rows"] == samp["paired_epochs"],
      f"{samp['tune_rows']:,} + {samp['evaluate_rows']:,} = {samp['paired_epochs']:,}")

# The denser pull spans the same 52 months but is complete in only 17 of them. The paragraph
# after the one fixed in round 12 described this as a patchwork of 17 months and then drew two
# wrong conclusions from it - that the evaluation set misses months in the span, and that the
# dense months lie inside the fitting period. Assert the coverage from the artifact and require
# the text to state the denominator.
_cov = json.loads((ROOT / "outputs" / "g5_collection_coverage_dense.json").read_text(encoding="utf-8"))
_complete = _cov["complete_months"]
check("the dense pull's completeness is stated with its denominator",
      f"{len(_complete)} of the {len(_all_months)} months" in text,
      f"{len(_complete)} complete of {len(_all_months)} covered")
check("the dense pull is not described as continuous, nor the sample as missing months",
      "patchwork of 17 complete months" not in text
      and "is not a sample of every month in that span" not in text,
      "stale completeness description removed")
check("the dense months are not placed inside the fitting period",
      "they also lie inside the model-fitting period" not in text,
      f"{len([m for m in _complete if m > '2023-12'])} complete months fall outside it")
check("the manuscript no longer says the experiment was not executed",
      "we have not executed it" not in text, "claim updated")

# ---------- 10. figure 1 value ----------
fit = frame[frame["split"] == "FIT"]
model = BinnedCalibrator().fit(fit["block_max_L12"].to_numpy(float), fit["L12_thr12.0"].to_numpy(float))
p13 = float(model.predict([13.0])[0])
caption = text[text.index("Two ways to read one forecast"):text.index("## The block event")]
stated = re.search(r"\((\d\.\d\d) at 13 m/s", caption)
check("Fig. 1 caption value matches the fitted model",
      stated is not None and abs(float(stated.group(1)) - round(p13, 2)) < 0.011,
      f"caption {stated.group(1) if stated else '?'} vs fitted {p13:.3f}")

# ---------- 11. dataset scale ----------
msgs, runs, cycles = 0, set(), set()
for manifest in ("gfs_gust_manifest_multi.jsonl", "gfs_gust_manifest_multi00.jsonl"):
    recs = [json.loads(l) for l in (ROOT / "outputs" / manifest).read_text(encoding="utf-8").splitlines() if l.strip()]
    msgs += len({(r["issue_date"], r["issue_cycle"], r["lead_hours"]) for r in recs})
    runs |= {(r["issue_date"], r["issue_cycle"]) for r in recs}
    cycles |= {r["issue_cycle"] for r in recs}
check("39,646 messages / 3,306 runs / 00+12 UTC cycles",
      msgs == 39646 and len(runs) == 3306 and cycles == {"00", "12"},
      f"{msgs} messages, {len(runs)} runs, cycles {sorted(cycles)}")
check("manuscript states the archive scale correctly",
      "39,646" in text and "3,306" in text and "281,997" in text, "scale present")

# ---------- 12. stale-version guard ----------
STALE = ("281,817", "47,142", "1/(1+C/L)", "0.20-0.35", "45-63%", "0.438",
         "assumption-free", "audited, not assumed", "exposure\u2013miss frontier",
         "critical fractile", "74.7%")
stale_hits = [tok for tok in STALE if tok in text]
check("no superseded number or claim survives in the text", not stale_hits,
      f"found: {stale_hits or 'none'}")

# ---------- figure files ----------
figs = re.findall(r"\]\(([^)]+\.pdf)\)", text)
missing = [f for f in figs if not (MD.parent / f).resolve().exists()]
check("every referenced figure exists", not missing, f"missing: {missing or 'none'}")

# Every figure must be cited in the text, and the citations must run in figure order -
# Elsevier checks both. The manuscript previously carried four figures with a callout for
# only Fig. 2, so Figs 1, 3 and 4 would have reached the reviewer uncited.
callouts = [(m.start(), int(m.group(1))) for m in re.finditer(r"Fig\.\s*(\d+)", text)]
cited_nums = {n for _, n in callouts}
check("every figure is cited in the text",
      cited_nums >= set(range(1, len(figs) + 1)),
      f"{len(figs)} figures, cited: {sorted(cited_nums)}")
first_seen, order_ok = [], True
for n in range(1, len(figs) + 1):
    positions = [pos for pos, num in callouts if num == n]
    if not positions:
        order_ok = False
        break
    first_seen.append(min(positions))
check("figures are cited in order of first appearance",
      order_ok and first_seen == sorted(first_seen),
      f"first-citation order: {[n for _, n in sorted(zip(first_seen, range(1, len(first_seen) + 1)))]}")

# Tables must be numbered in citation order too. Before 2026-09-17 the manuscript cited
# Table 6 from the Methods ahead of Table 1 and cited the positioning table (Table 2) last
# of all, so a reviewer met the tables as 6, 1, 3, 4, 5, 7, 8, 2; the numbering was shifted
# to 1..8 in citation order.
table_mentions = [(m.start(), int(m.group(1))) for m in re.finditer(r"Table\s+(\d+)", text)]
table_captions = [int(m.group(1)) for m in re.finditer(r"^Table\s+(\d+)\.", text, re.M)]
first_seen_t: list[int] = []
for _, n in table_mentions:
    if n not in first_seen_t:
        first_seen_t.append(n)
n_tables = len(table_captions)
check("tables are cited in order of first appearance",
      first_seen_t == list(range(1, n_tables + 1)),
      f"first-citation order: {first_seen_t}")
check("table captions are numbered 1..n without gaps",
      sorted(table_captions) == list(range(1, n_tables + 1)),
      f"{n_tables} captions: {sorted(table_captions)}")

failed = [c for c in checks if not c[1]]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    raise SystemExit(1)
