"""抓国家级学生资助/征兵政策原文入库。

来源：全国学生资助管理中心（xszz.edu.cn）、全国征兵网（gfbzb.gov.cn）
用法：python tools/ingest_national.py
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
OUT = SRC / "national"
TZ = timezone(timedelta(hours=8))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

PAGES = {
    "zz-jiaoyu": ("https://www.xszz.edu.cn/n40/c7154/content.html", "普通高等教育学生资助政策（全国学生资助管理中心）"),
    "zz-wenda": ("https://www.xszz.edu.cn/n41/n61/index.html", "高等教育资助政策问答（全国学生资助管理中心）"),
    "zz-daikuan-zhinan": ("https://www.xszz.edu.cn/n74/n77/c12733/content.html", "2026 国家助学贷款申请指南（全国学生资助管理中心）"),
    "zz-zhengce": ("https://www.xszz.edu.cn/n39/n54/index.html", "高校学生资助·政策文件（全国学生资助管理中心）"),
    "zb-wang": ("https://www.gfbzb.gov.cn/", "全国征兵网"),
}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        enc = r.headers.get_content_charset()
    for e in (enc, "utf-8", "gb18030"):
        if not e:
            continue
        try:
            return raw.decode(e)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "ignore")


def clean(html: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    h = re.sub(r"</(p|div|tr|li|h\d|table|br)>|<br\s*/?>|<td[^>]*>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&nbsp;", " ").replace("&amp;", "&")
    lines = [re.sub(r"[ \t\u3000\u00a0]+", " ", l).strip() for l in h.split("\n")]
    return "\n".join(l for l in lines if l)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    idx_p = SRC / "national-index.json"
    index = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}

    for slug, (url, title) in PAGES.items():
        try:
            text = clean(get(url))
        except Exception as e:  # noqa: BLE001
            print(f"✗ {slug}: {e}")
            continue
        if len(text) < 400:
            print(f"✗ {slug}: 正文过短 {len(text)}")
            continue
        (OUT / f"{slug}.txt").write_text(text, encoding="utf-8")
        index[slug] = {
            "url": url, "title": title, "chars": len(text),
            "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "kind": "national", "official": True,
        }
        print(f"[收] {len(text):>6} 字  {title}")

    idx_p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n索引 {len(index)} 条")


if __name__ == "__main__":
    main()
