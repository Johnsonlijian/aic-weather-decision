"""G1 novelty-check retrieval library.

Metadata-only retrieval from Crossref and OpenAlex. No API keys, no paid services.
Every returned record keeps the exact request URL so that the verification method
is reproducible and auditable.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

MAILTO = "research@example.org"
UA = f"AiC-G1-Novelty-Audit/1.0 (mailto:{MAILTO})"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw" / "g1"
RAW.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})
TIMEOUT = 40


def _get(url: str, params: dict | None = None, tries: int = 6):
    """GET with backoff. Crossref rate-limits (HTTP 429) aggressively."""
    last = None
    for attempt in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.json(), r.url, None
            last = f"HTTP {r.status_code}"
            if r.status_code == 429:
                time.sleep(9.0 * (attempt + 1))
                continue
        except Exception as exc:  # network flake
            last = repr(exc)
        time.sleep(2.0 * (attempt + 1))
    return None, None, last


def crossref(query: str, rows: int = 5, tag: str = "cr"):
    data, url, err = _get(
        "https://api.crossref.org/works",
        {"query.bibliographic": query, "rows": rows, "mailto": MAILTO},
    )
    if data is None:
        return {"tag": tag, "query": query, "url": url, "error": err, "items": []}
    items = []
    for it in data.get("message", {}).get("items", []):
        year = None
        for k in ("published-print", "published-online", "issued", "created"):
            if it.get(k, {}).get("date-parts", [[None]])[0][0]:
                year = it[k]["date-parts"][0][0]
                break
        items.append(
            {
                "doi": it.get("DOI"),
                "title": (it.get("title") or [""])[0],
                "container": (it.get("container-title") or [""])[0],
                "authors": [
                    f"{a.get('family','')}, {a.get('given','')}".strip(", ")
                    for a in it.get("author", [])
                ],
                "year": year,
                "volume": it.get("volume"),
                "issue": it.get("issue"),
                "page": it.get("page"),
                "article_number": it.get("article-number"),
                "type": it.get("type"),
                "publisher": it.get("publisher"),
                "is_referenced_by_count": it.get("is-referenced-by-count"),
                "url": f"https://doi.org/{it.get('DOI')}" if it.get("DOI") else None,
            }
        )
    return {"tag": tag, "query": query, "url": url, "error": None, "items": items}


def openalex(query: str, per_page: int = 5, tag: str = "oa"):
    data, url, err = _get(
        "https://api.openalex.org/works",
        {"search": query, "per_page": per_page, "mailto": MAILTO},
    )
    if data is None:
        return {"tag": tag, "query": query, "url": url, "error": err, "items": []}
    items = []
    for it in data.get("results", []):
        items.append(
            {
                "doi": (it.get("doi") or "").replace("https://doi.org/", "") or None,
                "title": it.get("title"),
                "container": ((it.get("primary_location") or {}).get("source") or {}).get(
                    "display_name"
                ),
                "authors": [
                    a["author"]["display_name"] for a in it.get("authorships", [])
                ],
                "year": it.get("publication_year"),
                "type": it.get("type"),
                "cited_by_count": it.get("cited_by_count"),
                "url": it.get("id"),
            }
        )
    return {"tag": tag, "query": query, "url": url, "error": None, "items": items}


def run_batch(queries: list[str], rows: int = 5) -> dict:
    out = {"crossref": [], "openalex": []}
    for i, q in enumerate(queries):
        out["crossref"].append(crossref(q, rows=rows, tag=f"cr{i:02d}"))
        time.sleep(0.6)
        out["openalex"].append(openalex(q, per_page=rows, tag=f"oa{i:02d}"))
        time.sleep(0.6)
    return out


if __name__ == "__main__":
    import sys

    qs = json.loads(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else "batch"
    res = run_batch(qs)
    p = RAW / f"{name}.json"
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)
    for blk in ("crossref", "openalex"):
        for entry in res[blk]:
            print(f"[{blk}:{entry['tag']}] {entry['query']!r} err={entry['error']}")
            for it in entry["items"][:5]:
                print(
                    "   -",
                    it.get("year"),
                    "|",
                    (it.get("title") or "")[:110],
                    "|",
                    (it.get("container") or "")[:60],
                    "|",
                    it.get("doi"),
                )
