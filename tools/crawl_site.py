"""从学校各部门官网抓取办事类官方文件，存进 sources/crawl/。

用途：把「事项库」的原料从 13 条扩到几十条，且每条都有官方页面可回溯。

用法：
    python tools/crawl_site.py            # 用内置种子跑一遍
    python tools/crawl_site.py --budget 80

产物：
    sources/crawl/<slug>.txt       页面正文
    sources/crawl-index.json       标题 / url / 字符数 / 抓取时间
"""
from __future__ import annotations

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
OUT = ROOT / "sources" / "crawl"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
TZ = timezone(timedelta(hours=8))

SEEDS = [
    "https://jwc.cuc.edu.cn/13082/list.htm",     # 教务处 学籍管理（优先）
    "https://jwc.cuc.edu.cn/13082/list2.htm",
    "https://jwc.cuc.edu.cn/6366/list.htm",      # 教务处 学籍相关
    "https://jwc.cuc.edu.cn/cjyw/list.htm",      # 教务处 常见业务（学生）
    "https://jwc.cuc.edu.cn/bllc/list.htm",      # 教务处 办理流程
    "https://jwc.cuc.edu.cn/cjxz/list.htm",      # 教务处 常用下载
    "https://jwc.cuc.edu.cn/zcwj/list.htm",      # 教务处 政策文件
    "https://its.cuc.edu.cn/fwtzzn/list.htm",    # 信息化处 服务指南大全
    "https://its.cuc.edu.cn/8478/list.htm",      # 信息化处 校园卡服务
    "https://its.cuc.edu.cn/8447/list.htm",      # 信息化处 常用文档
    "https://tiyu.cuc.edu.cn/",                  # 体育部 首页
    "https://xsc.cuc.edu.cn/",                   # 学生工作部 首页
    "https://lib.cuc.edu.cn/",                   # 图书馆
    "https://xyy.cuc.edu.cn/",                   # 校医院
    "https://cwc.cuc.edu.cn/",                   # 财务处
    "https://jwc.cuc.edu.cn/6487/list.htm",      # 教务处 校内规章
    "https://jwc.cuc.edu.cn/6364/list.htm",      # 教务处 通知公告
    "https://jwc.cuc.edu.cn/13082/list.htm",     # 教务处 学籍管理（含学籍管理规定）
    "https://jwc.cuc.edu.cn/6366/list.htm",      # 教务处 学籍相关
    "https://jwc.cuc.edu.cn/6365/list.htm",      # 教务处 规章制度总览
    "https://jwc.cuc.edu.cn/13082/list2.htm",
]

SKIP = re.compile(
    r"(javascript:|#|mailto:|\.(jpg|jpeg|png|gif|css|js|ico|zip|rar)$)", re.I)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
        enc = r.headers.get_content_charset()
    for e in [enc, "utf-8", "gb18030"]:
        if not e:
            continue
        try:
            return raw.decode(e)
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


def links(html: str, base: str) -> list[tuple[str, str]]:
    out = []
    for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        if SKIP.search(href):
            continue
        url = urllib.parse.urljoin(base, href)
        if "cuc.edu.cn" not in url:
            continue
        if not re.search(r"\.(htm|html)$", url.split("?")[0]):
            continue
        label = re.sub(r"<[^>]+>", "", text)
        label = re.sub(r"\s+", " ", label).strip()
        out.append((url, label))
    return out


def slug_for(url: str) -> str:
    m = re.search(r"/(\d{4})/(\d{4})/(c\d+a\d+)/", url)
    if m:
        return f"{m.group(1)}{m.group(2)}-{m.group(3)}"
    host = url.split("//")[1].split("/")[0].split(".")[0]
    tail = [p for p in url.split("/") if p]
    return host + "-" + (tail[-1].replace(".htm", "").replace(".html", "")[:24] if tail else "index")


def main() -> None:
    budget = 90
    if "--budget" in sys.argv:
        budget = int(sys.argv[sys.argv.index("--budget") + 1])

    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = OUT.parent / "crawl-index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}

    seen: set[str] = set()
    queue: list[tuple[str, str, int]] = []  # url, label, depth
    for s in SEEDS:
        queue.append((s, "seed", 0))

    added = 0
    while queue and added < budget:
        url, label, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            html = fetch(url)
        except Exception as e:  # noqa: BLE001
            print(f"[跳过] {url[:70]} {e}")
            continue

        text = body_text(html)
        is_list = "list.htm" in url or url.rstrip("/").count("/") <= 3
        # 列表页：只收链接，不存正文
        if is_list and len(links(html, url)) > 8:
            for u, t in links(html, url):
                if u not in seen and "cuc.edu.cn" in u:
                    queue.append((u, t, depth + 1))
            continue

        if len(text) < 120:  # 太空的页不要
            continue

        slug = slug_for(url)
        (OUT / f"{slug}.txt").write_text(text, encoding="utf-8")
        index[slug] = {
            "url": url,
            "title": title_of(html) or label,
            "chars": len(text),
            "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "seed_depth": depth,
        }
        added += 1
        print(f"[收] {len(text):>5} 字  {title_of(html)[:38]:<38} {url[:60]}")
        time.sleep(0.3)

    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n本次新增 {added} 页，累计 {len(index)} 页官方正文，存于 sources/crawl/")


if __name__ == "__main__":
    main()
