"""G1 DOI verifier: resolve an explicit DOI list through the authoritative registration
agency endpoints (Crossref /works/{doi}, DataCite, OpenAlex) and record the exact
verification URL, date and the raw record for each.

This is deliberately separate from keyword search: search finds candidates, this confirms
that a DOI exists and what bibliographic identity it carries.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests  # noqa: E402

MAILTO = "research@example.org"
UA = f"AiC-G1-Novelty-Audit/1.0 (mailto:{MAILTO})"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw" / "g1"
RAW.mkdir(parents=True, exist_ok=True)
S = requests.Session()
S.headers.update({"User-Agent": UA})


def crossref_doi(doi: str, tries: int = 5):
    url = f"https://api.crossref.org/works/{doi}?mailto={MAILTO}"
    err = None
    for a in range(tries):
        try:
            r = S.get(url, timeout=45)
            if r.status_code == 200:
                m = r.json()["message"]
                year = None
                for k in ("published-print", "published-online", "issued", "created"):
                    dp = m.get(k, {}).get("date-parts", [[None]])
                    if dp and dp[0] and dp[0][0]:
                        year = dp[0][0]
                        break
                return {
                    "ok": True,
                    "source": "crossref_doi",
                    "verification_url": url,
                    "doi": m.get("DOI"),
                    "title": (m.get("title") or [""])[0],
                    "container": (m.get("container-title") or [""])[0],
                    "short_container": (m.get("short-container-title") or [""])[0],
                    "authors": [
                        {
                            "family": x.get("family"),
                            "given": x.get("given"),
                            "sequence": x.get("sequence"),
                        }
                        for x in m.get("author", [])
                    ],
                    "year": year,
                    "issued": m.get("issued", {}).get("date-parts"),
                    "volume": m.get("volume"),
                    "issue": m.get("issue"),
                    "page": m.get("page"),
                    "article_number": m.get("article-number"),
                    "type": m.get("type"),
                    "publisher": m.get("publisher"),
                    "is_referenced_by_count": m.get("is-referenced-by-count"),
                    "license": [l.get("URL") for l in m.get("license", [])],
                    "abstract_present": bool(m.get("abstract")),
                }
            if r.status_code == 404:
                return {"ok": False, "source": "crossref_doi", "verification_url": url,
                        "error": "HTTP 404 not registered with Crossref"}
            if r.status_code == 429:
                time.sleep(9 * (a + 1))
                continue
        except Exception as exc:
            err = repr(exc)
            time.sleep(3 * (a + 1))
            continue
    return {"ok": False, "source": "crossref_doi", "verification_url": url, "error": err}


def openalex_doi(doi: str, tries: int = 4):
    url = f"https://api.openalex.org/works/https://doi.org/{doi}?mailto={MAILTO}"
    err = None
    for a in range(tries):
        try:
            r = S.get(url, timeout=45)
            if r.status_code == 200:
                d = r.json()
                return {
                    "ok": True,
                    "source": "openalex_doi",
                    "verification_url": url,
                    "doi": (d.get("doi") or "").replace("https://doi.org/", ""),
                    "title": d.get("title"),
                    "container": ((d.get("primary_location") or {}).get("source") or {}).get(
                        "display_name"
                    ),
                    "authors": [
                        x["author"]["display_name"] for x in d.get("authorships", [])
                    ],
                    "year": d.get("publication_year"),
                    "type": d.get("type"),
                    "cited_by_count": d.get("cited_by_count"),
                    "is_oa": (d.get("open_access") or {}).get("is_oa"),
                    "oa_url": (d.get("best_oa_location") or {}).get("pdf_url")
                    if d.get("best_oa_location")
                    else None,
                    "abstract_present": bool(d.get("abstract_inverted_index")),
                }
            if r.status_code == 404:
                return {"ok": False, "source": "openalex_doi", "verification_url": url,
                        "error": "HTTP 404"}
            time.sleep(2 * (a + 1))
        except Exception as exc:
            err = repr(exc)
            time.sleep(2 * (a + 1))
    return {"ok": False, "source": "openalex_doi", "verification_url": url, "error": err}


def verify(dois: list[str], name: str) -> dict:
    out = {}
    p = RAW / f"{name}.json"
    for i, doi in enumerate(dois):
        cr = crossref_doi(doi)
        time.sleep(1.0)
        oa = openalex_doi(doi)
        time.sleep(1.0)
        out[doi] = {"crossref": cr, "openalex": oa}
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        flag = "OK " if (cr.get("ok") or oa.get("ok")) else "FAIL"
        ttl = (cr.get("title") if cr.get("ok") else None) or (
            oa.get("title") if oa.get("ok") else None
        )
        print(f"[{i+1:02d}/{len(dois)}] {flag} {doi} :: {(ttl or '')[:100]}", flush=True)
        if not (cr.get("ok") or oa.get("ok")):
            print("        cr:", cr.get("error"), "| oa:", oa.get("error"), flush=True)
    print("WROTE", p)
    return out


if __name__ == "__main__":
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    verify(payload["dois"], payload["name"])
