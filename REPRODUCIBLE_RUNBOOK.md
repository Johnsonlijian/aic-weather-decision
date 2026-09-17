# Reproducible runbook

This runbook rebuilds the result-bearing outputs of the study from raw inputs or,
where raw inputs are excluded for licensing reasons, from their acquisition
instructions. The primary, frozen analysis is the block-window decision analysis
(`code/analyze_block_decisions.py`); the constructed scheduling kernel and its
59 tests are a separate, already-verified component.

## Environment

Python 3.12.14 (verified). Core numerical dependencies in `requirements.txt`;
analysis dependencies in `requirements-analysis.txt`. The manuscript needs
Pandoc and XeLaTeX. Install in an isolated virtual environment:

```text
python -m pip install -r requirements-analysis.txt
python -m unittest discover -s tests -v
```

Expected: **59 tests pass** (event executor, operation engine, calibrators, and
the deterministic kernel checks).

## Data acquisition

Raw third-party data is not shipped. `DATASETS_AND_LINKS.csv` records each
source, its URL, licence and package treatment. The two primary sources are
reusable: KNMI hourly observations (CC BY 4.0, attribute KNMI) and the NOAA GFS
NODD archive (open data, attribute NOAA). PSPLIB, DSLIB and downloaded full texts
are acquisition-instruction-only.

1. KNMI observations:

```text
python code/download_knmi_study.py
```

2. GFS surface-gust archive (byte-range, resumable, 00/12Z cycles, 6-72 h leads):

```text
python code/collect_gfs_gust_archive.py --start 2021-03-23 --end 2025-09-30 --cycles 00,12 --leads 6,12,18,24,30,36,42,48,54,60,66,72 --workers 12
python code/rebuild_gfs_tables.py
```

The collector writes per-message SHA-256 and byte ranges to
`outputs/gfs_gust_manifest.jsonl`; `rebuild_gfs_tables.py` derives the station
tables from that manifest. Expected scale: 12,111 verified messages, no data gaps.

## Decision-epoch table and the main analysis

Frozen result version v3 (post-audit; see `AUDIT_REPAIR_LOG_2026-09-16.md`):

```text
python code/build_epoch_table_multi.py --stations-file configs/knmi_stations_multi.json \
    --horizons 6,12,24 --publication-latency-hours 4 --out outputs/epochs_multi3.csv
python code/analyze_block_decisions.py --table outputs/epochs_multi3.csv --prefix g5_block_v3
python code/analyze_spatial_transfer.py --table outputs/epochs_multi3.csv --limit 12.0
python code/render_block_figures.py --prefix g5_block_v3
python code/manuscript_numbers_v3.py
python code/submission_consistency_check.py
```

Expected: `outputs/epochs_multi3.csv` with 281,997 rows (fit 169,184 / calibration
65,491 / test 47,322) over 45 usable stations; `outputs/g5_block_v3_calibration.json`,
`_economic_value.json`, `_campaign.json`; `outputs/g5_spatial_transfer_12ms.json`;
`outputs/manuscript_numbers_v3.{md,json}`; figures under `paper_figures/output/`.
The consistency check recomputes 31 headline numbers from these artefacts and exits
non-zero on any mismatch.

Headline results of v3: the raw deterministic rule misses 31-54% of block-exceedance
events; the calibrated probability reaches +0.27 to +0.41 held-out Brier skill over
climatology and transfers to unseen stations (median +0.372); the calibrated rule and a
raw threshold **tuned on the same calibration split** reach the same cost-loss value at
four of five limits, while the documented limit used as the decision threshold costs
0.45-0.53 against 0.54-0.84.

Regex and unit tests:

```text
python -m unittest discover -s tests -p "test_audit_repairs.py"
```

## Forecast-latency sensitivity

```text
python code/build_epoch_table_multi.py --stations-file configs/knmi_stations_multi.json \
    --horizons 6,12 --publication-latency-hours 4  --out outputs/epochs_lat4.csv
python code/build_epoch_table_multi.py --stations-file configs/knmi_stations_multi.json \
    --horizons 6,12 --publication-latency-hours 6  --out outputs/epochs_lat6.csv
python code/build_epoch_table_multi.py --stations-file configs/knmi_stations_multi.json \
    --horizons 6,12 --publication-latency-hours 8  --out outputs/epochs_lat8.csv
python code/build_epoch_table_multi.py --stations-file configs/knmi_stations_multi.json \
    --horizons 6,12 --publication-latency-hours 12 --out outputs/epochs_lat12.csv
python code/analyze_block_decisions.py --table outputs/epochs_lat6.csv  --prefix g5_lat6
python code/analyze_block_decisions.py --table outputs/epochs_lat8.csv  --prefix g5_lat8
python code/analyze_block_decisions.py --table outputs/epochs_lat12.csv --prefix g5_lat12
python code/analyze_latency_sensitivity.py
```

Expected (`outputs/g5_latency_sensitivity.json`): only two distinct outcomes across the
four rules, because the archive holds the 00 and 12 UTC cycles; the 12 m/s skill moves
+0.411 to +0.408 and the calibrated peak value 0.615 to 0.611.

## Forecast-availability audit

```text
python code/audit_forecast_availability.py
```

Expected: `outputs/gates/G3_forecast_availability_audit.json` reporting object
publication latency between 3.52 and 3.97 h after initialisation (median 3.70 h), which
is the basis of the declared 4 h publication-latency rule. This is a declared assumption
supported by sampled archive metadata, not a provider guarantee.

## Manuscript

From the project root:

```text
manuscript/build.ps1
```

This runs Pandoc (citeproc, `manuscript/references.json`, the fixed CSL) and two
XeLaTeX passes to produce `manuscript/Manuscript_AiC_WORKING_DRAFT.pdf` (8 pages,
three result figures). The reference list is generated from `references.json`;
every bibliographic item there carries a DOI or official URL verified before it
was added.

## Reproducibility boundary

- Raw GRIB2/index files, PSPLIB/DSLIB archives, downloaded full texts and
  standard/manual PDFs are excluded from any public package (`DATASETS_AND_LINKS.csv`).
- Derived tables that contain KNMI labels or GFS forecast values may be
  redistributed with the corresponding attribution; see `LICENSE`.
- Re-run timestamps and archive `Last-Modified` values change between runs, so
  hashes in `MANIFEST_SHA256_2026-09-15.txt` must be regenerated after any re-run.
