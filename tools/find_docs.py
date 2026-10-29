"""按标题去官网找文档：用浏览器搜（Bing），拿到 URL 再抓正文入库。

用法：
    python tools/find_docs.py --titles "公费医疗管理办法" "门急诊时间" --out sources/extra
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from crawl_sitemap import body_text  # noqa: E402

CDP = "http://localhost:3456"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
TZ = timezone(timedelta(hours=8))


def cdp_new(url: str) -> str:
    req = urllib.request.Request(f"{CDP}/new", data=url.encode(), method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["targetId"]


def nav(tid: str, url: str) -> None:
    req = urllib.request.Request(f"{CDP}/navigate?target={tid}", data=url.encode(), method="POST")
    urllib.request.urlopen(req, timeout=90).read()
    time.sleep(1.5)


def ev(tid: str, js: str) -> str:
    req = urllib.request.Request(f"{CDP}/eval?target={tid}", data=js.encode("utf-8"), method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=90).read()).get("value", "")


RESULT_JS = (
    '(()=>{const as=[...document.querySelectorAll("a")].filter(a=>'
    'String(a.href).indexOf("cuc.edu.cn")>0 && String(a.href).indexOf("bing.com")<0);'
    'return as.map(a=>a.innerText.replace(/\\s+/g," ").trim()+"\\t"+a.href).join("\\n")})()'
)


def fetch(url: str) -> str:
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--titles", nargs="+", required=True)
    ap.add_argument("--site", default="cuc.edu.cn")
    ap.add_argument("--limit", type=int, default=3, help="每个标题最多抓几篇")
    args = ap.parse_args()

    tid = cdp_new("https://www.bing.com")
    out_dir = ROOT / "sources" / "extra"
    out_dir.mkdir(parents=True, exist_ok=True)
    idx_p = ROOT / "sources" / "extra-index.json"
    index = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}

    for title in args.titles:
        q = urllib.parse.quote(f"site:{args.site} {title}")
        nav(tid, f"https://www.bing.com/search?q={q}")
        rows = ev(tid, RESULT_JS).strip().splitlines()
        picks = []
        for line in rows:
            if "\t" not in line:
                continue
            t, u = line.split("\t", 1)
            if any(ch in u for ch in (".pdf", ".doc", ".docx")):
                continue
            picks.append((t[:60], u))
        picks = picks[: args.limit]
        print(f"\n【{title}】候选 {len(picks)}")
        for t, u in picks:
            slug = hashlib.md5(u.encode()).hexdigest()[:10]
            if slug in index:
                print(f"  已入库 {u[:60]}")
                continue
            try:
                html = fetch(u)
            except Exception as e:  # noqa: BLE001
                print(f"  ✗ {e}")
                continue
            text = body_text(html)
            if len(text) < 300:
                print(f"  ✗ 正文过短 {u[:50]}")
                continue
            (out_dir / f"{slug}.txt").write_text(text, encoding="utf-8")
            index[slug] = {
                "url": u, "title": f"{title}（{'、'.join(sorted(set(re.findall(r'[a-z]+\.cuc', u))))}）",
                "chars": len(text),
                "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
                "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
                "kind": "extra",
            }
            print(f"  [收] {len(text):>5} 字  {t[:40]}")

    idx_p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n索引 {len(index)} 条")


if __name__ == "__main__":
    main()
