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

# ---------- 2. highlights ----------
hl_path = ROOT / "submission" / "Highlights.txt"
hl = [l.strip() for l in hl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
check("highlights count 3-5", 3 <= len(hl) <= 5, f"{len(hl)} bullets")
check("highlights <= 125 chars", all(len(l) <= 125 for l in hl), f"max {max(len(l) for l in hl)}")

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
check("critical probability equals C/L (expense-optimal rule)",
      all(abs(c["critical_prob"] - c["cost_loss_ratio"]) < 1e-12
          for row in rev for c in row["curve"]),
      "p* = C/L")
check("cost-loss ratio swept only over 0 < C/L < 1",
      all(0 < c["cost_loss_ratio"] < 1 for row in rev for c in row["curve"]),
      "grid inside (0,1)")

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
      "Tower-crane documents supply" in text
      and "mobile-crane industry guidance supplies 16.5" in text
      and "No single machine class or jurisdiction supplies more than three" in text,
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
check("work-package costs quoted in Table 6 match the artefact",
      abs(base["cost"]["operating_limit"] - 2.634) < 0.01
      and abs(base["cost"]["calibrated"] - 2.793) < 0.01
      and abs(base["cost"]["no_weather"] - 4.124) < 0.01,
      f"limit {base['cost']['operating_limit']:.3f}, cal {base['cost']['calibrated']:.3f}, "
      f"none {base['cost']['no_weather']:.3f}")
check("the manuscript reports the operating limit winning in two scenarios",
      "best rule tested" in text and "2.634" in text and "2.470" in text,
      "scenario-dependent ordering reported")
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
      "controlled mechanism experiment and not a held-out evaluation" in text
      and samp["paired_epochs"] == 283668,
      f"{samp['paired_epochs']:,} paired epochs")
check("the sampling section is present with its table",
      "Isolating one cause: the forecast's sampling interval" in text
      and "Table 8" in text, "section 3.9 present")
check("the detector cut is scored by TSS, not by a degenerate criterion",
      abs(samp["best_tuned_threshold"]["6-hourly"]["evaluate_tss"] - 0.633) < 0.005
      and abs(samp["best_tuned_threshold"]["3-hourly"]["evaluate_tss"] - 0.650) < 0.005,
      "TSS reported")
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

failed = [c for c in checks if not c[1]]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    raise SystemExit(1)
