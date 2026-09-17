#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download public Chinese standard documents into sources/raw/g2_cn and extract text.

Usage: python g2_cn_download.py <candidate-name> [<candidate-name> ...]
       python g2_cn_download.py --all
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import time

import requests
import urllib3

urllib3.disable_warnings()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "sources", "raw", "g2_cn")
TXT = os.path.join(ROOT, "sources", "extracted", "g2_cn")
os.makedirs(RAW, exist_ok=True)
os.makedirs(TXT, exist_ok=True)

PDFTOTEXT = r"C:\Users\renli\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdftotext.exe"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# label -> (url, filename, referer)
CANDIDATES: dict[str, tuple[str, str, str]] = {
    "jgj33-zhulouren-65713": ("https://www.zhulouren.com/gb65713.html", "jgj33_zhulouren65713.html", ""),
    "gb50164-sdjtu-preview": (
        "http://wljxpt.sdjtu.edu.cn/meol/common/script/preview/download_preview.jsp"
        "?fileid=2564942&resid=430157&lid=21554",
        "gb50164_sdjtu_preview.bin",
        "http://wljxpt.sdjtu.edu.cn/",
    ),
    "jgj104-waizi": ("https://www.waizi.org.cn/bz/126923.html", "jgj104_waizi.html", ""),
    "jgj104-biaozhuns": (
        "https://www.biaozhuns.com/archives/20150926/show-139575-65-1.html",
        "jgj104_biaozhuns.html",
        "",
    ),
    "gb50164-zhulouren": ("https://www.zhulouren.com/gb194185.html", "gb50164_zhulouren.html", ""),
    "jgj33-zhulouren-70058": ("https://www.zhulouren.com/gb70058.html", "jgj33_zhulouren70058.html", ""),
    "gb50666-10.2-jianbiaoku": (
        "http://www.jianbiaoku.com/webarbs/book/10316/296564.shtml",
        "gb50666_jianbiaoku_10_2.html",
        "",
    ),
    "gb50666-cabr-10.2": ("https://gf.cabr-fire.com/m/article-17800.htm", "gb50666_cabr_10_2.html", ""),
    "gb50666-guifanku": ("https://www.guifanku.com/335213.html", "gb50666_guifanku.html", ""),
    "sd-zjt-gb50164-ref": (
        "http://zjt.shandong.gov.cn/module/download/downfile.jsp?classid=0"
        "&filename=7d695dcdb92b46648208ba1bf255d694.pdf",
        "sd_zjt_concrete_guide.pdf",
        "http://zjt.shandong.gov.cn/",
    ),
    "jgj196-chinabuilding-probation": (
        "https://ebook.chinabuilding.com.cn/zbooklib/bookpdf/probation?SiteID=1&bookID=56218",
        "jgj196_chinabuilding_probation.pdf",
        "https://ebook.chinabuilding.com.cn/",
    ),
    "gbt28591-sac-openstd": (
        "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=E1B1A1B1B1B1B1B1B1B1B1B1B1B1B1B1",
        "openstd_probe.html",
        "",
    ),
}


def decode_body(content: bytes, content_type: str) -> str:
    charset = ""
    m = re.search(r"charset\s*=\s*[\"']?([\w\-]+)", content_type or "", re.I)
    if m:
        charset = m.group(1).lower()
    if not charset:
        head = content[:6000].decode("latin-1", errors="ignore")
        m = re.search(r"charset\s*=\s*[\"']?([\w\-]+)", head, re.I)
        if m:
            charset = m.group(1).lower()
    table = {
        "gb2312": "gb18030",
        "gbk": "gb18030",
        "gb18030": "gb18030",
        "utf-8": "utf-8",
        "utf8": "utf-8",
        "big5": "big5",
    }
    if charset in table:
        try:
            return content.decode(table[charset], errors="replace")
        except Exception:
            pass
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("gb18030", errors="replace")


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?</style>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</(p|div|tr|li|h[1-6]|table|td|th)>", "\n", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    for a, b in (
        ("&nbsp;", " "),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&#39;", "'"),
    ):
        html = html.replace(a, b)
    html = re.sub(r"[ \t\u3000]+", " ", html)
    html = re.sub(r"(\r?\n\s*){3,}", "\n\n", html)
    return html.strip()


def fetch(label: str) -> dict:
    url, filename, referer = CANDIDATES[label]
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    rec = {
        "label": label,
        "url": url,
        "referer": referer,
        "filename": filename,
        "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": None,
        "content_type": "",
        "final_url": "",
        "bytes": 0,
        "is_pdf": False,
        "text_chars": 0,
        "error": "",
    }
    path = os.path.join(RAW, filename)
    txtpath = os.path.join(TXT, os.path.splitext(filename)[0] + ".txt")
    try:
        r = requests.get(url, headers=headers, timeout=90, allow_redirects=True, verify=False)
        rec["status"] = r.status_code
        rec["content_type"] = r.headers.get("Content-Type", "")
        rec["final_url"] = r.url
        content = r.content
        rec["bytes"] = len(content)
        with open(path, "wb") as fh:
            fh.write(content)
        if content[:4] == b"%PDF":
            rec["is_pdf"] = True
            try:
                subprocess.run(
                    [PDFTOTEXT, "-enc", "UTF-8", "-layout", path, txtpath],
                    capture_output=True,
                    timeout=300,
                )
            except Exception as exc:  # noqa: BLE001
                rec["error"] = f"pdftotext: {exc}"
            if os.path.exists(txtpath):
                rec["text_chars"] = os.path.getsize(txtpath)
        else:
            text = html_to_text(decode_body(content, rec["content_type"]))
            with open(txtpath, "w", encoding="utf-8") as fh:
                fh.write(text)
            rec["text_chars"] = len(text)
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def main() -> int:
    args = sys.argv[1:]
    labels = list(CANDIDATES) if (not args or args[0] == "--all") else args
    out = []
    for label in labels:
        if label not in CANDIDATES:
            print(f"SKIP unknown label {label}", flush=True)
            continue
        rec = fetch(label)
        out.append(rec)
        print(
            f"[{rec['status']}] {label} bytes={rec['bytes']} pdf={rec['is_pdf']} "
            f"txt={rec['text_chars']} {rec['error'][:180]}",
            flush=True,
        )
    logpath = os.path.join(TXT, "_download_log.jsonl")
    with open(logpath, "a", encoding="utf-8") as fh:
        for rec in out:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
