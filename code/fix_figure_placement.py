"""Force in-place figure placement in the Pandoc-generated LaTeX.

Pandoc emits floating figures, which LaTeX may push to a page of their own and
leave large white gaps. The submission PDF should carry each figure next to its
reference, so every ``\\begin{figure}`` gets the ``[H]`` placement specifier that
the ``float`` package provides.
"""
from pathlib import Path
import sys

tex = Path(sys.argv[1] if len(sys.argv) > 1 else "Manuscript_AiC_WORKING_DRAFT.tex")
text = tex.read_text(encoding="utf-8")
count = text.count(r"\begin{figure}")
text = text.replace(r"\begin{figure}", r"\begin{figure}[H]")
tex.write_text(text, encoding="utf-8")
print(f"figures forced to [H]: {count}")
