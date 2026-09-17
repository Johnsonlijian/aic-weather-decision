"""G1 title-based verification: confirm exact bibliographic records by literal title
fragments, then re-resolve the winning DOI through Crossref and OpenAlex.

Used for classics whose DOI cannot be guessed (pre-1990s AMS, JRSS, PNAS, NC).
Writes sources/raw/g1/titlecheck_<name>.json with the search URL, the chosen hit and
the DOI-level confirmation, so the verification method is fully auditable.
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


def title_search(title: str, author: str | None = None, rows: int = 3):
    """Crossref bibliographic query; the query is a literal title, not a topic."""
    q = f"{title} {author}" if author else title
    url = "https://api.crossref.org/works"
    params = {"query.bibliographic": q, "rows": rows, "mailto": MAILTO}
    err = None
    for a in range(5):
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
                            "volume": it.get("volume"),
                            "issue": it.get("issue"),
                            "page": it.get("page"),
                            "type": it.get("type"),
                            "publisher": it.get("publisher"),
                            "cited_by": it.get("is-referenced-by-count"),
                            "authors": [
                                f"{x.get('family','')}, {x.get('given','')}".strip(", ")
                                for x in it.get("author", [])
                            ],
                        }
                    )
                return {"query": q, "verification_url": r.url, "error": None, "items": items}
            err = f"HTTP {r.status_code}"
            if r.status_code == 429:
                time.sleep(15 * (a + 1))
                continue
        except Exception as exc:
            err = repr(exc)
        time.sleep(4 * (a + 1))
    return {"query": q, "verification_url": url, "error": err, "items": []}


def main(spec_path: str) -> None:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    out = {}
    for i, tgt in enumerate(spec["targets"]):
        res = title_search(tgt["title"], tgt.get("author"), rows=tgt.get("rows", 3))
        out[tgt["key"]] = {"target": tgt, "search": res}
        print(f"[{i+1:02d}/{len(spec['targets'])}] {tgt['key']} :: {tgt['title'][:70]!r} "
              f"err={res['error']}", flush=True)
        for it in res["items"]:
            print(f"    - {it['year']} | {(it['title'] or '')[:110]} | "
                  f"{(it['container'] or '')[:50]} | {it['doi']} | "
                  f"{'; '.join(it['authors'][:3])}", flush=True)
        time.sleep(3.0)
    p = RAW / f"titlecheck_{spec['name']}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)


if __name__ == "__main__":
    main(sys.argv[1])
