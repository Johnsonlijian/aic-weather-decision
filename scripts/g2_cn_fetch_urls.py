#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fetch public Chinese standard pages, save raw + text under sources/{raw,extracted}/g2_cn.

Usage: python g2_cn_fetch_urls.py <batch.json>
batch.json = [{"label":..., "url":..., "filename":..., "referer":..., "kind":"html|pdf"}]
"""
from __future__ import annotations

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


def decode_body(content: bytes, content_type: str) -> str:
    charset = ""
    m = re.search(r"charset\s*=\s*[\"']?([\w\-]+)", content_type or "", re.I)
    if m:
        charset = m.group(1).lower()
    if not charset:
        head = content[:8000].decode("latin-1", errors="ignore")
        m = re.search(r"charset\s*=\s*[\"']?([\w\-]+)", head, re.I)
        if m:
            charset = m.group(1).lower()
    table = {"gb2312": "gb18030", "gbk": "gb18030", "gb18030": "gb18030", "utf-8": "utf-8", "big5": "big5"}
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
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        html = html.replace(a, b)
    html = re.sub(r"[ \t\u3000]+", " ", html)
    html = re.sub(r"(\r?\n\s*){3,}", "\n\n", html)
    return html.strip()


def main() -> int:
    with open(sys.argv[1], encoding="utf-8") as fh:
        batch = json.load(fh)
    out = []
    for item in batch:
        label = item["label"]
        url = item["url"]
        filename = item["filename"]
        referer = item.get("referer", "")
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
                    subprocess.run([PDFTOTEXT, "-enc", "UTF-8", "-layout", path, txtpath],
                                   capture_output=True, timeout=300)
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
        out.append(rec)
        print(f"[{rec['status']}] {label} bytes={rec['bytes']} pdf={rec['is_pdf']} txt={rec['text_chars']} {rec['error'][:150]}", flush=True)
    with open(os.path.join(TXT, "_download_log.jsonl"), "a", encoding="utf-8") as fh:
        for rec in out:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
