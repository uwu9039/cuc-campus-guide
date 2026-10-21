"""抓取微信公众号推文正文，存进 sources/wechat/。

公众号不是官网，所以每条都要留：公众号名 + 推文标题 + 发布日期 + 原文链接。
推文里引用的文件号（如「本科生院〔2024〕115号」）仍须回官网原文核对。

用法：
    python tools/crawl_wechat.py URL [URL ...]
    python tools/crawl_wechat.py --file urls.txt
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sources" / "wechat"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
TZ = timezone(timedelta(hours=8))


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://mp.weixin.qq.com/",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def pick(html: str, pattern: str) -> str:
    m = re.search(pattern, html, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def parse(html: str) -> dict:
    if "环境异常" in html and "js_content" not in html:
        return {"error": "触发微信环境验证（需人工打开或换 UA/时段）"}

    m = re.search(r'<div class="rich_media_content[^"]*"[^>]*id="js_content"[^>]*>(.*?)</div>\s*</div>', html, re.S)
    body = m.group(1) if m else ""
    body = re.sub(r"<style.*?</style>|<script.*?</script>", " ", body, flags=re.S)
    body = re.sub(r"<img[^>]*?(?:data-src|src)=\"([^\"]+)\"[^>]*>", r" [图] \1 ", body)
    body = re.sub(r"</(p|section|div|li|h\d|tr|blockquote)>", "\n", body)
    body = re.sub(r"<br\s*/?>", "\n", body)
    body = re.sub(r"<[^>]+>", "", body)
    body = (body.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
                .replace("&ldquo;", "“").replace("&rdquo;", "”"))
    lines = [re.sub(r"[ \t\u3000\u00a0]+", " ", l).strip() for l in body.split("\n")]
    text = "\n".join(l for l in lines if l)

    nickname = pick(html, r'var nickname = "([^"]*)"') or pick(html, r'id="js_name"[^>]*>\s*([^<]+)')
    title = pick(html, r'<meta property="og:title" content="([^"]*)"') or \
            pick(html, r'class="rich_media_title"[^>]*>\s*([^<]+)')
    ct = pick(html, r'var ct = "(\d+)"')
    pub = datetime.fromtimestamp(int(ct), TZ).date().isoformat() if ct else ""
    author = pick(html, r'var author = "([^"]*)"')
    return {"text": text, "account": nickname, "title": title, "date": pub, "author": author}


def main() -> None:
    urls: list[str] = []
    if "--file" in sys.argv:
        urls = [l.strip() for l in Path(sys.argv[sys.argv.index("--file") + 1]).read_text(encoding="utf-8").splitlines() if l.strip()]
    else:
        urls = [a for a in sys.argv[1:] if a.startswith("http")]

    if not urls:
        print("用法: python tools/crawl_wechat.py <url> [...] 或 --file urls.txt")
        return

    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = ROOT / "sources" / "wechat-index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}

    for url in urls:
        try:
            html = fetch(url)
            info = parse(html)
        except Exception as e:  # noqa: BLE001
            print(f"[失败] {url[:70]} {e}")
            continue
        if info.get("error"):
            print(f"[跳过] {info['error']}  {url[:70]}")
            continue
        if len(info["text"]) < 100:
            print(f"[跳过] 正文过短({len(info['text'])})  {url[:70]}")
            continue

        slug = f"{info.get('date') or 'nodate'}-{hashlib.sha256(url.encode()).hexdigest()[:8]}"
        (OUT / f"{slug}.txt").write_text(info["text"], encoding="utf-8")
        index[slug] = {
            "url": url,
            "account": info["account"],
            "title": info["title"],
            "date": info["date"],
            "author": info.get("author", ""),
            "chars": len(info["text"]),
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "kind": "wechat",
        }
        print(f"[收] {len(info['text']):>5} 字  {info['account']}｜{info['title'][:34]}｜{info['date']}")
        time.sleep(0.8)

    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n累计 {len(index)} 篇公众号推文，存于 sources/wechat/")


if __name__ == "__main__":
    main()
