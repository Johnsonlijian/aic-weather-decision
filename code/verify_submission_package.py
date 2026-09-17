#!/usr/bin/env python
"""Verify a built AiC submission package.

Checks the package as the author will hand it over, not as it was assembled:

  * every file in PACKAGE_MANIFEST_SHA256.txt hashes to the value recorded there;
  * the packaged PDF is byte-identical to the project's current manuscript PDF, so the
    package cannot ship a stale render;
  * the figure set matches the manuscript exactly - same count, same order, and every
    format that exists for that figure;
  * each declaration exists as both .md and .docx;
  * the deposit DOI appears in the data-availability statement and on the title page;
  * no superseded number, old package name or placeholder survives anywhere in the
    package's text, which is how "125 chars", "22 references" and "the deposit DOI is
    inserted at acceptance" previously travelled into a submission.

Usage:  python code/verify_submission_package.py [--pkg submission_package_AiC_2026-09-17]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PKG = ROOT / "submission_package_AiC_2026-09-17"
DOI = "10.5281/zenodo.22803783"
# XeLaTeX lives in a per-user MiKTeX tree on this machine, not on PATH
shutil_which = shutil.which

# text that must not appear in a submission-facing document. Historical records are exempt
# from the prose tokens, because they deliberately quote superseded wording to document it -
# the audit log quotes the old working title, and the figure map names the uncited figure it
# is excluding. Placeholders are checked everywhere.
FORBIDDEN_EVERYWHERE = {
    "submission_package_AiC_2026-09-16": "an older package name",
}
FORBIDDEN_IN_SUBMISSION_TEXT = {
    "to be inserted": "an unfilled DOI placeholder",
    "125 chars": "the old, too-loose Highlights limit",
    "22 references": "the pre-audit reference count",
    "74/74": "the pre-audit check count",
    "Resolvability of weather-sensitive": "the project's working title",
    "reproduces the primary analysis exactly": "the withdrawn epoch-for-epoch claim",
}
# records, not submission prose: they may quote superseded text on purpose. The audit log
# quotes the old DOI placeholder and the old working title precisely to document that both
# were removed, so a placeholder inside a record is evidence of the fix rather than a defect.
# The submission-facing documents are still checked for it directly.
RECORD_PATHS = ("Reproducibility/AUDIT_REPAIR_LOG", "Figures/FIGURE_MAP.md",
                "Reproducibility/manuscript_numbers")
SCAN_SUFFIXES = {".md", ".txt", ".tex", ".json", ".cff", ".csv"}
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pkg", default=str(DEFAULT_PKG))
    ap.add_argument("--compile", action="store_true",
                    help="also compile the packaged .tex, in a temporary copy so the "
                         "package itself is left untouched")
    ap.add_argument("--pages", type=int, default=None,
                    help="with --compile, require this page count")
    args = ap.parse_args()
    pkg = Path(args.pkg)

    check("the package directory exists", pkg.is_dir(), str(pkg))
    if not pkg.is_dir():
        print(f"missing package: {pkg}", file=sys.stderr)
        return 2

    # ---------- 1. manifest integrity ----------
    manifest = pkg / "PACKAGE_MANIFEST_SHA256.txt"
    check("the package carries a manifest", manifest.exists())
    if manifest.exists():
        entries = {}
        for line in manifest.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([0-9a-f]{64})  (.+)$", line)
            if m:
                entries[m.group(2)] = m.group(1)
        check("the manifest is non-empty", len(entries) > 0, f"{len(entries)} entries")
        bad, missing = [], []
        for rel, want in entries.items():
            p = pkg / rel
            if not p.exists():
                missing.append(rel)
            elif sha256(p) != want:
                bad.append(rel)
        check("every manifested file is present", not missing,
              f"missing: {missing[:5] or 'none'}")
        check("every manifested file matches its recorded SHA-256", not bad,
              f"mismatched: {bad[:5] or 'none'}")
        on_disk = {p.relative_to(pkg).as_posix() for p in pkg.rglob("*") if p.is_file()}
        extra = sorted(on_disk - set(entries) - {manifest.name})
        check("no file was added after the manifest was written", not extra,
              f"unmanifested: {extra[:5] or 'none'}")

    # ---------- 2. the PDF is the current render ----------
    live_pdf = ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.pdf"
    pkg_pdf = pkg / "Manuscript" / "Manuscript_AiC.pdf"
    check("the packaged PDF exists", pkg_pdf.exists())
    if pkg_pdf.exists() and live_pdf.exists():
        check("the packaged PDF is byte-identical to the current manuscript PDF",
              sha256(pkg_pdf) == sha256(live_pdf),
              f"{pkg_pdf.stat().st_size:,} vs {live_pdf.stat().st_size:,} bytes")
    for name in ("Manuscript_AiC.tex", "Manuscript_AiC.md"):
        check(f"the packaged {name} exists", (pkg / "Manuscript" / name).exists())

    # ---------- 3. figures match the manuscript ----------
    md = (ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md").read_text(encoding="utf-8")
    stems = list(dict.fromkeys(re.findall(r"\]\([^)]*?/([A-Za-z0-9_]+)\.pdf\)", md)))
    fig_dir = pkg / "Figures"
    for i, stem in enumerate(stems, start=1):
        for ext in ("pdf", "png", "svg"):
            src = ROOT / "paper_figures" / "output" / f"{stem}.{ext}"
            if src.exists():
                got = fig_dir / f"Figure_{i}.{ext}"
                check(f"Figure_{i}.{ext} matches {stem}.{ext}",
                      got.exists() and sha256(got) == sha256(src))
    shipped = sorted(p.stem for p in fig_dir.glob("*.pdf"))
    check("the package ships exactly the figures the manuscript cites",
          shipped == [f"Figure_{i}" for i in range(1, len(stems) + 1)],
          f"{shipped}")
    check("the uncited risk-efficiency figure is not shipped",
          not any("risk_efficiency" in p.name for p in fig_dir.iterdir()))
    check("the figure map is documented", (fig_dir / "FIGURE_MAP.md").exists())

    # ---------- 4. declarations ----------
    decl_dir = pkg / "Declarations"
    for stem in ("CRediT_author_contribution_statement",
                 "Declaration_of_competing_interest",
                 "Funding_statement",
                 "Declaration_of_generative_AI_use",
                 "Data_availability_statement"):
        check(f"declaration {stem}.md present", (decl_dir / f"{stem}.md").exists())
        check(f"declaration {stem}.docx present", (decl_dir / f"{stem}.docx").exists())
    dav = decl_dir / "Data_availability_statement.md"
    if dav.exists():
        body = dav.read_text(encoding="utf-8")
        check("the data-availability statement carries the deposit DOI", DOI in body,
              "DOI present" if DOI in body else "DOI MISSING")
        check("the data-availability statement carries the repository URL",
              "github.com/Johnsonlijian/aic-weather-decision" in body)

    # ---------- 5. title page and checklist ----------
    tp = pkg / "Title_page.md"
    check("the title page exists", tp.exists())
    if tp.exists():
        body = tp.read_text(encoding="utf-8")
        check("the title page carries the corresponding e-mail",
              "renlijian@imut.edu.cn" in body)
        check("the title page carries the DOI", DOI in body)
        check("the title page flags ORCID as outstanding, not invented",
              "ORCID" in body and "to be supplied" in body)
    cl = pkg / "SUBMISSION_CHECKLIST.md"
    check("the checklist exists", cl.exists())
    if cl.exists():
        body = cl.read_text(encoding="utf-8")
        n_figs = len(stems)
        check("the checklist reports the measured figure count",
              f"Figure_1..{n_figs}" in body, f"{n_figs} figures")
        check("the checklist does not mark the data statement as unfinished",
              "Data availability statement (Option C) | PARTIAL" not in body)
        check("the checklist carries the DOI", DOI in body)

    # ---------- 6. no superseded text anywhere ----------
    hits: dict[str, list[str]] = {}
    for p in pkg.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in SCAN_SUFFIXES:
            continue
        if p.name == "PACKAGE_MANIFEST_SHA256.txt":
            continue
        rel = p.relative_to(pkg).as_posix()
        is_record = any(rel.startswith(r) for r in RECORD_PATHS)
        try:
            body = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        tokens = dict(FORBIDDEN_EVERYWHERE)
        if not is_record:
            tokens.update(FORBIDDEN_IN_SUBMISSION_TEXT)
        for token, why in tokens.items():
            if token in body:
                hits.setdefault(f"{token} ({why})", []).append(rel)
    check("no superseded number, old package name or placeholder survives",
          not hits, "; ".join(f"{k}: {v[:2]}" for k, v in hits.items()) or "none")

    # a placeholder can hide in a submission-facing document even when the records are clean
    submission_files = [pkg / "Title_page.md", pkg / "SUBMISSION_CHECKLIST.md",
                        pkg / "README_PACKAGE.md", pkg / "Cover_letter.md"]
    submission_files += list((pkg / "Declarations").glob("*.md"))
    submission_files += list((pkg / "Highlights").glob("*.txt"))
    submission_files += list((pkg / "Manuscript").glob("Manuscript_AiC.*"))
    leftover = []
    for p in submission_files:
        if p.exists() and re.search(r"to be inserted|\[insert|TODO|TBD|XXX",
                                    p.read_text(encoding="utf-8", errors="ignore")):
            leftover.append(p.relative_to(pkg).as_posix())
    check("no submission-facing document carries a placeholder or TODO", not leftover,
          f"{leftover or 'none'}")

    # ---------- 6b. the packaged LaTeX source must compile where it sits ----------
    tex_path = pkg / "Manuscript" / "Manuscript_AiC.tex"
    check("the packaged .tex exists", tex_path.exists())
    if tex_path.exists():
        tex = tex_path.read_text(encoding="utf-8")
        graphics = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}", tex)
        check("the packaged .tex includes its figures", bool(graphics),
              f"{len(graphics)} includegraphics")
        unresolved = [g for g in graphics if not (tex_path.parent / g).resolve().exists()]
        check("every figure path in the packaged .tex resolves inside the package",
              not unresolved, f"unresolved: {unresolved or 'none'}")
        check("the packaged .tex uses the journal figure names",
              all(re.search(r"Figure_\d+\.pdf$", g) for g in graphics),
              f"{graphics[:2]}")
        check("the packaged .tex no longer refers to the working-draft file name",
              "WORKING_DRAFT" not in tex)

    # ---------- 7. nothing that may not be redistributed ----------
    bad_paths = [p.relative_to(pkg).as_posix() for p in pkg.rglob("*")
                 if p.is_file() and (".env" in p.name.lower()
                                     or "credential" in p.name.lower()
                                     or p.suffix.lower() in {".pyc"})]
    check("no credentials or build residue", not bad_paths, f"{bad_paths[:5] or 'none'}")
    raw = [p.relative_to(pkg).as_posix() for p in pkg.rglob("*")
           if "data/raw" in p.relative_to(pkg).as_posix()]
    check("no raw third-party archives", not raw, f"{raw[:3] or 'none'}")

    # ---------- 8. the packaged source compiles, in a throwaway copy ----------
    if args.compile:
        import subprocess
        import tempfile

        engine = (shutil_which("xelatex")
                  or str(Path(os.environ.get("LOCALAPPDATA", ""))
                         / "Programs/MiKTeX/miktex/bin/x64/xelatex.exe"))
        check("a XeLaTeX engine is available", Path(engine).exists(), engine)
        if Path(engine).exists():
            with tempfile.TemporaryDirectory(prefix="aic_pkg_compile_") as tmp:
                work = Path(tmp) / "pkg"
                shutil.copytree(pkg, work)
                man = work / "Manuscript"
                ok = True
                for _ in range(2):
                    proc = subprocess.run(
                        [engine, "-interaction=nonstopmode", "-halt-on-error",
                         "Manuscript_AiC.tex"],
                        cwd=man, capture_output=True, text=True)
                    ok = ok and proc.returncode == 0
                out_pdf = man / "Manuscript_AiC.pdf"
                check("the packaged .tex compiles with XeLaTeX", ok and out_pdf.exists())
                if out_pdf.exists():
                    pages = None
                    try:
                        from pypdf import PdfReader
                        pages = len(PdfReader(out_pdf).pages)
                    except Exception:
                        info = subprocess.run(["pdfinfo", str(out_pdf)],
                                              capture_output=True, text=True).stdout
                        m = re.search(r"^Pages:\s+(\d+)", info, re.M)
                        pages = int(m.group(1)) if m else None
                    shipped = None
                    try:
                        from pypdf import PdfReader
                        shipped = len(PdfReader(pkg / "Manuscript" / "Manuscript_AiC.pdf").pages)
                    except Exception:
                        pass
                    check("the recompiled PDF has the same page count as the shipped PDF",
                          pages is not None and pages == shipped,
                          f"recompiled {pages} vs shipped {shipped}")
                    if args.pages is not None:
                        check(f"the recompiled PDF has {args.pages} pages",
                              pages == args.pages, f"got {pages}")

    # ---------- report ----------
    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f": {detail}" if detail else ""))
    print(f"\n{len(results) - len(failed)}/{len(results)} package checks passed")
    if failed:
        print("\nFAILED:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
