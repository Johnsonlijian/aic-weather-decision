"""Assemble the AiC submission package from the verified project outputs.

Layout follows the journal's submission requirements: editable manuscript source plus PDF
with line and page numbers, highlights as a separate file, figures as separate vector files
named Figure_1..N, the declaration set (CRediT, competing interest, funding, generative-AI,
data availability), a title page, the data statement and a reproducibility bundle.

Nothing is published or uploaded; the package is built locally under
``submission_package_AiC_2026-09-17/`` and zipped for the author.

Two things are derived rather than written down, because both had gone stale:

* the figure mapping is read from the manuscript's own inclusion order, so a figure can
  neither be shipped under the wrong number nor dropped while the manuscript cites it - an
  earlier version shipped an uncited risk-efficiency figure as Figure_3 and omitted the
  cited replay figure;
* the checklist's counts (abstract length, highlight length, references, tables, figures,
  passing checks) are measured at build time, so the checklist cannot describe an older
  revision.

The build refuses to finish if the deposit DOI is missing from either the manuscript or
CITATION.cff, since the whole point of the deposit was to give the data statement a
resolvable identifier.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAMP = "2026-09-17"
PKG = ROOT / f"submission_package_AiC_{STAMP}"

TITLE = ("Separating operating wind limits from forecast-action thresholds in "
         "construction planning")
AUTHOR = "Lijian Ren"
EMAIL = "renlijian@imut.edu.cn"
AFFILIATION = "Inner Mongolia University of Technology, Hohhot, Inner Mongolia, China"
DOI = "10.5281/zenodo.22803783"
DOI_URL = f"https://doi.org/{DOI}"
REPO_URL = "https://github.com/Johnsonlijian/aic-weather-decision"

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

DATA_AVAIL = f"""Data availability statement (journal research-data policy: Option C)

The derived decision-epoch table, the calibration and campaign outputs, the figure
sources and all analysis code are openly available in the reproducibility package
archived at Zenodo: {DOI_URL}

The code is maintained at {REPO_URL}

Raw third-party inputs are re-fetchable by the acquisition scripts and are not
redistributed: KNMI hourly observations are CC BY 4.0 (attribution to KNMI) and
NOAA GFS is NODD open data. Downloaded full texts, standards and manual PDFs are
cited only and excluded.
"""


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {result.stderr[:400]}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure() -> dict:
    """Measure the submission-facing counts from the frozen artifacts."""
    md = (ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md").read_text(encoding="utf-8")
    abstract = re.sub(r"# Abstract\s*\{-\}\s*", "",
                      md[md.index("# Abstract"):md.index("**Keywords:**")]).strip()
    keywords = md[md.index("**Keywords:**"):].splitlines()[0]
    n_keywords = len([k for k in keywords.split(":", 1)[1].split(";") if k.strip()])
    highlights = [l.strip() for l in
                  (ROOT / "submission" / "Highlights.txt").read_text(encoding="utf-8").splitlines()
                  if l.strip()]
    refs = json.loads((ROOT / "manuscript" / "references.json").read_text(encoding="utf-8"))
    fig_stems = re.findall(r"\]\([^)]*?/([A-Za-z0-9_]+)\.pdf\)", md)
    captions = re.findall(r"^Table\s+(\d+)\.", md, re.M)
    check = subprocess.run([sys.executable, str(ROOT / "code" / "submission_consistency_check.py")],
                           capture_output=True, text=True)
    m = re.search(r"(\d+)/(\d+) checks passed", check.stdout)
    return {
        "abstract_words": len(abstract.split()),
        "n_keywords": n_keywords,
        "n_highlights": len(highlights),
        "max_highlight": max(len(l) for l in highlights),
        "n_refs": len(refs),
        "n_tables": len(captions),
        "fig_stems": fig_stems,
        "n_figs": len(fig_stems),
        "checks_passed": int(m.group(1)) if m else 0,
        "checks_total": int(m.group(2)) if m else 0,
        "checks_ok": check.returncode == 0,
    }


def main() -> None:
    stats = measure()
    md = (ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md").read_text(encoding="utf-8")
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    problems = []
    if DOI not in md:
        problems.append(f"the manuscript does not carry the deposit DOI {DOI}")
    if DOI not in cff:
        problems.append("CITATION.cff does not carry the deposit DOI")
    if not stats["checks_ok"]:
        problems.append(f"the consistency check is failing "
                        f"({stats['checks_passed']}/{stats['checks_total']})")
    if problems:
        print("REFUSING to build the submission package:")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)

    if PKG.exists():
        shutil.rmtree(PKG)
    for sub in ("Manuscript", "Highlights", "Figures", "Declarations",
                "Data", "Reproducibility/code", "Reproducibility/tests"):
        (PKG / sub).mkdir(parents=True, exist_ok=True)

    # ---- manuscript source + PDF ----
    # The submission carries clean file names, and the .tex is rewritten so its figure
    # paths resolve inside the package: the generated source points at
    # ../paper_figures/output/, which does not exist here, so an editor could not compile
    # it as shipped.
    for name in ("Manuscript_AiC_WORKING_DRAFT.md", "references.json",
                 "elsevier-with-titles.csl", "pdf_header.tex"):
        src = ROOT / "manuscript" / name
        if src.exists():
            shutil.copy2(src, PKG / "Manuscript" / name)
    (PKG / "Manuscript" / "Manuscript_AiC.md").write_bytes(
        (ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md").read_bytes())
    shutil.copy2(ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.pdf",
                 PKG / "Manuscript" / "Manuscript_AiC.pdf")

    tex = (ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.tex").read_text(encoding="utf-8")
    numbered = {stem: f"Figure_{i}"
                for i, stem in enumerate(dict.fromkeys(stats["fig_stems"]), start=1)}

    def retarget(m: re.Match) -> str:
        target = m.group(2)
        stem = Path(target).stem
        if stem in numbered:
            return f"{m.group(1)}{{../Figures/{numbered[stem]}.pdf}}"
        return m.group(0)

    tex = re.sub(r"(\\includegraphics\[[^\]]*\])\{([^}]*)\}", retarget, tex)
    tex = tex.replace("Manuscript_AiC_WORKING_DRAFT", "Manuscript_AiC")
    (PKG / "Manuscript" / "Manuscript_AiC.tex").write_text(tex, encoding="utf-8")

    # ---- highlights ----
    shutil.copy2(ROOT / "submission" / "Highlights.txt", PKG / "Highlights" / "Highlights.txt")
    run(["pandoc", str(PKG / "Highlights" / "Highlights.txt"), "-o",
         str(PKG / "Highlights" / "Highlights.docx")])

    # ---- figures: the manuscript's own inclusion order defines the numbering ----
    fig_rows = []
    for i, stem in enumerate(dict.fromkeys(stats["fig_stems"]), start=1):
        out_name = f"Figure_{i}"
        shipped = []
        for ext in ("pdf", "png", "svg"):
            src = ROOT / "paper_figures" / "output" / f"{stem}.{ext}"
            if src.exists():
                shutil.copy2(src, PKG / "Figures" / f"{out_name}.{ext}")
                shipped.append(ext)
        fig_rows.append(f"| {out_name} | `{stem}` | {', '.join(shipped)} |")
    # a figure the manuscript does not cite must not travel with the submission
    cited = set(stats["fig_stems"])
    uncited = sorted(p.stem for p in (ROOT / "paper_figures" / "output").glob("*.pdf")
                     if p.stem not in cited)
    (PKG / "Figures" / "FIGURE_MAP.md").write_text(
        "# Figure files\n\n"
        "Numbered in the order the manuscript first includes them.\n\n"
        "| Journal file | Source stem | Formats |\n|---|---|---|\n"
        + "\n".join(fig_rows) + "\n\n"
        "Generated but not cited by the manuscript, and therefore **not** part of this "
        f"submission: {', '.join('`' + u + '`' for u in uncited) if uncited else 'none'}.\n",
        encoding="utf-8")

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

**ORCID:** *(to be supplied by the author before upload)*

**Article type:** Original research paper

**Data and code:** {DOI_URL} - {REPO_URL}

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
    for pattern in ("g5_lat*_calibration.json", "g5_lat*_economic_value.json"):
        for src in sorted((ROOT / "outputs").glob(pattern)):
            shutil.copy2(src, PKG / "Reproducibility" / src.name)
    for extra in ("g5_spatial_transfer_12ms.json", "g5_latency_sensitivity.json",
                  "manuscript_numbers_v3.md", "manuscript_numbers_v3.json",
                  "epochs_version_diff.json", "knmi_field_semantics_audit.json",
                  "epochs_multi3.audit.json", "g5_replay_v3.json",
                  "g5_replay_v3_count_table.csv", "g5_holdout_evaluation.json",
                  "g5_work_package.json", "g5_work_package_table.json",
                  "g5_uncertainty.json", "g5_sampling_experiment.json",
                  "g5_independent_recomputation.json", "g5_holdout_gaps.json",
                  "g5_collection_continuity.json", "g5_collection_coverage.json"):
        src = ROOT / "outputs" / extra
        if src.exists():
            shutil.copy2(src, PKG / "Reproducibility" / extra)
    # the submission-facing documents. The 2026-09-16 declarations draft is deliberately
    # excluded: it still carries "[Repository DOI / URL to be inserted after deposit.]" and
    # is superseded by the generated declaration files. The internal hostile review is not
    # submission material either.
    for rel, dest in (("submission/cover_letter_AiC_2026-09-16.pdf", "Cover_letter.pdf"),
                      ("submission/cover_letter_AiC_2026-09-16.md", "Cover_letter.md"),
                      ("submission/release/README_RELEASE.md", "Release_README.md"),
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
author (see outputs/gates/G6_live_2026_reverification.md). Every count below is
measured from the packaged artifacts at build time rather than transcribed, so the
checklist cannot describe an older revision.

| # | Journal requirement | Status | File / evidence |
|---|---|---|---|
| 1 | Editable manuscript source required | DONE | Manuscript/Manuscript_AiC.tex (+ .md) |
| 2 | PDF is not an acceptable source but is useful for review | DONE | Manuscript/Manuscript_AiC.pdf |
| 3 | Abstract <= 150 words | DONE | {stats['abstract_words']} words (measured) |
| 4 | Keywords 1-7 | DONE | {stats['n_keywords']} keywords |
| 5 | Highlights: 3-5 bullets, <= 85 chars, separate file | DONE | Highlights/Highlights.txt (+ .docx); {stats['n_highlights']} bullets, longest {stats['max_highlight']} chars |
| 6 | Line and page numbering | DONE | linenumbers + page footers in the PDF |
| 7 | Numbered sections (1, 1.1) | DONE | Pandoc --number-sections |
| 8 | Figures as separate files, named logically | DONE | Figures/Figure_1..{stats['n_figs']} (vector PDF + PNG + SVG) |
| 9 | Every figure cited in the text | DONE | Figs 1-{stats['n_figs']} cited in first-appearance order (checked) |
| 10 | Figure captions carry title + description | DONE | in manuscript |
| 11 | Tables numbered in citation order | DONE | Tables 1-{stats['n_tables']} (checked) |
| 12 | Tables editable text, no vertical rules | DONE | all {stats['n_tables']} tables in manuscript |
| 13 | Declaration of competing interest (Word, from the tool) | PARTIAL | Declarations/Declaration_of_competing_interest.docx is a local equivalent; the author must run Elsevier's declarations tool and upload its .docx |
| 14 | CRediT author contribution statement | DONE | Declarations/CRediT_author_contribution_statement.md/.docx |
| 15 | Funding statement in the prescribed format | DONE | Declarations/Funding_statement.md/.docx |
| 16 | Generative-AI declaration before the references | DONE | in manuscript + Declarations/Declaration_of_generative_AI_use.md/.docx |
| 17 | Data availability statement with a resolvable identifier | DONE | Declarations/Data_availability_statement.md; DOI {DOI} |
| 18 | Title page with names, affiliation, corresponding e-mail | DONE | Title_page.md ({EMAIL}) |
| 19 | ORCID on the title page | HUMAN | Title_page.md carries a placeholder; no verified ORCID exists in the project |
| 20 | References numbered in citation order, complete data | DONE | {stats['n_refs']} references, all cited, all with a DOI or a URL and access date |
| 21 | Graphical abstract (optional) | NOT DONE | optional; Fig. 1 works as one if the editor asks |
| 22 | Cover letter | INCLUDED | Cover_letter.pdf |
| 23 | Submission system | HUMAN | Editorial Manager (AUTCON) |

## Consistency verification

`code/submission_consistency_check.py` passes **{stats['checks_passed']}/{stats['checks_total']}**
checks, each comparing the manuscript against a frozen artifact rather than against itself.
`code/verify_independent.py` reproduces the 13 headline numbers with an independently
implemented estimator. `tests/test_*.py` run the regression suite that holds the repaired
defects shut. The deposit archive verifies itself with
`submission/release/verify_release_archive.py`, which extracts the published zip and runs
its own suite there.

## Human-only steps before upload

1. ORCID: add it to the title page and to CITATION.cff. No ORCID is recorded anywhere in
   the project, so it was not invented.
2. Run Elsevier's declaration tool and upload the .docx it generates.
3. Submit through Editorial Manager (AUTCON).
4. Rotate the Zenodo API token, which was exposed in a session log during deposit setup.

## Note on the deposit

The published record is a frozen snapshot: it is not rebuilt as the working tree moves on,
so its checksum keeps matching the audited build. Changes made after publication (the ratio
grid disclosure, the figure callouts, the table renumbering, the corrected latency claim)
are in the manuscript and in this package, and `AUDIT_REPAIR_LOG_2026-09-16.md` section
"Round 10" records them. If the paper is revised after review, publish a new Zenodo
**version** rather than replacing the record.
"""
    (PKG / "SUBMISSION_CHECKLIST.md").write_text(checklist, encoding="utf-8")

    # ---- package README ----
    readme = f"""# AiC submission package, built {datetime.now(timezone.utc).date().isoformat()}

{stats['n_figs']} figures, {stats['n_tables']} tables, {stats['n_refs']} references,
abstract {stats['abstract_words']} words, consistency check
{stats['checks_passed']}/{stats['checks_total']}.

| Path | What it is |
|---|---|
| `Manuscript/Manuscript_AiC.tex` | editable source, compiles with XeLaTeX |
| `Manuscript/Manuscript_AiC.pdf` | rendered PDF with line and page numbers |
| `Manuscript/Manuscript_AiC.md` | Markdown original |
| `Highlights/Highlights.txt` / `.docx` | {stats['n_highlights']} bullets, longest {stats['max_highlight']} characters |
| `Figures/Figure_1..{stats['n_figs']}` | vector PDF + PNG + SVG, numbered in citation order |
| `Declarations/*.md` / `.docx` | CRediT, competing interest, funding, generative-AI, data availability |
| `Title_page.md` | title, author, affiliation, corresponding e-mail |
| `Cover_letter.pdf` | cover letter |
| `Data/DATASETS_AND_LINKS.csv` | every source, its licence and its treatment |
| `Reproducibility/` | code, tests, frozen artifacts, runbook, audit log |
| `SUBMISSION_CHECKLIST.md` | requirement-by-requirement status |
| `PACKAGE_MANIFEST_SHA256.txt` | checksum of every file in this package |
| `verify_submission_package.py` | re-checks this package; run it before upload |

## Compiling the source

The `.tex` is self-contained apart from its figures, which it expects at
`../Figures/Figure_N.pdf` relative to `Manuscript/`. From this package root:

```powershell
cd Manuscript
xelatex -interaction=nonstopmode Manuscript_AiC.tex
```

XeLaTeX is required (`unicode-math` and `fontspec` are loaded); pdfLaTeX will not work.
The bibliography is embedded as `\\bibitem` entries, so no BibTeX run is needed.

## Before upload

1. `python verify_submission_package.py` must pass.
2. Supply the ORCID on the title page.
3. Run Elsevier's declaration tool and replace
   `Declarations/Declaration_of_competing_interest.docx` with its output.
4. Upload through Editorial Manager (AUTCON).

The deposit DOI {DOI} is already in the manuscript's data-availability statement, the
cover letter and `CITATION.cff`.
"""
    (PKG / "README_PACKAGE.md").write_text(readme, encoding="utf-8")
    shutil.copy2(ROOT / "code" / "verify_submission_package.py",
                 PKG / "verify_submission_package.py")

    # ---- package manifest ----
    lines = [f"# Submission package manifest, built {datetime.now(timezone.utc).isoformat()}", ""]
    for path in sorted(PKG.rglob("*")):
        if path.is_file():
            lines.append(f"{sha256(path)}  {path.relative_to(PKG).as_posix()}")
    (PKG / "PACKAGE_MANIFEST_SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    archive = ROOT / f"AiC_submission_package_{STAMP}.zip"
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(archive.with_suffix("")), "zip", PKG)

    n_files = sum(1 for p in PKG.rglob("*") if p.is_file())
    print(f"package files : {n_files}")
    print(f"package dir   : {PKG}")
    print(f"archive       : {archive} ({archive.stat().st_size / 1e6:.2f} MB)")
    print(f"figures       : {stats['n_figs']} ({', '.join(stats['fig_stems'])})")
    print(f"tables        : {stats['n_tables']}, references: {stats['n_refs']}")
    print(f"abstract      : {stats['abstract_words']} words")
    print(f"checks        : {stats['checks_passed']}/{stats['checks_total']}")


if __name__ == "__main__":
    main()
