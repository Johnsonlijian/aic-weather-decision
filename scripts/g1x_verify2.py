#!/usr/bin/env python
"""Two-route DOI verification (doi.org content negotiation + OpenAlex), no Crossref.

Used while the Crossref query API is throttled; the Crossref column is added later by
g1x_lit.py verify. Writes raw JSON as the audit trail.
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from g1x_lit import doi_content_negotiation, openalex_doi  # noqa: E402

if __name__ == "__main__":
    dois = json.load(open(sys.argv[1], encoding="utf-8"))
    seen, uniq = set(), []
    for d in dois:
        d = d.strip().lower()
        if d and d not in seen:
            seen.add(d)
            uniq.append(d)
    out = []
    for doi in uniq:
        rec = {"doi": doi, "verify_date": "2026-09-15",
               "doi_resolve": doi_content_negotiation(doi), "openalex": openalex_doi(doi)}
        out.append(rec)
        dr, oa = rec["doi_resolve"], rec["openalex"]
        print(f"{'R' if dr.get('resolve_verified') else '.'}{'O' if oa.get('openalex_verified') else '.'} "
              f"{doi:42s} {str(dr.get('year') or oa.get('year')):6s} {str(dr.get('title') or oa.get('title'))[:78]}")
        time.sleep(0.4)
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nWROTE {sys.argv[2]} ({len(out)} unique DOIs)")
