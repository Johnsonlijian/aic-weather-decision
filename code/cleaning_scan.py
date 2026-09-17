"""Pre-submission cleaning scan.

Mechanical checks that a hostile reviewer or a copy-editor would run, reported with
line numbers so each hit can be judged rather than blanket-deleted.

Categories:
  traces      - project tooling, internal paths, version labels, development notes
  ai_tells    - phrasing that reads as generated text
  defensive   - repeated disclaimers, counted per section so redundancy is visible
  style       - em-dash density, paragraph length uniformity, hedging
  refs        - bibliography formatting problems
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

TRACE_PATTERNS = [
    (r"\bv\d+(\.\d+)?\b", "version label"),
    (r"\b(g5_|epochs_|code/|outputs/|\.py\b|\.json\b|\.csv\b)", "artifact or script reference"),
    (r"\b(round|gate|audit|checker|consistency check)\b", "project-process word"),
    (r"TODO|FIXME|TBD|XXX|placeholder", "placeholder marker"),
    (r"\b(WORKING|DRAFT|superseded|deprecated)\b", "draft marker"),
    (r"[A-Z]:\\\\|/mnt/|C:\\Users", "absolute path"),
]

AI_PATTERNS = [
    (r"it is (worth|important|notable) (noting|to note)", "stock hedging opener"),
    (r"\b(delve|underscore[sd]?|leverage[ds]?|robust(ly)? (demonstrate|show))\b", "generated-text verb"),
    (r"plays? a (crucial|key|vital|pivotal) role", "stock importance claim"),
    (r"not only .{0,60} but also", "mechanical correlative"),
    (r"\b(furthermore|moreover|additionally|in conclusion|overall)\b", "connective padding"),
    (r"\b(it is|this is) (also )?(clear|evident|obvious) that\b", "empty assertion"),
    (r"\bharness(ing)? the power\b", "stock phrase"),
    (r"\bin today's\b", "stock opener"),
    (r"a (growing|burgeoning) body of", "stock phrase"),
    (r"\bseamless(ly)?\b|\bcutting-edge\b|\bstate-of-the-art\b", "promotional adjective"),
]

DEFENSIVE_PATTERNS = [
    (r"not a (safety|monetary|compliance|crane-level|structural)", "negative scope claim"),
    (r"does not (authorise|authorize|assert|claim|make)", "negative scope claim"),
    (r"remain(s)? outside the scope", "scope disclaimer"),
    (r"no (monetary|safety|schedule) (benefit|saving)", "benefit disclaimer"),
    (r"should not be (read|taken|interpreted)", "interpretation guard"),
    (r"\bnot\b.{0,30}\bverified lifting|verified lifting-compliance", "compliance guard"),
]


def scan(text: str, patterns, label: str) -> list[tuple[int, str, str]]:
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for pat, why in patterns:
            for m in re.finditer(pat, line, flags=re.I):
                hits.append((i, why, m.group(0)))
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root: Path = args.root
    md = root / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md"
    text = md.read_text(encoding="utf-8")
    body = text.split("\n---\n", 2)[-1] if text.startswith("---") else text

    print("=" * 78)
    print("INTERNAL TRACES")
    print("=" * 78)
    traces = scan(body, TRACE_PATTERNS, "trace")
    if not traces:
        print("  none")
    for line_no, why, hit in traces:
        ctx = body.splitlines()[line_no - 1].strip()
        print(f"  L{line_no:<4} [{why}] {hit!r}")
        print(f"        {ctx[:150]}")

    print()
    print("=" * 78)
    print("AI-WRITING TELLS")
    print("=" * 78)
    tells = scan(body, AI_PATTERNS, "ai")
    counts = Counter(w for _, w, _ in tells)
    if not tells:
        print("  none")
    for line_no, why, hit in tells:
        print(f"  L{line_no:<4} [{why}] {hit!r}")

    print()
    print("=" * 78)
    print("OVER-DEFENSIVENESS")
    print("=" * 78)
    defensive = scan(body, DEFENSIVE_PATTERNS, "def")
    print(f"  total scope/benefit disclaimers: {len(defensive)}")
    # attribute each hit to its section
    sections = [(m.start(), m.group(0)) for m in re.finditer(r"^#{1,2} .+$", body, flags=re.M)]
    def section_of(pos: int) -> str:
        name = "(front)"
        for start, title in sections:
            if start <= pos:
                name = title
            else:
                break
        return name
    offsets, acc = [], 0
    for line in body.splitlines(keepends=True):
        offsets.append(acc)
        acc += len(line)
    per_section = Counter()
    for line_no, why, hit in defensive:
        per_section[section_of(offsets[line_no - 1])] += 1
    for name, n in per_section.most_common():
        print(f"  {n:2d}  {name[:90]}")

    print()
    print("=" * 78)
    print("STYLE")
    print("=" * 78)
    em = len(re.findall(r"—|--", body))
    print(f"  em-dash / double-hyphen count: {em}")
    paras = [p for p in body.split("\n\n") if len(p.split()) > 25]
    lens = [len(p.split()) for p in paras]
    if lens:
        import statistics
        print(f"  paragraphs >25 words: {len(lens)} | mean {statistics.mean(lens):.0f} "
              f"| sd {statistics.pstdev(lens):.0f} | min {min(lens)} max {max(lens)}")
    for pat, why in ((r"\bwe\b", "first person plural"), (r"\bI\b", "first person singular")):
        n = len(re.findall(pat, body))
        print(f"  {why}: {n}")

    print()
    print("=" * 78)
    print("REFERENCES")
    print("=" * 78)
    refs = json.loads((root / "manuscript" / "references.json").read_text(encoding="utf-8"))
    problems = []
    for r in refs:
        rid = r.get("id", "?")
        if "&Amp;" in json.dumps(r) or "&amp;" in json.dumps(r):
            problems.append((rid, "HTML entity in a field"))
        if r.get("type") == "article-journal":
            ct = r.get("container-title", "")
            if ct and not re.search(r"\b(J|Journal|Bull|Proc|Mon|Rev|Sci|Eng|Struct|Geotech|"
                                    r"Comput|Autom|Water|Res|Lett|Int|Adv|Mech|Dyn|Saf|Reliab)\b", ct):
                problems.append((rid, f"check journal name: {ct}"))
            if not r.get("volume"):
                problems.append((rid, "journal article without volume"))
        if not (r.get("DOI") or r.get("URL")):
            problems.append((rid, "no DOI or URL"))
        for a in r.get("author", []):
            if "family" not in a and "literal" not in a:
                problems.append((rid, "author without family name"))
    print(f"  entries: {len(refs)}")
    if problems:
        for rid, why in problems:
            print(f"  {rid:26s} {why}")
    else:
        print("  no formatting problems detected")

    # journal-name abbreviation candidates
    print()
    print("  journal names as stored (check LTWA abbreviation at copy-edit):")
    for r in refs:
        if r.get("type") == "article-journal":
            print(f"    {r.get('container-title','')}")


if __name__ == "__main__":
    main()
