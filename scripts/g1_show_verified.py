"""Print a compact bibliographic digest from a g1_verify_dois.py result JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def fmt_authors(auths) -> str:
    out = []
    for a in auths or []:
        if isinstance(a, dict):
            fam, giv = a.get("family"), a.get("given") or ""
            if fam:
                initials = " ".join(f"{p[0]}." for p in giv.replace("-", " ").split() if p)
                out.append(f"{fam}, {initials}".strip())
            else:
                out.append(str(a))
        else:
            parts = str(a).split()
            if len(parts) >= 2:
                out.append(f"{parts[-1]}, " + " ".join(f"{p[0]}." for p in parts[:-1]))
            else:
                out.append(str(a))
    return "; ".join(out)


def main(path: str) -> None:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    for doi, rec in d.items():
        cr, oa = rec.get("crossref", {}), rec.get("openalex", {})
        if not (cr.get("ok") or oa.get("ok")):
            print(f"UNVERIFIED {doi} :: cr={cr.get('error')} oa={oa.get('error')}")
            continue
        src = cr if cr.get("ok") else oa
        auth = fmt_authors(src.get("authors"))
        print(f"DOI      : {doi}")
        print(f"TITLE    : {src.get('title')}")
        print(f"AUTHORS  : {auth}")
        print(f"VENUE    : {src.get('container')}")
        yr = src.get("year")
        vol = src.get("volume") or ""
        iss = src.get("issue") or ""
        pg = src.get("page") or src.get("article_number") or ""
        print(f"CITE     : {yr}; vol {vol}; no {iss}; pp {pg}")
        print(f"TYPE/PUB : {src.get('type')} / {src.get('publisher')}")
        print(f"CITED BY : cr={cr.get('is_referenced_by_count')} oa={oa.get('cited_by_count')}")
        print(f"OA       : {oa.get('is_oa')} {oa.get('oa_url') or ''}")
        print(f"ABS?     : cr={cr.get('abstract_present')} oa={oa.get('abstract_present')}")
        print(f"VERIFY   : {cr.get('verification_url') or oa.get('verification_url')}")
        print(f"OA-VERIFY: {oa.get('verification_url')}")
        print()


if __name__ == "__main__":
    main(sys.argv[1])
