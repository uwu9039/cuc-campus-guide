"""抓学院师资：老师姓名 / 职称 / 职务 / 邮箱 / 研究方向。

站点是 JS 渲染的，列表和详情都要用浏览器（CDP 代理）拿。

用法：
    python tools/crawl_faculty.py --host dsmi.cuc.edu.cn --college 数据科学与智能媒体学院
    python tools/crawl_faculty.py --host ccs.cuc.edu.cn  --college 计算机与网络空间安全学院
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
OUT = ROOT / "faculty.json"
CDP = "http://localhost:3456"
TZ = timezone(timedelta(hours=8))

FIELDS = ["姓名", "职称", "职务", "邮箱", "电话", "办公室", "研究方向", "教育背景", "学术兼职"]


def cdp_new(url: str) -> str:
    req = urllib.request.Request(f"{CDP}/new", data=url.encode(), method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["targetId"]


def nav(tid: str, url: str) -> None:
    req = urllib.request.Request(f"{CDP}/navigate?target={tid}", data=url.encode(), method="POST")
    urllib.request.urlopen(req, timeout=90).read()
    time.sleep(1.2)


def ev(tid: str, js: str) -> str:
    req = urllib.request.Request(f"{CDP}/eval?target={tid}", data=js.encode("utf-8"), method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=90).read()).get("value", "")


LIST_JS = (
    '(()=>{const as=[...document.querySelectorAll("a")].filter(a=>String(a.href).indexOf("page.htm")>0);'
    'return as.map(a=>a.innerText.trim()+"\\t"+a.href).join("\\n")})()'
)

TEXT_JS = 'document.body.innerText.replace(/\\n{2,}/g,"\\n")'


def parse_profile(text: str, name_hint: str) -> dict:
    """从详情页纯文本里抽字段：一行「姓名：X」这种结构很稳。"""
    rec: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        for f in FIELDS:
            m = re.match(rf"^{f}\s*[：:]\s*(.+)$", line)
            if m and f not in rec:
                rec[f] = m.group(1).strip()[:120]
    if "姓名" not in rec and name_hint:
        rec["姓名"] = name_hint
    # 研究方向常在标题下面几行，取到下一个字段前
    if "研究方向" not in rec:
        m = re.search(r"研究方向\s*[：:]?\s*\n?(.{0,120})", text)
        if m:
            rec["研究方向"] = re.sub(r"\s+", " ", m.group(1)).strip()[:120]
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--college", required=True)
    ap.add_argument("--list", default="/szdw/list.htm")
    ap.add_argument("--max", type=int, default=0)
    args = ap.parse_args()

    tid = cdp_new(f"https://{args.host}/")
    nav(tid, f"https://{args.host}{args.list}")
    raw = ev(tid, LIST_JS)
    pairs = []
    for line in raw.split("\n"):
        if "\t" not in line:
            continue
        name, href = line.split("\t", 1)
        name = name.strip()
        if 2 <= len(name) <= 5 and re.fullmatch(r"[\u4e00-\u9fff·]+", name):
            pairs.append((name, urllib.parse.urljoin(f"https://{args.host}", href)))
    pairs = list(dict.fromkeys(pairs))
    print(f"{args.college}：发现 {len(pairs)} 位教师")
    if args.max:
        pairs = pairs[: args.max]

    store = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"people": []}
    have = {(p.get("college"), p.get("姓名")) for p in store["people"]}

    added = 0
    for name, url in pairs:
        if (args.college, name) in have:
            continue
        try:
            nav(tid, url)
            text = ev(tid, TEXT_JS)
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {name}: {e}")
            continue
        rec = parse_profile(text, name)
        rec.update({"college": args.college, "url": url,
                    "fetched_at": datetime.now(TZ).isoformat(timespec="seconds")})
        store["people"].append(rec)
        added += 1
        mail = rec.get("邮箱", "")
        print(f"  [收] {name:<4} {rec.get('职称','')[:8]:<9} {mail}")

    store["updated"] = datetime.now(TZ).isoformat(timespec="seconds")
    OUT.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n新增 {added} 位，faculty.json 共 {len(store['people'])} 位")


if __name__ == "__main__":
    main()
