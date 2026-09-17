#!/usr/bin/env python
"""Prove that an edit pass changed no number in the manuscript.

A readability rewrite, a style pass or a section move can silently drop or alter a figure.
The consistency checker guards the numbers it knows about, but a rewrite can disturb values
outside its list, so this keeps an independent census of every numeric token.

    python code/check_number_integrity.py --write    # record the baseline (before editing)
    python code/check_number_integrity.py --check    # compare against it (after editing)

The census counts tokens rather than checking named claims, so it catches a dropped decimal,
a changed thousands separator, or a figure that moved out of the text entirely. Run --write
deliberately: it overwrites the baseline, and the comparison is only meaningful against the
state you meant to preserve.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MS = ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md"
SNAPSHOT = ROOT / "outputs" / "manuscript_number_snapshot.json"
# signed integers, thousands separators and decimals, as they appear in the prose and tables
NUMBER = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def census() -> Counter:
    text = MS.read_text(encoding="utf-8")
    body = text.split("\n---\n", 2)[-1]      # drop the YAML front matter
    return Counter(NUMBER.findall(body))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="record the baseline")
    ap.add_argument("--check", action="store_true", help="compare against the baseline")
    args = ap.parse_args()
    if not (args.write or args.check):
        ap.error("choose --write or --check")

    counts = census()
    if args.write:
        SNAPSHOT.write_text(json.dumps(
            {"total_tokens": sum(counts.values()), "distinct": len(counts),
             "counts": dict(sorted(counts.items()))}, indent=2), encoding="utf-8")
        print(f"baseline recorded: {sum(counts.values())} numeric tokens, "
              f"{len(counts)} distinct -> {SNAPSHOT.relative_to(ROOT)}")
        return 0

    if not SNAPSHOT.exists():
        print(f"no baseline at {SNAPSHOT}; run --write before editing.", file=sys.stderr)
        return 2
    old = Counter(json.loads(SNAPSHOT.read_text(encoding="utf-8"))["counts"])
    removed = {k: old[k] - counts.get(k, 0) for k in old if old[k] > counts.get(k, 0)}
    added = {k: counts[k] - old.get(k, 0) for k in counts if counts[k] > old.get(k, 0)}

    print(f"tokens: {sum(old.values())} -> {sum(counts.values())}")
    print(f"distinct: {len(old)} -> {len(counts)}")
    if added:
        print(f"\nADDED ({len(added)}) - each must be a deliberate, artifact-backed addition:")
        for k in sorted(added, key=lambda x: -added[x]):
            print(f"   {k}: {old.get(k, 0)} -> {counts[k]}")
    if removed:
        print(f"\nREMOVED ({len(removed)}) - investigate before accepting:")
        for k in sorted(removed, key=lambda x: -removed[x]):
            print(f"   {k}: {old[k]} -> {counts.get(k, 0)}")
        print("\nFAIL - a number left the manuscript")
        return 1
    print("\nPASS - no numeric token was removed; the census is consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
