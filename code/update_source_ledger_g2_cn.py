"""Append the Chinese-standard sources found by the parallel evidence track (S35-S43).

Append-only, schema-guarded, idempotent. Every locator here was either read
directly by the parent session or verified in the extracted text saved under
sources/extracted/g2_cn/.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT_ROOT / "sources" / "source_ledger.csv"

EXPECTED_HEADER = [
    "source_id",
    "title",
    "doi",
    "url",
    "authority",
    "purpose",
    "access_status_as_of_2026_09_15",
    "critical_limit",
]

NEW_ROWS: list[dict[str, str]] = [
    {
        "source_id": "S35",
        "title": "GB 55034-2022 General code for safety, health and occupational hygiene on building and municipal construction sites (建筑与市政施工现场安全卫生与职业健康通用规范)",
        "doi": "",
        "url": "https://gf.cabr-fire.com/m/article-62620.htm",
        "authority": "Ministry of Housing and Urban-Rural Development of the PRC — 强制性工程建设规范 (full-text mandatory technical code)",
        "purpose": "code-level numeric wind threshold for crane installation/dismantling and a Beaufort-based stop rule for all work at height",
        "access_status_as_of_2026_09_15": (
            "Sec. 3.4.7 read verbatim by the parent session on 2026-09-15 at the CABR mirror; Sec. 3.2.6 "
            "read by the parallel evidence track from a Dongguan Housing Bureau reproduction"
        ),
        "critical_limit": (
            "PRIMARY MANDATORY CODE TEXT, and the strongest source in the whole contract: 3.4.7 states "
            "that above 9.0 m/s at the highest point of the machine, crane installation and dismantling "
            "must stop. It is a mandatory full-text code that prevails over the older JGJ/GB standards. "
            "It governs installation/dismantling, NOT normal lifting, and it states no averaging interval"
        ),
    },
    {
        "source_id": "S36",
        "title": "JGJ 33-2012 Safety technical regulations for the use of construction machinery (建筑机械使用安全技术规程)",
        "doi": "",
        "url": "http://gzhxaq.com/mydata/law/202102/04/16123986714443.htm",
        "authority": "Ministry of Housing and Urban-Rural Development of the PRC (industry standard; Ministry Announcement No. 1364)",
        "purpose": "code-level numeric wind thresholds for crane installation/dismantling, open-air lifting, construction hoists and concrete placing booms, plus the standard's own Beaufort-to-m/s conversion table",
        "access_status_as_of_2026_09_15": (
            "Chinese text read 2026-09-15 via mirror; Sec. 4.1.14, 4.1.15 and 8.10.8 verified verbatim from "
            "the saved extract sources/extracted/g2_cn/jgj33_gzhxaq.txt; Table 4-2 of the tiaowen shuoming "
            "(Beaufort vs m/s) read from the same extract"
        ),
        "critical_limit": (
            "PRIMARY code text. Sec. 4.1.14 (>= 9.0 m/s, 严禁 installation/dismantling), Sec. 4.1.15 "
            "(>= 12.0 m/s, 应停止露天起重吊装作业) and Sec. 8.10.8 (>= 10.8 m/s, concrete placing boom) all "
            "carry the same defect as every other crane source: a magnitude with NO averaging interval. "
            "The Ministry announcement lists 4.1.14 among the 强制性条文 (mandatory clauses)"
        ),
    },
    {
        "source_id": "S37",
        "title": "JGJ 196-2010 Safety technical regulations for installation, use and dismantling of tower cranes in construction (建筑施工塔式起重机安装、使用、拆卸安全技术规程)",
        "doi": "",
        "url": "http://www.zgjjzyjy.org/newss.asp?id=1259",
        "authority": "Ministry of Housing and Urban-Rural Development of the PRC (industry standard)",
        "purpose": "tower-crane-specific wind limits for installation/dismantling and for normal use, anemometer threshold, and the scope ruling that climbing/jacking counts as installation/dismantling",
        "access_status_as_of_2026_09_15": (
            "Sec. 3.4.8, 4.0.9, 4.0.16 and the Sec. 2 scope commentary verified 2026-09-15 across three "
            "independent mirrors (zgjjzyjy.org, gdzjgp.org.cn, ynjj.org.cn); extracts saved under "
            "sources/extracted/g2_cn/"
        ),
        "critical_limit": (
            "PRIMARY code text as reproduced by three independent mirrors. 12 m/s is quoted against "
            "'最大高度处风速' / '最大安装高度处' (wind speed at the maximum height of the machine): a "
            "code-level numeric limit WITH a stated height. No averaging interval is stated"
        ),
    },
    {
        "source_id": "S38",
        "title": "GB 5144-2006 Safety code for tower cranes (塔式起重机安全规程)",
        "doi": "",
        "url": "http://www.zhuoligk.com/Inews/1565.html",
        "authority": "General Administration of Quality Supervision, Inspection and Quarantine of the PRC (national standard)",
        "purpose": "tower-crane installation/dismantling/climbing wind limit, anemometer requirement, and the treatment of the non-working (out-of-service) state",
        "access_status_as_of_2026_09_15": (
            "Sec. 10.2, 6.7, 6.3.4, 6.8 and 3.6a read 2026-09-15 via mirror, with a second mirror "
            "(ynjj.org.cn) and a book118 preview PDF cross-checked by the parallel evidence track"
        ),
        "critical_limit": (
            "PRIMARY code text via mirror. Sec. 10.2 gives 13 m/s for 安装、拆卸、加节或降节 at 最大安装"
            "高度处, which is LOOSER than GB 55034-2022's 9.0 m/s; GB 55034-2022 prevails as the later "
            "full-text mandatory code. The non-working state (Sec. 6.3.4 / 6.8) is QUALITATIVE only — "
            "free slewing plus rail clamping, no number. The widely circulated '800 Pa' non-working wind "
            "pressure was NOT seen in any source read and is NOT reported"
        ),
    },
    {
        "source_id": "S39",
        "title": "GB 6067.1-2010 Safety rules for lifting appliances Part 1: General (起重机械安全规程 第1部分：总则)",
        "doi": "",
        "url": "http://gzhxaq.com/mydata/law/202102/04/16124058093350.htm",
        "authority": "General Administration of Quality Supervision, Inspection and Quarantine of the PRC (national standard)",
        "purpose": "anemometer and wind-alarm requirements, and the code's own statement of what the alarm quantity is",
        "access_status_as_of_2026_09_15": (
            "Sec. 9.6.1.1, 9.6.1.2 and 17.1 k) verified verbatim 2026-09-15 from the saved extract "
            "sources/extracted/g2_cn/gb6067_1_gzhxaq.txt"
        ),
        "critical_limit": (
            "PRIMARY code text, and the most useful single sentence in the whole averaging-interval "
            "search: Sec. 9.6.1.2 requires a wind alarm that DISPLAYS 瞬时风速 (instantaneous wind speed). "
            "The governing accident-prevention quantity in the Chinese chain is therefore instantaneous, "
            "not a 10-minute mean. Sec. 17.1 k) sets no code number and defers to the manufacturer's "
            "maximum working wind speed"
        ),
    },
    {
        "source_id": "S40",
        "title": "JGJ 80-2016 Technical code for safety of high-altitude work in construction (建筑施工高处作业安全技术规范)",
        "doi": "",
        "url": "https://gf.cabr-fire.com/m/article-46638.htm",
        "authority": "Ministry of Housing and Urban-Rural Development of the PRC (industry standard)",
        "purpose": "Beaufort-force-based stop rule for all open-air climbing and suspended work at height, with the code's own Beaufort-to-m/s conversion stated in its commentary",
        "access_status_as_of_2026_09_15": (
            "Sec. 3.0.8 and its tiaowen shuoming read 2026-09-15 at the CABR mirror"
        ),
        "critical_limit": (
            "PRIMARY code text. Sec. 3.0.8 stops open-air climbing and suspended work at height from "
            "Beaufort force 6 upward, and the code's OWN commentary converts that to 'wind speed exceeding "
            "10.8 m/s to 13.8 m/s'. This is the cleanest in-code Beaufort-to-m/s conversion found, and it "
            "is broader in scope than a crane rule: it stops the work at height itself"
        ),
    },
    {
        "source_id": "S41",
        "title": "JGJ/T 104-2011 Specification for winter construction of building engineering (建筑工程冬期施工规程)",
        "doi": "",
        "url": "https://max.book118.com/try_down/425021344210011200.pdf",
        "authority": "Ministry of Housing and Urban-Rural Development of the PRC (industry standard, recommended JGJ/T)",
        "purpose": "the exact wording of the winter-construction entry and exit rule, and the minimum concrete placing temperature in winter",
        "access_status_as_of_2026_09_15": (
            "Sec. 1.0.3 and 6.2.6 read 2026-09-15 from a 53-page text-layer PDF of the standard; "
            "the wording was corroborated against three independent winter-construction explainers"
        ),
        "critical_limit": (
            "PRIMARY code text with a real text layer (unlike the GB/T 28591 scan). Sec. 1.0.3 states the "
            "5-day / 5 degrees C entry AND exit rule verbatim. It is an industry standard (行业标准), not "
            "a full-text mandatory code, so GB 55034-2022 prevails where the two overlap"
        ),
    },
    {
        "source_id": "S42",
        "title": "GB 6067.3-202X Safety rules for lifting appliances Part 3: Tower cranes (DRAFT FOR COMMENT)",
        "doi": "",
        "url": "https://www.samr.gov.cn/ (official SAMR draft-for-comment PDF)",
        "authority": "State Administration for Market Regulation of the PRC — DRAFT",
        "purpose": "a stated averaging interval for a crane anemometer quantity",
        "access_status_as_of_2026_09_15": (
            "Draft PDF fetched 2026-09-15 by the parallel evidence track; Sec. 10.3.3 and 14.1.2.3 read "
            "from sources/extracted/g2_cn/gb6067_3_towercrane_draft.txt"
        ),
        "critical_limit": (
            "DRAFT FOR COMMENT ONLY — NOT IN FORCE, MUST NEVER BE CITED AS A CODE REQUIREMENT. It is "
            "recorded solely because Sec. 10.3.3 specifies that the anemometer measures '3 s时距内的平均"
            "阵风速度' (the mean gust speed over a 3-second interval), which is the ONLY published averaging "
            "window found anywhere in the lifting chain. It documents what regulators were thinking, not "
            "what is binding"
        ),
    },
    {
        "source_id": "S43",
        "title": "GB 50164-2011 Standard for quality control of concrete (混凝土质量控制标准), Sec. 6.4.4",
        "doi": "",
        "url": "",
        "authority": "Ministry of Housing and Urban-Rural Development of the PRC (national standard)",
        "purpose": "winter minimum concrete placing temperature from the concrete quality-control standard",
        "access_status_as_of_2026_09_15": (
            "SECONDARY ONLY. The clause text ('混凝土拌合物入模温度不应低于5℃') was seen only as a quotation "
            "inside a Shandong provincial housing-authority guidance document whose own PDF returned HTTP "
            "500, surfaced through a search index. The free full-text copy at jsjsjc.cn is an image-only "
            "scan with no extractable text layer. The standard itself was NOT read"
        ),
        "critical_limit": (
            "SECONDARY. The quoted 5 degrees C agrees with GB 50666-2011 Sec. 8.1.2 and JGJ/T 104-2011 "
            "Sec. 6.2.6, which WERE read directly, so the value is corroborated; but the clause number "
            "6.4.4 must not be cited as read. Use S28 or S41 for the number"
        ),
    },
]


def main() -> int:
    with LEDGER.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        existing = list(reader)

    if header != EXPECTED_HEADER:
        print("SCHEMA CHANGED - refusing to write")
        return 2

    known = {r["source_id"] for r in existing}
    added = []
    for row in NEW_ROWS:
        if row["source_id"] in known:
            print(f"skip {row['source_id']} (already present)")
            continue
        missing = [c for c in EXPECTED_HEADER if row.get(c, "") == "" and c not in ("doi", "url")]
        if missing:
            print(f"REFUSE {row['source_id']} missing {missing}")
            return 3
        added.append(row)

    combined = existing + added
    with LEDGER.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=EXPECTED_HEADER)
        writer.writeheader()
        writer.writerows(combined)

    with LEDGER.open("r", encoding="utf-8", newline="") as fh:
        check = csv.DictReader(fh)
        check_header = list(check.fieldnames or [])
        rows = list(check)

    ids = [r["source_id"] for r in rows]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    print(f"ledger rows: before={len(existing)} added={len(added)} after={len(rows)}")
    print(f"header preserved exactly: {check_header == EXPECTED_HEADER}")
    print(f"duplicate source_id: {dupes if dupes else 'none'}")
    print(f"next free id: S{max(int(i[1:]) for i in ids) + 1:02d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
