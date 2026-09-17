"""G1 discovery sweep via OpenAlex + Crossref (interleaved with generous pacing).

Design rationale: the Crossref /works?query endpoint rate-limits this client heavily
(HTTP 429), whereas OpenAlex search is fast and returns DOI + venue + year + cited-by.
Crossref is therefore used mainly as the authoritative DOI resolver (see
g1_verify_dois.py), and its query endpoint only with long pauses.

Outputs one JSON per batch plus a flat candidate list keyed by normalised DOI.
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


def openalex_search(query: str, per_page: int = 8, tries: int = 4):
    url = "https://api.openalex.org/works"
    params = {"search": query, "per_page": per_page, "mailto": MAILTO}
    err = None
    for a in range(tries):
        try:
            r = S.get(url, params=params, timeout=45)
            if r.status_code == 200:
                items = []
                for it in r.json().get("results", []):
                    items.append(
                        {
                            "doi": (it.get("doi") or "").replace("https://doi.org/", "") or None,
                            "title": it.get("title"),
                            "container": (
                                (it.get("primary_location") or {}).get("source") or {}
                            ).get("display_name"),
                            "year": it.get("publication_year"),
                            "type": it.get("type"),
                            "cited_by_count": it.get("cited_by_count"),
                            "authors": [
                                x["author"]["display_name"] for x in it.get("authorships", [])
                            ],
                            "openalex_id": it.get("id"),
                            "is_oa": (it.get("open_access") or {}).get("is_oa"),
                            "has_abstract": bool(it.get("abstract_inverted_index")),
                        }
                    )
                return {"query": query, "error": None,
                        "verification_url": r.url, "items": items}
            time.sleep(2 * (a + 1))
        except Exception as exc:
            err = repr(exc)
            time.sleep(2 * (a + 1))
    return {"query": query, "error": err, "verification_url": url, "items": []}


def crossref_search(query: str, rows: int = 8, tries: int = 3):
    url = "https://api.crossref.org/works"
    params = {"query.bibliographic": query, "rows": rows, "mailto": MAILTO}
    err = None
    for a in range(tries):
        try:
            r = S.get(url, params=params, timeout=45)
            if r.status_code == 200:
                items = []
                for it in r.json()["message"].get("items", []):
                    year = None
                    for k in ("published-print", "published-online", "issued", "created"):
                        dp = it.get(k, {}).get("date-parts", [[None]])
                        if dp and dp[0] and dp[0][0]:
                            year = dp[0][0]
                            break
                    items.append(
                        {
                            "doi": it.get("DOI"),
                            "title": (it.get("title") or [""])[0],
                            "container": (it.get("container-title") or [""])[0],
                            "year": year,
                            "type": it.get("type"),
                            "cited_by_count": it.get("is-referenced-by-count"),
                            "authors": [
                                f"{x.get('family','')}, {x.get('given','')}".strip(", ")
                                for x in it.get("author", [])
                            ],
                            "verification_url": f"https://doi.org/{it.get('DOI')}",
                        }
                    )
                return {"query": query, "error": None, "verification_url": r.url,
                        "items": items}
            err = f"HTTP {r.status_code}"
            if r.status_code == 429:
                time.sleep(20 * (a + 1))
                continue
        except Exception as exc:
            err = repr(exc)
        time.sleep(4 * (a + 1))
    return {"query": query, "error": err, "verification_url": url, "items": []}


def run(queries: list[str], name: str, per_page: int = 8, do_crossref: bool = True):
    res = {"openalex": [], "crossref": []}
    flat: dict[str, dict] = {}
    for i, q in enumerate(queries):
        oa = openalex_search(q, per_page=per_page)
        res["openalex"].append(oa)
        for it in oa["items"]:
            if it["doi"]:
                flat.setdefault(it["doi"].lower(), it)
        print(f"[OA {i+1:02d}/{len(queries)}] {q!r} err={oa['error']} n={len(oa['items'])}")
        for it in oa["items"]:
            print(f"    - {it['year']} | {(it['title'] or '')[:120]} | "
                  f"{(it['container'] or '')[:50]} | {it['doi']} | cit={it['cited_by_count']}")
        time.sleep(0.5)
        if do_crossref:
            cr = crossref_search(q, rows=per_page)
            res["crossref"].append(cr)
            for it in cr["items"]:
                if it["doi"]:
                    flat.setdefault(it["doi"].lower(), it)
            print(f"[CR {i+1:02d}/{len(queries)}] {q!r} err={cr['error']} n={len(cr['items'])}")
            for it in cr["items"]:
                print(f"    * {it['year']} | {(it['title'] or '')[:120]} | "
                      f"{(it['container'] or '')[:50]} | {it['doi']}")
            time.sleep(2.0)
    (RAW / f"{name}.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    (RAW / f"{name}_flat.json").write_text(
        json.dumps(flat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"WROTE {RAW / (name + '.json')}  ({len(flat)} unique DOIs)")
    return res, flat


if __name__ == "__main__":
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    run(spec["queries"], spec["name"], per_page=spec.get("per_page", 8),
        do_crossref=spec.get("crossref", True))
