"""站点级采集：先把部门官网的所有栏目扫出来，再按「与新规定相关 + 发布时间新」排序抓正文。

设计要点（针对之前"只抓第一页就被预算截断"的坑）：
  1. 发现：从首页提取全部栏目（/xxxx/list.htm），不靠人工给种子
  2. 翻页：每个栏目顺着 list.htm → list2 → list3 … 直到拿不到新条目
  3. 排序：标题命中「学籍/选课/成绩/毕业/转专业/休学/奖助/体测…」优先，同分按发布日期倒序
  4. 预算只防跑飞，栏目一定抓完

用法：
    python tools/crawl_sitemap.py                 # 默认四个部门，预算 160
    python tools/crawl_sitemap.py --budget 220
    python tools/crawl_sitemap.py --hosts jwc.cuc.edu.cn its.cuc.edu.cn
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
TZ = timezone(timedelta(hours=8))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

HOSTS = ["jwc.cuc.edu.cn", "its.cuc.edu.cn", "xsc.cuc.edu.cn", "tiyu.cuc.edu.cn",
         "lib.cuc.edu.cn", "xyy.cuc.edu.cn", "cwc.cuc.edu.cn",
         # 后勤 + 学院（2026-10-21 扩）
         "zchq.cuc.edu.cn", "dsmi.cuc.edu.cn", "ices.cuc.edu.cn",
         "ccs.cuc.edu.cn", "sic.cuc.edu.cn", "animation.cuc.edu.cn"]

PRIORITY = re.compile(
    r"学籍|选课|退课|重修|重考|缓考|免修|成绩|考试|毕业|结业|学位|转专业|转学|"
    r"休学|复学|保留学籍|退学|留级|奖助|奖学金|助学金|宿舍|校园卡|一卡通|"
    r"体测|体质|军训|入学|注册|请假|考勤|培养方案|辅修|微专业|"
    r"办理|申请|指南|流程|安排|须知|要求|办法|规定|细则")


def fetch(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
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


def body_text(html: str) -> str:
    m = re.search(r'class="wp_articlecontent"[^>]*>(.*?)</div>\s*</div>', html, re.S)
    seg = m.group(1) if m else html
    seg = re.sub(r"<style.*?</style>|<script.*?</script>", " ", seg, flags=re.S)
    seg = re.sub(r"<img[^>]*?(?:src|data-src)=\"([^\"]+)\"[^>]*>", r" [附件] \1 ", seg)
    seg = re.sub(r"</(p|div|tr|li|h\d|table|br)>|<br\s*/?>|<td[^>]*>", "\n", seg)
    seg = re.sub(r"<[^>]+>", "", seg)
    seg = (seg.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
    lines = [re.sub(r"[ \t\u3000\u00a0]+", " ", l).strip() for l in seg.split("\n")]
    return "\n".join(l for l in lines if l)


def pub_date(html: str) -> str:
    m = re.search(r"发布时间[：:]\s*(\d{4})-(\d{2})-(\d{2})", html) or \
        re.search(r"(\d{4})-(\d{2})-(\d{2})", html)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def title_of(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def links(html: str, base: str, pattern: str) -> list[tuple[str, str]]:
    out = []
    for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        u = urllib.parse.urljoin(base, href)
        if not re.search(pattern, u):
            continue
        label = re.sub(r"<[^>]+>", "", text)
        label = re.sub(r"\s+", " ", label).strip()
        if label:
            out.append((u, label))
    return out


def slug(url: str) -> str:
    m = re.search(r"/(\d{4})/(\d{4})/(c\d+a\d+)/", url)
    return f"{m.group(1)}{m.group(2)}-{m.group(3)}" if m else re.sub(r"\W+", "-", url)[-28:]


def main() -> None:
    budget = 160
    if "--budget" in sys.argv:
        budget = int(sys.argv[sys.argv.index("--budget") + 1])
    hosts = HOSTS
    if "--hosts" in sys.argv:
        i = sys.argv.index("--hosts")
        hosts = [a for a in sys.argv[i + 1:] if not a.startswith("--")]

    OUT.mkdir(parents=True, exist_ok=True)
    idx_p = ROOT / "sources" / "crawl-index.json"
    index = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}

    # ---- 1. 发现栏目 ----
    columns: set[str] = set()
    for h in hosts:
        try:
            home = fetch(f"https://{h}/")
        except Exception as e:  # noqa: BLE001
            print(f"[跳过] {h}: {e}")
            continue
        for u, _ in links(home, f"https://{h}/", r"/[a-zA-Z0-9_]+/list\.htm$"):
            columns.add(u.split("?")[0])
        print(f"[栏目] {h}: 发现 {len(columns)} 个（累计）")

    # ---- 2. 栏目翻页，收集文章 ----
    articles: dict[str, str] = {}
    for col in sorted(columns):
        for page in range(1, 9):
            url = col if page == 1 else col.replace("list.htm", f"list{page}.htm")
            try:
                html = fetch(url)
            except Exception:  # noqa: BLE001
                break
            found = links(html, url, r"/\d{4}/\d{4}/c\d+a\d+/page\.htm$")
            if not found:
                break
            new = 0
            for u, t in found:
                if u not in articles:
                    articles[u] = t
                    new += 1
            if new == 0:
                break
            time.sleep(0.15)
        print(f"[栏目] {col.split('cuc.edu.cn')[1]:<28} 累计文章 {len(articles)}")

    # ---- 3. 排序：主题相关优先，其次新近 ----
    def score(item: tuple[str, str]) -> tuple[int, str]:
        u, t = item
        m = re.search(r"/(\d{4})/(\d{4})/", u)
        d = f"{m.group(1)}-{m.group(2)}" if m else "0000-00"
        return (1 if PRIORITY.search(t) else 0, d)

    ordered = sorted(articles.items(), key=score, reverse=True)
    print(f"\n共发现 {len(ordered)} 篇文章，开始抓正文（预算 {budget}，已入库的会跳过）")

    added = skipped = 0
    for u, t in ordered:
        if added >= budget:
            break
        s = slug(u)
        if s in index:
            skipped += 1
            continue
        try:
            html = fetch(u)
        except Exception:  # noqa: BLE001
            continue
        text = body_text(html)
        if len(text) < 150:
            continue
        (OUT / f"{s}.txt").write_text(text, encoding="utf-8")
        index[s] = {"url": u, "title": title_of(html) or t, "chars": len(text),
                    "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
                    "published": pub_date(html),
                    "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
                    "kind": "sitemap"}
        added += 1
        if PRIORITY.search(t):
            print(f"[收] {index[s]['published'] or '    -  '}  {len(text):>5} 字  {t[:36]}")
        time.sleep(0.2)

    idx_p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n新增 {added} 篇，跳过已入库 {skipped} 篇，索引共 {len(index)} 条")


if __name__ == "__main__":
    main()
