"""把学信网（CHSI）页面转成干净文本入库，供条目引用原文。

用法：python tools/ingest_chsi.py
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
OUT = SRC / "chsi"
TZ = timezone(timedelta(hours=8))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

PAGES = {
    "chsi-benren": ("https://www.chsi.com.cn/xlcx/brcxff.jsp", "查询本人学籍学历学位信息方法（学信网）"),
    "chsi-yanzheng": ("https://www.chsi.com.cn/xlcx/bgcx.jsp", "在线验证报告（学信网）"),
    "chsi-xuewei": ("https://www.chsi.com.cn/xwcx/index.jsp", "学位查询（学信网）"),
    "chsi-fanwei": ("https://www.chsi.com.cn/help/cxfw.jsp", "学历查询范围（学信网）"),
    "chsi-xueli": ("https://www.chsi.com.cn/xlcx/index.jsp", "学历查询（学信网）"),
}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        enc = r.headers.get_content_charset()
    return raw.decode(enc or "utf-8", "ignore")


def clean(html: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    h = re.sub(r"</(p|div|tr|li|h\d|table|br)>|<br\s*/?>|<td[^>]*>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&nbsp;", " ").replace("&amp;", "&")
    lines = [re.sub(r"[ \t\u3000\u00a0]+", " ", l).strip() for l in h.split("\n")]
    return "\n".join(l for l in lines if l)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    idx_p = SRC / "chsi-index.json"
    index = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}

    for slug, (url, title) in PAGES.items():
        try:
            text = clean(get(url))
        except Exception as e:  # noqa: BLE001
            print(f"✗ {slug}: {e}")
            continue
        if len(text) < 200:
            print(f"✗ {slug}: 正文过短 {len(text)}")
            continue
        (OUT / f"{slug}.txt").write_text(text, encoding="utf-8")
        index[slug] = {
            "url": url, "title": title, "chars": len(text),
            "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "kind": "chsi", "official": True,
        }
        print(f"[收] {len(text):>5} 字  {title}")

    idx_p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n索引 {len(index)} 条")


if __name__ == "__main__":
    main()
