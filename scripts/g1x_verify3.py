#!/usr/bin/env python
"""Gentle batch DOI verification: Crossref + OpenAlex + doi.org, long backoff on 429.

Writes one JSON record per DOI with all three routes and the exact verification URLs,
so any reader can reproduce the check by hand.
"""
from __future__ import annotations

import json
import sys
import time

HERE = __file__.rsplit("\\", 1)[0]
sys.path.insert(0, HERE)
from g1x_lit import crossref_doi, doi_content_negotiation, openalex_doi  # noqa: E402

if __name__ == "__main__":
    dois = json.load(open(sys.argv[1], encoding="utf-8-sig"))
    seen, uniq = set(), []
    for d in dois:
        d = d.strip().lower()
        if d and d not in seen:
            seen.add(d); uniq.append(d)
    out_path = sys.argv[2]
    records = []
    for doi in uniq:
        rec = {"doi": doi, "verify_date": "2026-09-15"}
        for key, fn in (("crossref", crossref_doi), ("openalex", openalex_doi),
                        ("doi_resolve", doi_content_negotiation)):
            rec[key] = fn(doi)
            time.sleep(1.5)
        ok = bool(rec["crossref"].get("verified"))
        records.append(rec)
        title = rec["crossref"].get("title") or rec["doi_resolve"].get("title") or rec["openalex"].get("title")
        print(f"{'OK ' if ok else 'FAIL'} {doi:40s} cr={rec['crossref'].get('verified')} "
              f"oa={rec['openalex'].get('openalex_verified')} res={rec['doi_resolve'].get('resolve_verified')} "
              f"| {str(title)[:70]}", flush=True)
        json.dump(records, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(2.0)
    print(f"\nWROTE {out_path} ({len(records)} DOIs)")
