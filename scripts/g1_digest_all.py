"""Print authors/venue/pages for a set of DOIs across all g1 verify_*.json files."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "sources" / "raw" / "g1"

WANT = [
    "10.1016/j.oceaneng.2023.115896", "10.1016/j.oceaneng.2024.117027",
    "10.1016/j.marstruc.2026.104144", "10.1115/omae2019-96137",
    "10.1016/j.ejor.2016.08.057", "10.3390/jmse14020223",
    "10.1049/rpg2.12689", "10.3390/en11092190", "10.1016/j.ifacol.2021.08.037",
    "10.1109/wsc.2016.7822324", "10.1088/1742-6596/753/9/092016",
    "10.1061/(asce)co.1943-7862.0000258", "10.1139/cjce-2013-0087",
    "10.1061/(asce)0733-9364(1993)119:2(226)",
    "10.1061/(asce)0733-9364(1985)111:4(325)",
    "10.1016/j.eswa.2022.119188", "10.3390/buildings10080134",
    "10.3390/su13052861", "10.1016/j.autcon.2022.104341",
    "10.1017/s1350482702003043", "10.1002/met.167", "10.1002/met.44",
    "10.1002/qj.49712656313", "10.1002/qj.4674", "10.5194/hess-11-725-2007",
    "10.1175/1520-0493(1976)104<1058:dmmitc>2.0.co;2",
    "10.1175/1520-0493(1977)105<0803:tvocca>2.0.co;2",
    "10.1175/1520-0493(1985)113<0362:dmatvo>2.0.co;2",
    "10.1175/1520-0493(1990)118<0939:odmatv>2.0.co;2",
    "10.1175/1520-0493(1985)113<0801:rdmatv>2.0.co;2",
    "10.1175/1520-0493(2001)129<2329:aapevo>2.0.co;2",
    "10.1175/mwr3031.1", "10.1017/s1350482701002092",
    "10.1017/cbo9780511608278", "10.1017/cbo9780511608278.003",
    "10.1017/cbo9780511608278.005", "10.1017/cbo9780511608278.007",
    "10.1175/1520-0477-33.6.223",
    "10.1175/1520-0493(1950)078<0001:vofeit>2.0.co;2",
    "10.1175/1520-0434(1993)008<0281:wiagfa>2.0.co;2",
    "10.1111/j.1467-9868.2007.00587.x", "10.1175/mwr2904.1",
    "10.1175/1520-0477(2002)083<0073:tevoeb>2.3.co;2",
    "10.1002/met.1392",
    "10.1287/mnsc.2020.3922", "10.1287/mnsc.2018.3253", "10.1287/opre.2018.1757",
    "10.1002/qj.3803", "10.3390/modelling7040137",
    "10.3390/jmse14020223",
]


def fmt_authors(auths) -> str:
    out = []
    for a in auths or []:
        if isinstance(a, dict):
            fam, giv = a.get("family"), a.get("given") or ""
            if fam:
                parts = [p for p in giv.replace(".", " ").replace("-", " ").split() if p]
                out.append(f"{fam}, " + " ".join(f"{p[0]}." for p in parts))
            else:
                out.append(str(a))
        else:
            out.append(str(a))
    return "; ".join(out)


def main() -> None:
    merged: dict[str, dict] = {}
    for p in sorted(RAW.glob("verify_*.json")):
        for doi, rec in json.loads(p.read_text(encoding="utf-8")).items():
            if doi not in merged:
                merged[doi] = rec
    print(f"# merged verified records: {len(merged)}\n")
    missing = []
    for doi in WANT:
        rec = merged.get(doi)
        if not rec:
            missing.append(doi)
            continue
        cr, oa = rec.get("crossref", {}), rec.get("openalex", {})
        if not (cr.get("ok") or oa.get("ok")):
            missing.append(doi)
            continue
        s = cr if cr.get("ok") else oa
        cite = (f"{s.get('year')}; {s.get('volume') or ''}"
                f"{('(' + str(s.get('issue')) + ')') if s.get('issue') else ''}"
                f":{s.get('page') or s.get('article_number') or ''}")
        print(f"{doi}\n  T: {s.get('title')}\n  A: {fmt_authors(s.get('authors'))}"
              f"\n  V: {s.get('container')} | {cite}\n")
    if missing:
        print("NOT FOUND OR UNVERIFIED:", missing)


if __name__ == "__main__":
    main()
