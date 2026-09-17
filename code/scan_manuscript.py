"""Scan the manuscript for numbers and phrases that the corrections superseded.

Two jobs: count the abstract (the AiC guide caps it at 150 words) and flag any
stale value or withdrawn claim that survived the rewrite. Run before every
build; a hit is a defect, not a warning.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

STALE = [
    "47,142", "281,817", "1/(1+C/L)", "1/(1+r)", "45-63%", "45\u201363%",
    "0.20-0.35", "0.20\u20130.35", "0.377", "0.398", "506 test positives",
    "0.438", "0.246", "0.239", "0.173", "assumption-free",
    "audited, not assumed", "exposure-miss frontier", "exposure\u2013miss frontier",
    "24-lift campaign reports", "74.7%", "11,904", "reserved for inspection",
    "2025 is evaluated once", "The decision fails at the detector", "R_mm", "DR_deg",
    "prescribed risk c", "critical fractile",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", default="manuscript/Manuscript_AiC_WORKING_DRAFT.md")
    args = parser.parse_args()
    path = Path(args.manuscript)
    text = path.read_text(encoding="utf-8")

    abstract = text.split("# Abstract {-}", 1)[1].split("**Keywords:**", 1)[0].strip()
    words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\u2019./+-]*", abstract))
    print(f"abstract words: {words} (target 150)")

    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for token in STALE:
            if token in line:
                hits.append((i, token, line.strip()[:110]))
    if hits:
        print(f"STALE references: {len(hits)}")
        for i, token, line in hits:
            print(f"  line {i}: [{token}] {line}")
    else:
        print("stale references: none")

    # every figure path must exist
    for match in re.finditer(r"\]\(([^)]+\.pdf)\)", text):
        target = (path.parent / match.group(1)).resolve()
        if not target.exists():
            print(f"MISSING FIGURE: {match.group(1)}")
    print("figure check done")


if __name__ == "__main__":
    main()
