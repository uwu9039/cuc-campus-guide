"""爬取 ilib 图书馆门户的列表型栏目（新闻、书评、推荐、微课等）。

列表接口：engine2/data/api-v2/0/type/datas?e=<导航引擎>&t=<栏目 publicId>
p2 是每页条数（上限约 200），p 是页码。
"""
from __future__ import annotations

import hashlib
import html as htmllib
import json
import re
import time
import urllib.parse
import urllib.request
import http.cookiejar
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
NAV = ROOT / "_ilib_nav.json"
RAW_DIR = SRC / "ilib-list"
TEXT_DIR = SRC / "ilib-list-text"
INDEX = SRC / "ilib-list-index.json"

BASE = "https://ilib.cuc.edu.cn"
NAV_ENGINE = "72c0388e5ac91311ef183b86750fdaf0d81f"
NEWS_ENGINE = "c623aaa02a1a0311ef28b096bdaff9e3cef8"
NEWS_TYPE = "c6272d110a1a0311ef28b098d1b322c5ad5e"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
CST = timezone(timedelta(hours=8))
GROUPS = {
    "本馆资源", "专题资源", "读者服务", "学校活动", "学校服务", "读者指南", "读书角",
    "指南引导", "科研支持", "科研活动", "校园科研", "科研创新", "馆际合作", "校园馆际",
    "学校合作", "首页",
}

TAG = re.compile(r"<[^>]+>")
BLOCK = re.compile(r"(?i)</?(?:p|div|li|tr|h[1-6]|table|tbody|thead|ul|ol|section|article)[^>]*>")


def load_opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept-Language", "zh-CN,zh;q=0.9")]
    op.open(BASE + "/", timeout=30).read()
    return op


def clean_text(raw: str) -> str:
    s = raw or ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</td>", " | ", s)
    s = re.sub(r"(?i)</tr>", "\n", s)
    s = BLOCK.sub("\n", s)
    s = re.sub(r"(?i)<img[^>]+src=[\"']([^\"']+)[\"'][^>]*>", r"[图] \1", s)
    s = re.sub(r"(?i)<iframe[^>]+src=[\"']([^\"']+)[\"'][^>]*>", r"[附件] \1", s)
    s = TAG.sub("", s)
    s = htmllib.unescape(s)
    s = s.replace("\xa0", " ").replace("\u3000", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]*\n+", "\n", s)
    lines = [ln.strip(" |") for ln in s.split("\n")]
    return "\n".join(ln for ln in lines if ln).strip()


def safe_name(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|\r\n]", "_", s or "")
    s = re.sub(r"\s+", "", s)
    return s[:60] or "未命名"


def item_title(item: dict) -> str:
    for key in ("1", "title", "name"):
        v = item.get(key)
        if isinstance(v, dict) and v.get("value"):
            return clean_text(str(v["value"])).split("\n")[0][:80]
        if isinstance(v, str) and v.strip():
            return clean_text(v).split("\n")[0][:80]
    text = clean_text(item.get("content") or "")
    return text.split("\n")[0][:80] if text else ""


def item_author(item: dict) -> str:
    v = item.get("3")
    if isinstance(v, dict) and v.get("value"):
        return str(v["value"]).strip()[:60]
    return ""


def item_time(item: dict) -> str:
    v = item.get("6")
    if isinstance(v, dict) and v.get("value"):
        return str(v["value"]).strip()[:30]
    return ""


def iter_pages(op, engine: str, type_id: str, label: str):
    """逐条取：p2=1 时接口才返回 content，p2>1 只有元数据。

    按页产出，调用方边收边落盘，中途断掉也能续。
    """
    page = 1
    total_page = 1
    while page <= total_page:
        q = urllib.parse.urlencode({
            "e": engine, "t": type_id, "ap": 1, "sw": "", "p2": 1,
            "p": page, "nv": "false", "m": 0,
        })
        url = f"{BASE}/engine2/data/api-v2/0/type/datas?{q}"
        req = urllib.request.Request(url, headers={
            "Referer": BASE + "/", "Accept": "application/json, text/plain, */*",
        })
        payload = None
        for attempt in range(3):
            try:
                payload = json.loads(op.open(req, timeout=40).read())
                break
            except Exception as exc:
                if attempt == 2:
                    print(f"[跳过] {label} 第{page}条 请求失败：{exc}")
                time.sleep(0.8)
        if not payload:
            break
        data = ((payload.get("data") or {}).get("datas") or {})
        rows = data.get("datas") or []
        total_page = int(data.get("totalPage") or 0)
        if page == 1:
            print(f"[列表] {label:<16} {int(data.get('totalRecords') or 0):>4} 条")
        if not rows:
            break
        yield rows
        page += 1
        if page % 50 == 0:
            print(f"  {label} 第{page}/{total_page}页")
        time.sleep(0.2)


def seed_index() -> dict:
    """断点续爬：磁盘上已有的篇目直接补进索引，不再重复请求。"""
    out: dict[str, dict] = {}
    for p in sorted(TEXT_DIR.glob("*.txt")):
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        if not lines:
            continue
        url = next((ln.split("：", 1)[1].strip() for ln in lines[:5]
                    if ln.startswith("来源：")), "")
        label = next((ln.split("：", 1)[1].strip() for ln in lines[:6]
                      if ln.startswith("栏目：")), "")
        body = p.read_text(encoding="utf-8", errors="ignore").split("\n\n", 1)[-1]
        out[p.stem] = {
            "url": url,
            "title": lines[0].strip(),
            "label": label,
            "chars": len(body.strip()),
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16],
            "fetched_at": "",
            "kind": "ilib-list",
        }
    return out


def main() -> None:
    import sys

    only = [x for x in sys.argv[1:] if not x.startswith("-")]
    nav = json.loads(NAV.read_text(encoding="utf-8"))
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    index = seed_index()
    op = load_opener()
    seen: set[str] = {k.rsplit("-", 1)[-1] for k in index}
    fetched = 0

    columns = [(x["label"], x["publicId"], NAV_ENGINE) for x in nav
               if x.get("publicId") and x["label"] not in GROUPS and x.get("showType") != 2]
    columns.append(("新闻公告", NEWS_TYPE, NEWS_ENGINE))
    if only:
        columns = [c for c in columns if c[0] in only]
        print(f"只跑栏目：{[c[0] for c in columns]}")

    for label, type_id, engine in columns:
        for rows in iter_pages(op, engine, type_id, label):
            for item in rows:
                pid = str(item.get("publicId") or item.get("id") or "")
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                title = item_title(item) or label
                body = clean_text(item.get("content") or "")
                if len(body) < 40:
                    continue
                detail = item.get("dataUrl") or ""
                url = BASE + detail if detail.startswith("/") else detail
                if not url:
                    url = f"{BASE}/engine2/data/api-v2/detail/data/{engine}/{type_id}/{pid}"
                fetched_at = datetime.now(CST).isoformat(timespec="seconds")
                stem = f"{safe_name(label)}-{pid}"
                text = (
                    f"{title}\n"
                    f"来源：{url}\n"
                    f"栏目：{label}\n"
                    f"作者：{item_author(item)}\n"
                    f"发布时间：{item_time(item)}\n\n"
                    f"{body}\n"
                )
                (TEXT_DIR / f"{stem}.txt").write_text(text, encoding="utf-8")
                (RAW_DIR / f"{stem}.json").write_text(
                    json.dumps(item, ensure_ascii=False, indent=1), encoding="utf-8")
                index[stem] = {
                    "url": url,
                    "title": title,
                    "label": label,
                    "chars": len(body),
                    "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()[:16],
                    "fetched_at": fetched_at,
                    "kind": "ilib-list",
                }
                fetched += 1
            time.sleep(0.3)
            if fetched and fetched % 50 == 0:
                INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
                print(f"  已落盘 {fetched} 篇")

    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    total_chars = sum(v.get("chars", 0) for v in index.values())
    print(f"\n共入库 {fetched} 篇列表文章，索引 {len(index)} 条，正文 {total_chars} 字")
    print(f"正文目录：{TEXT_DIR}")


if __name__ == "__main__":
    main()
