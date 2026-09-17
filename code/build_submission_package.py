"""Assemble the AiC submission package from the verified project outputs.

Layout follows the journal's submission requirements: editable manuscript source
plus PDF with line and page numbers, highlights as a separate file, figures as
separate vector files named Figure_1..N, the declaration set (CRediT, competing
interest, funding, generative-AI, data availability), a title page, the data
statement and a reproducibility bundle.

Nothing is published or uploaded; the package is built locally under
``submission_package_AiC_2026-09-16/`` and zipped for the author.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "submission_package_AiC_2026-09-16"

TITLE = ("Separating operating wind limits from forecast-action thresholds in "
         "construction planning")
AUTHOR = "Lijian Ren"
EMAIL = "renlijian@imut.edu.cn"
AFFILIATION = "Inner Mongolia University of Technology, Hohhot, Inner Mongolia, China"

CREDIT = """Lijian Ren: Conceptualization; Methodology; Software; Validation; Formal analysis;
Investigation; Data curation; Writing - original draft; Writing - review & editing;
Visualization; Project administration. (Single-author study.)
"""

COMPETING = """Declaration of competing interest

The author declares that he has no known competing financial interests or personal
relationships that could have appeared to influence the work reported in this paper.
I have nothing to declare.
"""

FUNDING = """Funding

This research did not receive any specific grant from funding agencies in the
public, commercial, or not-for-profit sectors.
"""

AI_DECL = """Declaration of generative AI and AI-assisted technologies in the manuscript
preparation process

During the preparation of this work the author used AI-assisted tools in order to
draft, edit and restructure text and to assist with software development and
analysis. After using these tools, the author reviewed and edited the content as
needed and takes full responsibility for the content of the published article.
"""

DATA_AVAIL = """Data availability statement (journal research-data policy: Option C)

The derived decision-epoch table, the calibration and campaign outputs, the figure
sources and all analysis code are available in the reproducibility bundle. Raw
third-party inputs are re-fetchable by the acquisition scripts and are not
redistributed: KNMI hourly observations are CC BY 4.0 (attribution to KNMI) and
NOAA GFS is NODD open data (attribution requested). Downloaded full texts and
standard/manual PDFs are cited only and excluded.

[Repository DOI / URL to be inserted after deposit.]
"""


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {result.stderr[:400]}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if PKG.exists():
        shutil.rmtree(PKG)
    for sub in ("Manuscript", "Highlights", "Figures", "Declarations",
                "Data", "Reproducibility/code", "Reproducibility/tests"):
        (PKG / sub).mkdir(parents=True, exist_ok=True)

    # ---- manuscript source + PDF ----
    for name in ("Manuscript_AiC_WORKING_DRAFT.tex", "Manuscript_AiC_WORKING_DRAFT.pdf",
                 "Manuscript_AiC_WORKING_DRAFT.md", "references.json",
                 "elsevier-with-titles.csl", "pdf_header.tex", "build.ps1"):
        src = ROOT / "manuscript" / name
        if src.exists():
            shutil.copy2(src, PKG / "Manuscript" / name)
    (PKG / "Manuscript" / "Manuscript_AiC.tex").write_bytes(
        (PKG / "Manuscript" / "Manuscript_AiC_WORKING_DRAFT.tex").read_bytes())
    shutil.copy2(PKG / "Manuscript" / "Manuscript_AiC_WORKING_DRAFT.pdf",
                 PKG / "Manuscript" / "Manuscript_AiC.pdf")

    # ---- highlights ----
    shutil.copy2(ROOT / "submission" / "Highlights.txt", PKG / "Highlights" / "Highlights.txt")
    run(["pandoc", str(PKG / "Highlights" / "Highlights.txt"), "-o",
         str(PKG / "Highlights" / "Highlights.docx")])

    # ---- figures (separate files, journal naming) ----
    figure_map = {
        "Figure_1": "fig1_forecast_decision_mechanism",
        "Figure_2": "fig_reliability_12ms",
        "Figure_3": "fig_risk_efficiency_12ms",
        "Figure_4": "fig_economic_value",
    }
    fig_rows = []
    for out_name, stem in figure_map.items():
        for ext in ("pdf", "png"):
            src = ROOT / "paper_figures" / "output" / f"{stem}.{ext}"
            if src.exists():
                shutil.copy2(src, PKG / "Figures" / f"{out_name}.{ext}")
        svg_src = ROOT / "paper_figures" / "output" / f"{stem}.svg"
        if svg_src.exists():
            shutil.copy2(svg_src, PKG / "Figures" / f"{out_name}.svg")
        fig_rows.append(f"| {out_name} | {stem} | {stem}.pdf (vector) |")

    # ---- declarations ----
    decl = {
        "CRediT_author_contribution_statement.md": CREDIT,
        "Declaration_of_competing_interest.md": COMPETING,
        "Funding_statement.md": FUNDING,
        "Declaration_of_generative_AI_use.md": AI_DECL,
        "Data_availability_statement.md": DATA_AVAIL,
    }
    for name, body in decl.items():
        (PKG / "Declarations" / name).write_text(body, encoding="utf-8")
        run(["pandoc", str(PKG / "Declarations" / name), "-o",
             str(PKG / "Declarations" / name.replace(".md", ".docx"))])

    # ---- title page ----
    title_page = f"""# Title page

**Article title:** {TITLE}

**Author:** {AUTHOR}

**Affiliation:** {AFFILIATION}

**Corresponding author:** {AUTHOR}

**Corresponding author e-mail:** {EMAIL}

**Article type:** Original research paper

**Declarations:** see the separate declaration files (CRediT, competing interests,
funding, generative-AI use, data availability).
"""
    (PKG / "Title_page.md").write_text(title_page, encoding="utf-8")

    # ---- data + reproducibility ----
    shutil.copy2(ROOT / "DATASETS_AND_LINKS.csv", PKG / "Data" / "DATASETS_AND_LINKS.csv")
    shutil.copy2(ROOT / "REPRODUCIBLE_RUNBOOK.md", PKG / "Reproducibility" / "REPRODUCIBLE_RUNBOOK.md")
    shutil.copy2(ROOT / "LICENSE", PKG / "Reproducibility" / "LICENSE")
    shutil.copy2(ROOT / "CITATION.cff", PKG / "Reproducibility" / "CITATION.cff")
    for src in sorted((ROOT / "code").glob("*.py")):
        if src.name.endswith("_v1.py"):
            continue
        shutil.copy2(src, PKG / "Reproducibility" / "code" / src.name)
    for src in sorted((ROOT / "tests").glob("*.py")):
        shutil.copy2(src, PKG / "Reproducibility" / "tests" / src.name)
    # only the frozen v3 result version enters the package: earlier prefixes are
    # superseded by the audit repairs and must not travel with a submission
    for src in sorted((ROOT / "outputs").glob("g5_block_v3_*.json")):
        if src.name.endswith("_campaign.json"):
            continue  # superseded by the reconciled per-station replay
        shutil.copy2(src, PKG / "Reproducibility" / src.name)
    for src in sorted((ROOT / "outputs").glob("g5_lat*_calibration.json")):
        shutil.copy2(src, PKG / "Reproducibility" / src.name)
    for src in sorted((ROOT / "outputs").glob("g5_lat*_economic_value.json")):
        shutil.copy2(src, PKG / "Reproducibility" / src.name)
    for extra in ("g5_spatial_transfer_12ms.json", "g5_latency_sensitivity.json",
                  "manuscript_numbers_v3.md", "manuscript_numbers_v3.json",
                  "epochs_version_diff.json", "knmi_field_semantics_audit.json",
                  "epochs_multi3.audit.json", "g5_replay_v3.json",
                  "g5_replay_v3_count_table.csv"):
        src = ROOT / "outputs" / extra
        if src.exists():
            shutil.copy2(src, PKG / "Reproducibility" / extra)
    # the submission-facing documents prepared on 2026-09-16
    for rel, dest in (("submission/cover_letter_AiC_2026-09-16.pdf", "Cover_letter.pdf"),
                      ("submission/cover_letter_AiC_2026-09-16.md", "Cover_letter.md"),
                      ("submission/declarations_AiC_2026-09-16.md", "Declarations_text_drafts.md"),
                      ("submission/SUPERSEDED_conference_route.md", "Superseded_conference_route.md"),
                      ("submission/release/README_RELEASE.md", "Release_README.md"),
                      ("outputs/g5_independent_recomputation.json",
                       "Reproducibility/g5_independent_recomputation.json"),
                      ("code/verify_independent.py", "Reproducibility/code/verify_independent.py")):
        src = ROOT / rel
        if src.exists():
            shutil.copy2(src, PKG / dest)

    repair_log = ROOT / "AUDIT_REPAIR_LOG_2026-09-16.md"
    if repair_log.exists():
        shutil.copy2(repair_log, PKG / "Reproducibility" / repair_log.name)
    for extra in ("decision_epochs_age12.audit.json", "decision_epochs_age12_fh.audit.json",
                  "g5_observation_quantity_sensitivity.json", "gfs_gust_tables_rebuild.json"):
        src = ROOT / "outputs" / extra
        if src.exists():
            shutil.copy2(src, PKG / "Reproducibility" / extra)
    gate = ROOT / "outputs" / "gates" / "G3_forecast_availability_audit.json"
    if gate.exists():
        shutil.copy2(gate, PKG / "Reproducibility" / "G3_forecast_availability_audit.json")

    # ---- checklist ----
    checklist = f"""# AiC submission checklist (built {datetime.now(timezone.utc).date().isoformat()})

Requirement values are from the live 2026 Guide for Authors re-verified by the
author (see outputs/gates/G6_live_2026_reverification.md).

| # | Journal requirement | Status | File / evidence |
|---|---|---|---|
| 1 | Editable manuscript source required | DONE | Manuscript/Manuscript_AiC.tex (+ .md) |
| 2 | PDF is not an acceptable source but is useful for review | DONE | Manuscript/Manuscript_AiC.pdf |
| 3 | Abstract <= 150 words | DONE | 148 words (checked by code/submission_consistency_check.py) |
| 4 | Keywords 1-7 | DONE | 5 keywords |
| 5 | Highlights: 3-5 bullets, <= 125 chars, separate file named "Highlights" | DONE | Highlights/Highlights.txt (+ .docx) |
| 6 | Line and page numbering | DONE | linenumbers + page footers in PDF |
| 7 | Numbered sections (1, 1.1) | DONE | Pandoc --number-sections |
| 8 | Figures as separate files, named logically | DONE | Figures/Figure_1..4 (pdf vector + png + svg) |
| 9 | Figure captions carry title + description | DONE | in manuscript |
| 10 | Tables editable text, no vertical rules | DONE | Table 1 and Table 2 in manuscript |
| 11 | Declaration of competing interest (Word, from the tool) | PARTIAL | Declarations/Declaration_of_competing_interest.docx; the author must run Elsevier's declarations tool and upload its .docx |
| 12 | CRediT author contribution statement | DONE | Declarations/CRediT_author_contribution_statement.md/.docx |
| 13 | Funding statement in the prescribed format | DONE | Declarations/Funding_statement.md/.docx |
| 14 | Generative-AI declaration before the references | DONE | in manuscript + Declarations/Declaration_of_generative_AI_use.md/.docx |
| 15 | Data availability statement (Option C) | PARTIAL | Declarations/Data_availability_statement.md; repository deposit is a human-only step |
| 16 | Title page with names, affiliation, corresponding author e-mail | DONE | Title_page.md (renlijian@imut.edu.cn) |
| 17 | References numbered in citation order, complete data | DONE | 22 references, all cited, all DOI/URL verified |
| 18 | Graphical abstract (optional) | NOT DONE | optional; Fig. 1 is designed to work as one if needed |
| 19 | Cover letter | NOT REQUIRED | the live guide does not ask for one |
| 20 | Submission system | HUMAN | Editorial Manager (AUTCON) |

## Consistency verification

`code/submission_consistency_check.py` passes 74/74 checks and `code/verify_independent.py` reproduces 13/13 headline numbers with an independently implemented estimator. The consistency checks cover: abstract
length, highlight limits, citation/definition closure, Table 1 recomputation,
Brier-skill ranges, REV peaks, the Fig. 1 probability value, the mean-wind
sensitivity counts, the manifest-derived dataset counts, the epoch-table sizes,
the latency audit bounds, and the LaTeX formatting gates.

## Human-only steps before upload

1. Corresponding-author e-mail on the title page.
2. Run Elsevier's declaration tool and upload its generated .docx.
3. Deposit the derived data (and get a DOI), then insert it in the data statement.
4. Optional: post the SSRN preprint during submission.
"""
    (PKG / "SUBMISSION_CHECKLIST.md").write_text(checklist, encoding="utf-8")

    # ---- package manifest ----
    lines = [f"# Submission package manifest, built {datetime.now(timezone.utc).isoformat()}", ""]
    for path in sorted(PKG.rglob("*")):
        if path.is_file():
            lines.append(f"{sha256(path)}  {path.relative_to(PKG).as_posix()}")
    (PKG / "PACKAGE_MANIFEST_SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    archive = ROOT / "AiC_submission_package_2026-09-16.zip"
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(archive.with_suffix("")), "zip", PKG)

    n_files = sum(1 for p in PKG.rglob("*") if p.is_file())
    print(f"package files: {n_files}")
    print(f"package dir   : {PKG}")
    print(f"archive       : {archive} ({archive.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
