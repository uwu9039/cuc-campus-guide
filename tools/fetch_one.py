"""按 URL 精确抓取指定官方页面并入库（用于补漏：从搜索或用户指认找到的链接）。

用法：
    python tools/fetch_one.py URL [URL ...]
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
TZ = timezone(timedelta(hours=8))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")


def fetch(url: str) -> str:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
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


def body(html: str) -> str:
    m = re.search(r'class="wp_articlecontent"[^>]*>(.*?)</div>\s*</div>', html, re.S)
    seg = m.group(1) if m else html
    seg = re.sub(r"<style.*?</style>|<script.*?</script>", " ", seg, flags=re.S)
    seg = re.sub(r"<img[^>]*?(?:src|data-src)=\"([^\"]+)\"[^>]*>", r" [附件] \1 ", seg)
    seg = re.sub(r"</(p|div|tr|li|h\d|table|br)>|<br\s*/?>|<td[^>]*>", "\n", seg)
    seg = re.sub(r"<[^>]+>", "", seg)
    seg = (seg.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
    lines = [re.sub(r"[ \t\u3000\u00a0]+", " ", l).strip() for l in seg.split("\n")]
    return "\n".join(l for l in lines if l)


def title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def slug(url: str) -> str:
    m = re.search(r"/(\d{4})/(\d{4})/(c\d+a\d+)/", url)
    return f"{m.group(1)}{m.group(2)}-{m.group(3)}" if m else re.sub(r"\W+", "-", url)[-30:]


def main() -> None:
    urls = [a for a in sys.argv[1:] if a.startswith("http")]
    if not urls:
        print(__doc__)
        return
    idx_p = SRC / "crawl-index.json"
    index = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}
    (SRC / "crawl").mkdir(exist_ok=True)

    for u in urls:
        html = fetch(u)
        text = body(html)
        slug_ = slug(u)
        (SRC / "crawl" / f"{slug_}.txt").write_text(text, encoding="utf-8")
        index[slug_] = {"url": u, "title": title(html), "chars": len(text),
                        "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
                        "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
                        "kind": "manual"}
        print(f"[收] {len(text):>5} 字  {title(html)[:44]}  {slug_}")

    idx_p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"crawl 索引共 {len(index)} 条")


if __name__ == "__main__":
    main()
