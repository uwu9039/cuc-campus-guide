"""第三轮别名补齐：把近义错位（预约座位 / 熄灯 / 宿舍网 / 夜宵等）拉到精确命中。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


TEXTS: dict[str, str] = {}
for sub in ("wendao-text", "great", "local", "huibian", "crawl", "cdp", "extra", "wechat", "pdf"):
    d = SRC / sub
    if not d.exists():
        continue
    for f in d.glob("*.txt"):
        TEXTS.setdefault(f.stem, squash(f.read_text(encoding="utf-8", errors="ignore")))
for f in SRC.glob("*.txt"):
    TEXTS.setdefault(f.stem, squash(f.read_text(encoding="utf-8", errors="ignore")))


def q(src: str, text: str) -> dict[str, str]:
    assert squash(text) in TEXTS.get(src, ""), f"{src} 找不到：{text[:60]}"
    return {"src": src, "quote": text}


ADD_ALIASES = {
    "lib-zuowei-yuyue": ["图书馆能预约座位吗", "预约座位", "图书馆预约座位", "座位预约怎么约"],
    "shitang-shijian": ["食堂有夜宵吗", "夜宵", "有没有夜宵"],
    "sushe-menjin": ["宿舍几点熄灯", "宿舍熄灯", "几点熄灯"],
    "it-wangluo": ["宿舍网怎么连", "宿舍怎么上网", "宿舍上网"],
    "sushe-chongwu": ["宿舍可以养乌龟吗", "养乌龟", "养宠物"],
    "shitang-zhifu": ["校园码在哪", "校园码"],
    "it-vpn": ["vpn怎么用", "VPN怎么用"],
}

NEW_PITFALLS = {
    "shitang-shijian": [
        ("官方只公布早、中、晚三个供餐时段，没有单列夜宵档口。",
         q("28d54bca", "北苑餐厅一层和二层基本伙、民族餐厅供餐时间：早餐 6:30 至 9:00，中餐 11:00 至 13:00，晚餐 17:00 至 18:30")),
    ],
}


def main() -> None:
    p = ROOT / "items.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    by_id = {it["id"]: it for it in data["items"]}

    added = 0
    for iid, aliases in ADD_ALIASES.items():
        it = by_id[iid]
        for a in aliases:
            if a not in it["aliases"]:
                it["aliases"].append(a)
                added += 1

    new_pf = 0
    for iid, items in NEW_PITFALLS.items():
        it = by_id[iid]
        for text, quote in items:
            i = len(it["pitfalls"])
            it["pitfalls"].append(text)
            it["evidence"][f"pitfalls.{i}"] = quote
            new_pf += 1

    data["updated"] = "2026-10-30"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"补别名 {added} 个，补提示 {new_pf} 条，总计 {len(data['items'])}")


if __name__ == "__main__":
    main()
