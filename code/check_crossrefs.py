"""Verify every internal cross-reference against the manuscript's own numbering."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "manuscript" / "Manuscript_AiC_WORKING_DRAFT.md").read_text(encoding="utf-8")
body = text.split("\n---\n", 2)[-1]
lines = body.splitlines()

# build the true numbering and the line ranges of each section
sections: list[tuple[int, str, str]] = []   # (line index, number, title)
n1 = n2 = 0
for i, line in enumerate(lines):
    m1 = re.match(r"^# (?!#)(.+)$", line)
    m2 = re.match(r"^## (?!#)(.+)$", line)
    if m1:
        name = m1.group(1).strip()
        if name.endswith("{-}"):
            continue
        n1 += 1
        n2 = 0
        sections.append((i, str(n1), name))
    elif m2 and n1:
        n2 += 1
        sections.append((i, f"{n1}.{n2}", m2.group(1).strip()))

def containing(lineno: int) -> str:
    current = "(front)"
    for idx, num, _title in sections:
        if idx < lineno:
            current = num
        else:
            break
    return current

print(f"{'line':>5} {'says':>10}  {'is in':>7}  verdict")
problems = 0
for i, line in enumerate(lines, 1):
    for m in re.finditer(r"Section (\d+(?:\.\d+)?)", line):
        target = m.group(1)
        here = containing(i)
        valid = any(num == target for _idx, num, _t in sections)
        if not valid:
            verdict = "TARGET DOES NOT EXIST"
            problems += 1
        elif target == here:
            verdict = "SELF-REFERENCE"
            problems += 1
        else:
            verdict = "ok"
        title = next((t for _i, n, t in sections if n == target), "?")
        print(f"{i:>5} {target:>10}  {here:>7}  {verdict}"
              + (f"   -> {title[:52]}" if verdict == "ok" else ""))
print(f"\nproblem references: {problems}")
