"""Append-only update of sources/source_ledger.csv for the G2 operation-contract round.

Reads the existing ledger, keeps its schema exactly, appends rows S23-S34, and
re-parses the result with the csv module to prove it still loads. Idempotent: if
the ID already exists the row is skipped, so re-running cannot duplicate rows.
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
        "source_id": "S23",
        "title": "Yongmao STT293 Tower Crane Operation & Service Manual (en-version 2.0)",
        "doi": "",
        "url": "https://cranemanuals.com/wp-content/uploads/2024/03/Yongmao-STT293-Tower-Crane-Operating-Service-Manual.pdf",
        "authority": "crane manufacturer (third-party manual mirror)",
        "purpose": "manufacturer in-service and out-of-service wind limits; crane-function wind limits; anemoscope alarm settings; weathervane securing procedure",
        "access_status_as_of_2026_09_15": (
            "full 157-page PDF fetched 2026-09-15 and text-extracted; Ch. 2.1, Ch. 3.4, "
            "Sec. 3.4.1(h), Sec. 3.4.3, Sec. 2.4, Sec. 10.7.3.2 and Sec. 10.7.4.1 read directly"
        ),
        "critical_limit": (
            "PRIMARY manufacturer text. It gives 20 m/s in-service and 50 m/s out-of-service but "
            "never states the averaging interval or the anemometer height; it is one model, not all cranes"
        ),
    },
    {
        "source_id": "S24",
        "title": "CPA TIN 101 The Effect of Wind on Mobile Cranes In-service",
        "doi": "",
        "url": "http://www.ritchiestraining.co.uk/wp-content/uploads/2016/01/TheEffectofWindonMobileCranesIn-service.pdf",
        "authority": "Construction Plant-hire Association, Crane Interest Group (UK trade body)",
        "purpose": "UK industry-recommended in-service wind speed for tower cranes; mobile-crane duty-chart wind limits; forecast height correction; out-of-service procedure",
        "access_status_as_of_2026_09_15": (
            "full 2-page PDF fetched 2026-09-15 and text-extracted; Issue A dated 04.12.09; both pages read"
        ),
        "critical_limit": (
            "PRIMARY trade-body note, not a standard and not law. The 16.5 m/s figure is an industry "
            "recommendation produced with HSE involvement; no averaging interval is given"
        ),
    },
    {
        "source_id": "S25",
        "title": "DGUV Vorschrift 52 Krane, Section 30 Pflichten des Kranfuehrers",
        "doi": "",
        "url": "https://www.bgbau-medien.de/handlungshilfen_gb/daten/dguv/52/30.htm",
        "authority": "Deutsche Gesetzliche Unfallversicherung (German statutory accident insurance)",
        "purpose": "national regulation showing that the numeric wind limit is delegated to the crane manufacturer; securing procedure for storm state",
        "access_status_as_of_2026_09_15": (
            "full regulation text of Section 30 plus its Durchfuehrungsanweisungen fetched 2026-09-15 and read"
        ),
        "critical_limit": (
            "PRIMARY regulation text with NO numeric threshold by design: Sec. 30(6)1 points to the "
            "manufacturer's Betriebsanleitung. Must never be cited as a numeric limit"
        ),
    },
    {
        "source_id": "S26",
        "title": "29 CFR Part 1926 Subpart CC, sections 1926.1417 and 1926.1435 (US OSHA)",
        "doi": "",
        "url": "https://www.law.cornell.edu/cfr/text/29/1926.1417",
        "authority": "US Occupational Safety and Health Administration (text via Cornell LII e-CFR mirror)",
        "purpose": "US federal rule: competent-person wind duty, manufacturer/qualified-person wind limit for tower-crane erecting-climbing-dismantling, mandated wind speed indicator location, storm-warning securing duty",
        "access_status_as_of_2026_09_15": (
            "current e-CFR text of both sections fetched 2026-09-15 and read in full; eCFR direct fetch "
            "was blocked by an unblock.federalregister.gov redirect, so the Cornell LII e-CFR mirror was used"
        ),
        "critical_limit": (
            "PRIMARY regulation text. It contains NO numeric wind threshold; do not attribute a number "
            "to OSHA. The Cornell mirror is an e-CFR copy, not the primary federalregister.gov rendering"
        ),
    },
    {
        "source_id": "S27",
        "title": "VDOT IIM-S&B-91 General Requirements for the Usage, Design and Specification of Post-Tensioned Bridge Superstructures, 13 December 2016",
        "doi": "",
        "url": "https://snowplowing.vdot.virginia.gov/media/vdotvirginiagov/doing-business/technical-guidance-and-support/technical-guidance-documents/structure-and-bridge/migrated-acc/iim/SBIIM91.pdf",
        "authority": "Virginia Department of Transportation, Structure and Bridge Division (owner specification)",
        "purpose": "the fully documented non-preemptive material operation: segmental epoxy jointing substrate temperature window, open time, 70 percent rule, 20-minute application limit, contact pressure, 24-hour post-join hold and 24-hour recovery",
        "access_status_as_of_2026_09_15": (
            "full 204-page PDF fetched 2026-09-15; text extracted to sources/extracted/vdot_iim_sb91.txt; "
            "Sec. 453-4.4, 453-4.5.2, 453-5.1 to 453-5.8 and Sec. 10.2/section 452 cure clauses read directly"
        ),
        "critical_limit": (
            "PRIMARY owner specification text. It is a US state DOT contractual specification that "
            "incorporates FDOT Specifications 452 and 453; it is not a national or international standard. "
            "The 42-minute usable window is our arithmetic on the published 60-minute open time and 70 percent rule"
        ),
    },
    {
        "source_id": "S28",
        "title": "GB 50666-2011 Code for construction of concrete structures (混凝土结构工程施工规范)",
        "doi": "",
        "url": "https://gf.cabr-fire.com/m/article-17761.htm",
        "authority": "Ministry of Housing and Urban-Rural Development of the People's Republic of China (national code, with tiaowen shuoming commentary)",
        "purpose": "concrete placing and discharge temperature limits, winter and hot-weather regime triggers, rain-period placing rules, curing and formwork-striking temperature criteria",
        "access_status_as_of_2026_09_15": (
            "Chinese normative text plus commentary read 2026-09-15 for Sec. 8.1.2, 10.1.1, 10.1.2, 10.2.7, "
            "10.2.10, 10.2.12, 10.2.14, 10.2.15, 10.2.16, 10.2.18, 10.3.5, 10.3.6 and 10.4.4 to 10.4.10; "
            "Table 10.2.5 and Table 10.3.3 are images and were NOT read"
        ),
        "critical_limit": (
            "PRIMARY national code text. The mirror is a third-party reproduction; the 8.1.2 clause text "
            "and its commentary were seen, but the two numeric heating tables were not. The rain gate is "
            "categorical (小雨/中雨/大雨/暴雨) with NO mm/h boundary in this code"
        ),
    },
    {
        "source_id": "S29",
        "title": "WMO Guide to Meteorological Instruments and Methods of Observation (CIMO Guide), Part I Chapter 5 Measurement of Surface Wind",
        "doi": "",
        "url": "https://old.wmo.int/extranet/pages/prog/www/IMOP/publications/CIMO-Guide/Prelim_2018_ed/8_I_5_en_MR_tc.pdf",
        "authority": "World Meteorological Organization",
        "purpose": "definition of the averaged wind quantity, the 10-minute averaging interval, the 3-second peak gust, and the gust-duration concept",
        "access_status_as_of_2026_09_15": (
            "full 19-page PDF fetched 2026-09-15 and text-extracted; Sec. 5.1.1, 5.1.2, 5.1.3, 5.8.1 and 5.8.2 read"
        ),
        "critical_limit": (
            "PRIMARY standard text. It documents that a 10-minute average is the synoptic reporting "
            "quantity and that the 3-second peak gust is a separate variable; it does NOT authorise using "
            "a model instantaneous gust field as a 10-minute mean"
        ),
    },
    {
        "source_id": "S30",
        "title": "Met Office Beaufort wind force scale",
        "doi": "",
        "url": "https://weather.metoffice.gov.uk/guides/coast-and-sea/beaufort-scale",
        "authority": "UK Met Office (national meteorological service)",
        "purpose": "documented m/s boundaries for Beaufort forces so that a Beaufort-based national code threshold can be converted without invention",
        "access_status_as_of_2026_09_15": (
            "full table fetched 2026-09-15; the Mean Wind Speed column and the Limits of wind speed column both read"
        ),
        "critical_limit": (
            "PRIMARY meteorological table. Force 6 (strong breeze) is mean 12 m/s with limits 11-14 m/s. "
            "The table is a marine observational scale; converting a code's 六级风 clause into a number is "
            "still our mapping, not the code's own wording"
        ),
    },
    {
        "source_id": "S31",
        "title": "GB/T 28591-2012 Wind force scale (风力等级)",
        "doi": "",
        "url": "http://cmastd.cmatc.cn/u/cms/www/201602/01152025b4yb.pdf",
        "authority": "China Meteorological Administration standards channel (national standard reproduction)",
        "purpose": "the Chinese national wind-force scale that Chinese construction codes rely on when they say 六级风",
        "access_status_as_of_2026_09_15": (
            "1,887,481-byte PDF fetched 2026-09-15 (HTTP 200) but all 7 pages extract as empty text; the "
            "document is image-only and NO numeric value was read from it"
        ),
        "critical_limit": (
            "NOT OBTAINED IN READABLE FORM. The file was retrieved but is unusable for citation of any "
            "number. The Beaufort scale in S30 is used instead, and any 六级风 to m/s mapping must be "
            "labelled as our conversion"
        ),
    },
    {
        "source_id": "S32",
        "title": "CIM 5710-2016 Tower crane operation and maintenance safety regulation (English summary)",
        "doi": "",
        "url": "https://www.irc.gov.mo/storage/app/media/uploaded-files/CIM%205710-2016.pdf",
        "authority": "Macao SAR Government, Infrastructure and Utilities",
        "purpose": "candidate supplementary regional tower-crane regulation",
        "access_status_as_of_2026_09_15": (
            "URL identified from a web index only; the document was NEVER fetched in this session and no "
            "content was read"
        ),
        "critical_limit": (
            "NOT ACCESSED. Useful only as a lead. No claim, number or clause may be attributed to this "
            "source until the document is actually retrieved and read"
        ),
    },
    {
        "source_id": "S33",
        "title": "ASME B30.5 Mobile and Locomotive Cranes",
        "doi": "",
        "url": "",
        "authority": "American Society of Mechanical Engineers (consensus standard)",
        "purpose": "US consensus-standard wind duty for mobile cranes",
        "access_status_as_of_2026_09_15": (
            "SECONDARY ONLY. Two independent secondary descriptions were seen on 2026-09-15 stating that "
            "B30.5 requires crews to monitor wind and to lower, retract and secure the boom when the "
            "manufacturer's or site-specific limit is met, and that B30.5 is conservative on wind. The "
            "standard itself was NOT obtained"
        ),
        "critical_limit": (
            "SECONDARY. The secondary sources are a Colorado crane-school guidance PDF "
            "(https://mscss.us/wp-content/uploads/2025/12/Cranes-and-Wind-Speed.pdf) and the ASCC safety "
            "article cited as S34. Do not cite a B30.5 clause number or a B30.5 numeric limit"
        ),
    },
    {
        "source_id": "S34",
        "title": "ASCC Industry Knowledge in Action: Wind-Speed Shutdowns for Cranes and Concrete Boom Pumps",
        "doi": "",
        "url": "https://ascconline.org/Home/News/articleType/ArticleView/articleId/568/categoryId",
        "authority": "American Society of Concrete Contractors (industry association)",
        "purpose": "evidence that the widely repeated 20-22 mph crane wind figure is an industry practice benchmark rather than a code requirement, and that manufacturer manuals govern",
        "access_status_as_of_2026_09_15": (
            "full web page fetched 2026-09-15 (HTTP 200, posted 14 November 2025); body text read"
        ),
        "critical_limit": (
            "SECONDARY / industry commentary, not a standard. It explicitly states there is no universal "
            "rule and that manufacturer recommendations govern. It gives no averaging interval"
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
        print("  existing:", header)
        print("  expected:", EXPECTED_HEADER)
        return 2

    known = {r["source_id"] for r in existing}
    added: list[dict[str, str]] = []
    for row in NEW_ROWS:
        if row["source_id"] in known:
            print(f"skip {row['source_id']} (already present)")
            continue
        missing = [c for c in EXPECTED_HEADER if row.get(c, "") == "" and c != "doi" and c != "url"]
        if missing:
            print(f"REFUSE {row['source_id']} missing {missing}")
            return 3
        added.append(row)

    combined = existing + added
    with LEDGER.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=EXPECTED_HEADER)
        writer.writeheader()
        writer.writerows(combined)

    # Verify by re-parsing from disk with the csv module.
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
