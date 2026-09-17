#!/usr/bin/env python
"""G1-expansion literature retrieval + verification harness (2026-09-15).

Usage:
  python scripts/g1x_lit.py search   --spec sources/raw/g1x/spec.json
  python scripts/g1x_lit.py verify   --dois sources/raw/g1x/dois.json
  python scripts/g1x_lit.py verify-file --in sources/raw/g1x/candidates.json --out sources/raw/g1x/verified.json

Discovery: Crossref /works?query.bibliographic=...&rows=5 and OpenAlex /works?search=...&per_page=5
Verification: Crossref /works/{doi} + OpenAlex /works/https://doi.org/{doi} (+ DOI content negotiation)
No paid APIs. Raw responses written to disk as the audit trail.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:  # keep a GBK/cp1252 console from killing the run on non-ASCII titles
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

MAILTO = "research@example.org"
UA = "IMUT-lit-audit/1.0 (mailto:research@example.org)"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get(url: str, tries: int = 4, sleep: float = 2.0):
    last = None
    for i in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(sleep * (i + 1) * 2)
                continue
            return {"__error__": last, "__url__": url}
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            time.sleep(sleep * (i + 1))
    return {"__error__": last, "__url__": url}


def crossref_query(q: str, rows: int = 5):
    url = ("https://api.crossref.org/works?query.bibliographic="
           + urllib.parse.quote(q) + f"&rows={rows}&mailto={MAILTO}")
    d = _get(url)
    out = []
    for it in (d.get("message", {}) or {}).get("items", []) or []:
        out.append({
            "source": "crossref",
            "doi": (it.get("DOI") or "").lower(),
            "title": (it.get("title") or [""])[0],
            "container": (it.get("container-title") or [""])[0],
            "year": ((it.get("issued", {}) or {}).get("date-parts", [[None]])[0] or [None])[0],
            "type": it.get("type"),
            "authors": [f"{a.get('family','')} {a.get('given','')}".strip()
                        for a in (it.get("author") or [])][:12],
            "url": it.get("URL"),
        })
    return {"query": q, "api": "crossref", "url": url, "error": d.get("__error__"), "items": out}


def openalex_query(q: str, per_page: int = 5):
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q)
           + f"&per_page={per_page}&mailto={MAILTO}")
    d = _get(url)
    out = []
    for it in (d.get("results") or []):
        out.append({
            "source": "openalex",
            "doi": (it.get("doi") or "").replace("https://doi.org/", "").lower(),
            "title": it.get("title") or it.get("display_name"),
            "container": ((it.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "year": it.get("publication_year"),
            "type": it.get("type"),
            "authors": [a.get("author", {}).get("display_name") for a in (it.get("authorships") or [])][:12],
            "cited_by": it.get("cited_by_count"),
            "oa": (it.get("open_access") or {}).get("oa_status"),
            "url": it.get("id"),
        })
    return {"query": q, "api": "openalex", "url": url, "error": d.get("__error__"), "items": out}


def crossref_doi(doi: str):
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={MAILTO}"
    d = _get(url, tries=3)
    m = d.get("message") if isinstance(d, dict) else None
    if not m:
        return {"doi": doi, "verified": False, "error": d.get("__error__") if isinstance(d, dict) else "no message",
                "method": "crossref /works/{doi}", "url": url}
    auth = m.get("author") or []
    return {
        "doi": (m.get("DOI") or doi).lower(),
        "verified": True,
        "method": "Crossref REST /works/{doi}",
        "url": url,
        "title": (m.get("title") or [""])[0],
        "container": (m.get("container-title") or [""])[0],
        "short_container": (m.get("short-container-title") or [""])[0] if m.get("short-container-title") else "",
        "year": ((m.get("issued", {}) or {}).get("date-parts", [[None]])[0] or [None])[0],
        "issued_date_parts": (m.get("issued", {}) or {}).get("date-parts"),
        "type": m.get("type"),
        "volume": m.get("volume"),
        "issue": m.get("issue"),
        "page": m.get("page"),
        "article_number": m.get("article-number"),
        "publisher": m.get("publisher"),
        "authors": [{"family": a.get("family", ""), "given": a.get("given", "")} for a in auth],
        "license": [l.get("URL") for l in (m.get("license") or [])][:4],
        "abstract_present": bool(m.get("abstract")),
        "abstract": (m.get("abstract") or "")[:4000],
        "refs_count": m.get("reference-count"),
        "is_referenced_by_count": m.get("is-referenced-by-count"),
    }


def openalex_doi(doi: str):
    url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}?mailto={MAILTO}"
    d = _get(url, tries=3)
    if not isinstance(d, dict) or d.get("__error__") or not d.get("id"):
        return {"doi": doi, "openalex_verified": False,
                "error": d.get("__error__") if isinstance(d, dict) else "no record", "url": url}
    loc = d.get("primary_location") or {}
    return {
        "doi": doi,
        "openalex_verified": True,
        "method": "OpenAlex /works/https://doi.org/{doi}",
        "url": url,
        "openalex_id": d.get("id"),
        "title": d.get("title") or d.get("display_name"),
        "container": ((loc.get("source") or {}) or {}).get("display_name"),
        "year": d.get("publication_year"),
        "type": d.get("type"),
        "cited_by": d.get("cited_by_count"),
        "oa_status": (d.get("open_access") or {}).get("oa_status"),
        "oa_url": (d.get("open_access") or {}).get("oa_url"),
        "best_oa_location": (d.get("best_oa_location") or {}).get("pdf_url") if d.get("best_oa_location") else None,
        "abstract_inverted_present": bool(d.get("abstract_inverted_index")),
        "concepts": [c.get("display_name") for c in (d.get("concepts") or [])][:8],
        "topics": [t.get("display_name") for t in (d.get("topics") or [])][:6],
    }


def doi_content_negotiation(doi: str):
    """Third independent route: doi.org content negotiation (citation JSON)."""
    url = f"https://doi.org/{doi}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.citationstyles.csl+json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        return {"doi": doi, "resolve_verified": True, "method": "doi.org content negotiation (CSL-JSON)",
                "title": d.get("title"), "container": d.get("container-title"),
                "year": ((d.get("issued", {}) or {}).get("date-parts", [[None]])[0] or [None])[0],
                "type": d.get("type"), "publisher": d.get("publisher")}
    except Exception as e:  # noqa: BLE001
        return {"doi": doi, "resolve_verified": False, "method": "doi.org content negotiation (CSL-JSON)",
                "error": f"{type(e).__name__}: {e}"}


def cmd_search(args):
    spec = json.load(open(args.spec, encoding="utf-8"))
    outdir = os.path.join(ROOT, "sources", "raw", "g1x")
    os.makedirs(outdir, exist_ok=True)
    results = []
    for block in spec:
        q = block["query"]
        rows = block.get("rows", 5)
        rec = {"id": block.get("id"), "direction": block.get("direction"), "query": q,
               "crossref": crossref_query(q, rows), "openalex": openalex_query(q, rows)}
        results.append(rec)
        print(f"[{block.get('id')}] {q}")
        for src in ("crossref", "openalex"):
            for it in rec[src]["items"]:
                print(f"   {src:9s} {str(it.get('year')):5s} {it.get('doi')}  {str(it.get('title'))[:95]}")
        time.sleep(1.0)
    out = os.path.join(outdir, args.out)
    json.dump(results, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nWROTE {out}  ({len(results)} query blocks)")


def cmd_verify(args):
    dois = json.load(open(args.dois, encoding="utf-8"))
    out = []
    for doi in dois:
        rec = {"doi": doi, "crossref": crossref_doi(doi), "openalex": openalex_doi(doi),
               "doi_resolve": doi_content_negotiation(doi), "verify_date": "2026-09-15"}
        out.append(rec)
        cr = rec["crossref"]
        print(f"{'OK ' if cr.get('verified') else 'FAIL'} {doi:45s} {str(cr.get('year')):6s} {str(cr.get('title'))[:70]}")
        time.sleep(0.5)
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nWROTE {args.out}  ({len(out)} records)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("--spec", required=True)
    s.add_argument("--out", default="search.json"); s.set_defaults(func=cmd_search)
    v = sub.add_parser("verify"); v.add_argument("--dois", required=True)
    v.add_argument("--out", required=True); v.set_defaults(func=cmd_verify)
    a = ap.parse_args()
    a.func(a)
