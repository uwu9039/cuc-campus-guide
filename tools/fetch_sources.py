"""抓取 items.json 里引用的所有官方页面，保存正文原文，作为唯一事实来源。

产物：
  sources/<slug>.txt   —— 页面正文纯文本（去掉标签，保留换行）
  sources/index.json   —— 每个来源的 url / slug / 抓取时间 / sha256 / 字符数 / 标题

用法：python tools/fetch_sources.py [--only slug1 slug2]
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")


def slugify(url: str) -> str:
    m = re.search(r"/(\d{4})/(\d{4})/(c\d+a\d+)/", url)
    if m:
        return f"{m.group(1)}{m.group(2)}-{m.group(3)}"
    parts = url.split("//", 1)[1].split("/")
    host = parts[0].split(".")[0]
    path = [p for p in parts[1:] if p]
    if not path:
        return f"{host}-index"
    if path[-1].startswith("list."):
        return f"{host}-{path[-2] if len(path) > 1 else 'index'}"
    return f"{host}-{path[-1].replace('.htm', '').replace('.html', '')}"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        ctype = r.headers.get_content_charset()
    for enc in [ctype, "utf-8", "gb18030"]:
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "ignore")


def body_text(html: str) -> str:
    m = re.search(r'class="wp_articlecontent"[^>]*>(.*?)</div>\s*</div>', html, re.S)
    body = m.group(1) if m else html
    body = re.sub(r"<style.*?</style>|<script.*?</script>", " ", body, flags=re.S)
    body = re.sub(r"<img[^>]*?(?:src|data-src)=\"([^\"]+)\"[^>]*>", r" [附件] \1 ", body)
    body = re.sub(r"</(p|div|tr|li|h\d|table|br)>", "\n", body)
    body = re.sub(r"<br\s*/?>|<td[^>]*>", "\n", body)
    body = re.sub(r"<[^>]+>", "", body)
    body = (body.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    lines = [re.sub(r"[ \t\u3000\u00a0]+", " ", l).strip() for l in body.split("\n")]
    return "\n".join(l for l in lines if l)


def title_of(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def main() -> None:
    SRC.mkdir(exist_ok=True)
    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
    urls = sorted({s["url"] for it in items for s in it.get("source", [])})

    only = None
    if "--only" in sys.argv:
        i = sys.argv.index("--only")
        only = set(sys.argv[i + 1:])

    index_path = SRC / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    tz = timezone(timedelta(hours=8))

    for url in urls:
        slug = slugify(url)
        if only and slug not in only:
            continue
        try:
            html = fetch(url)
            text = body_text(html)
            if len(text) < 40:
                print(f"[薄] {slug:<22} {len(text):>5} 字  ← 可能是附件下载页或需要登录")
            (SRC / f"{slug}.txt").write_text(text, encoding="utf-8")
            index[slug] = {
                "url": url,
                "title": title_of(html),
                "chars": len(text),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                "fetched_at": datetime.now(tz).isoformat(timespec="seconds"),
            }
            print(f"[ok] {slug:<22} {len(text):>5} 字")
        except Exception as e:  # noqa: BLE001
            print(f"[失败] {slug:<20} {e}")

    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n共 {len(index)} 个来源，正文存于 sources/")


if __name__ == "__main__":
    main()
