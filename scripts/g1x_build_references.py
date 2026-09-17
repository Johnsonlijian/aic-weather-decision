#!/usr/bin/env python
"""Build sources/raw/g1x/references_append_candidates.json.

21 records in the EXACT schema of manuscript/references.json, built from the verified
Crossref records (never typed by hand), so that appending them is a concatenation plus a
json.load plus an id-collision assert.

Schema kept: id, type, title, author[{family,given}|{literal}], container-title,
issued.date-parts, DOI, URL, volume/page/issue optional.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources/raw/g1x")

# cite_key -> DOI (order follows the matrix)
ORDER = [
    ("augustyn2025app", "10.3390/app15094683"),
    ("li2023jmse", "10.3390/jmse11040803"),
    ("wang2024lnme", "10.1007/978-981-97-1876-4_60"),
    ("hu2023ssci", "10.1016/j.ssci.2022.106044"),
    ("chen2019jlf", "10.1177/1461348419847306"),
    ("jafarpour2023marstruc", "10.1016/j.marstruc.2023.103483"),
    ("wu2021marstruc", "10.1016/j.marstruc.2021.103050"),
    ("wang2016omae", "10.1115/omae2016-54774"),
    ("li2025oceaneng", "10.1016/j.oceaneng.2025.121664"),
    ("mohamed2024wace", "10.1016/j.wace.2024.100718"),
    ("wu2022jmse", "10.3390/jmse10020284"),
    ("schulz2022mwr", "10.1175/mwr-d-21-0150.1"),
    ("coburn2022waf", "10.1175/waf-d-21-0118.1"),
    ("benacek2023waf", "10.1175/waf-d-22-0006.1"),
    ("kolios2023oceaneng", "10.1016/j.oceaneng.2023.115265"),
    ("azcarate2017rene", "10.1016/j.renene.2016.10.064"),
    ("hubbard2021firo", "10.1002/essoar.10505717.1"),
    ("lin2026risa", "10.1111/risa.70328"),
    ("sitthiyot2024mex", "10.1016/j.mex.2024.103010"),
    ("rasp2024wb2", "10.1029/2023MS004019"),
    ("hamill2014bams", "10.1175/bams-d-12-00014.1"),
]

# Crossref type -> CSL type used by references.json
TYPE_MAP = {
    "journal-article": "article-journal",
    "proceedings-article": "paper-conference",
    "posted-content": "article-journal",  # preprint; flagged in notes, not in type
    "book-chapter": "chapter",
}


def load():
    recs = {}
    for name in ("verified_batch1.json", "verified_batch2.json", "verified_extra.json"):
        for r in json.load(open(os.path.join(SRC, name), encoding="utf-8")):
            recs[r["doi"].lower()] = r["crossref"]
    return recs


def build():
    cr = load()
    out, problems = [], []
    for ck, doi in ORDER:
        m = cr.get(doi.lower())
        if not m or not m.get("verified"):
            problems.append(f"{ck}: no verified Crossref record for {doi}")
            continue
        authors = [{"family": a.get("family", ""), "given": a.get("given", "")}
                   for a in (m.get("authors") or []) if a.get("family")]
        if not authors:
            authors = [{"literal": m.get("publisher") or "Unknown"}]
        rec = {
            "id": ck,
            "type": TYPE_MAP.get(m.get("type") or "", "article-journal"),
            "title": m.get("title"),
            "author": authors,
            "container-title": m.get("container") or m.get("short_container") or "",
            "issued": {"date-parts": m.get("issued_date_parts") or [[m.get("year")]]},
            "DOI": m.get("doi"),
            "URL": f"https://doi.org/{m.get('doi')}",
        }
        if m.get("volume"):
            rec["volume"] = m["volume"]
        if m.get("issue"):
            rec["issue"] = m["issue"]
        page = m.get("page") or m.get("article_number")
        if page:
            rec["page"] = page
        out.append(rec)

    # ---- self-checks demanded by the task ----
    existing = json.load(open(os.path.join(ROOT, "manuscript/references.json"), encoding="utf-8"))
    old_ids = {r["id"] for r in existing}
    new_ids = [r["id"] for r in out]
    assert len(new_ids) == len(set(new_ids)), "duplicate ids inside the append list"
    collisions = old_ids & set(new_ids)
    assert not collisions, f"id collision with manuscript/references.json: {collisions}"

    out_path = os.path.join(SRC, "references_append_candidates.json")
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # prove the files parse and that a merge would parse
    merged = existing + json.load(open(out_path, encoding="utf-8"))
    json.loads(json.dumps(merged))
    print(f"WROTE {out_path}")
    print(f"  append records     : {len(out)}")
    print(f"  existing ids       : {len(old_ids)}")
    print(f"  collisions         : {sorted(collisions) or 'NONE'}")
    print(f"  merged list parses : yes ({len(merged)} entries, all ids unique: "
          f"{len({r['id'] for r in merged}) == len(merged)})")
    if problems:
        print("  PROBLEMS:", problems)
    for r in out:
        print(f"    {r['id']:24s} {r['issued']['date-parts'][0][0]} {r['type']:16s} {r['title'][:58]}")


if __name__ == "__main__":
    build()
