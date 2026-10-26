"""用 CDP（登录态浏览器）抓 JS 站点：栏目列表靠浏览器渲染，正文用 curl 拿。

适用于静态 curl 拿不到文章链接的站点（学工部、图书馆这类南大之星 / SPA）。

用法：
    python tools/crawl_cdp.py --columns 2760,2761 --host xsc.cuc.edu.cn
    python tools/crawl_cdp.py --host xsc.cuc.edu.cn --columns 2758,2752,2753,2760,2761,2762,2763,2765
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
from crawl_sitemap import body_text, pub_date  # 复用正文与日期提取

CDP = "http://localhost:3456"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
TZ = timezone(timedelta(hours=8))
OUT = ROOT / "sources" / "cdp"


def cdp_new(url: str) -> str:
    req = urllib.request.Request(f"{CDP}/new", data=url.encode(), method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["targetId"]


def cdp_nav(tid: str, url: str) -> None:
    req = urllib.request.Request(f"{CDP}/navigate?target={tid}", data=url.encode(), method="POST")
    urllib.request.urlopen(req, timeout=60).read()
    time.sleep(1.5)


def cdp_eval(tid: str, js: str) -> str:
    req = urllib.request.Request(f"{CDP}/eval?target={tid}", data=js.encode(), method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read()).get("value", "")


ARTICLE_JS = (
    'Array.from(document.querySelectorAll("a"))'
    '.map(a=>[a.textContent.replace(/\\s+/g," ").trim(), a.href])'
    '.filter(([t,h])=>/page\\.htm/.test(h) && t.length>4)'
    '.map(([t,h])=>t+"\\t"+h).join("\\n")'
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
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


def slug_of(url: str) -> str:
    m = re.search(r"/(\d{4})/(\d{4})/(c\d+a\d+)/", url)
    return f"{m.group(1)}{m.group(2)}-{m.group(3)}" if m else hashlib.md5(url.encode()).hexdigest()[:12]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--columns", required=True)
    ap.add_argument("--pages", type=int, default=3)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    idx_p = ROOT / "sources" / "cdp-index.json"
    index = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}

    tid = cdp_new(f"https://{args.host}/")
    found: dict[str, str] = {}
    for col in args.columns.split(","):
        for page in range(1, args.pages + 1):
            suffix = "list.htm" if page == 1 else f"list{page}.htm"
            url = f"https://{args.host}/{col.strip()}/{suffix}"
            try:
                cdp_nav(tid, url)
            except Exception as e:  # noqa: BLE001
                print(f"[跳过] {url}: {e}")
                break
            rows = cdp_eval(tid, ARTICLE_JS).strip()
            if not rows:
                break
            new = 0
            for line in rows.split("\n"):
                if "\t" not in line:
                    continue
                t, h = line.split("\t", 1)
                if h not in found:
                    found[h] = t
                    new += 1
            print(f"[栏目 {col} p{page}] 新增 {new}，累计 {len(found)}")
            if new == 0:
                break

    print(f"\n共发现 {len(found)} 篇文章，开始抓正文")
    added = 0
    for url, title in found.items():
        s = slug_of(url)
        if s in index:
            continue
        try:
            html = fetch(url)
        except Exception:  # noqa: BLE001
            continue
        text = body_text(html)
        if len(text) < 200:
            continue
        (OUT / f"{s}.txt").write_text(text, encoding="utf-8")
        index[s] = {
            "url": url, "title": title, "chars": len(text),
            "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
            "published": pub_date(html),
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "kind": "cdp", "host": args.host,
        }
        added += 1
        print(f"  [收] {index[s]['published'] or '   -   '} {len(text):>5} 字  {title[:40]}")
        time.sleep(0.15)

    idx_p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n新增 {added} 篇，索引共 {len(index)} 条")


if __name__ == "__main__":
    main()
