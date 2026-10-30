"""给食堂条目补「清真食堂」位置与消费规则，并加别名。

只做 upsert / append，不删除任何已有条目。
"""
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
        TEXTS[f.stem] = squash(f.read_text(encoding="utf-8", errors="ignore"))
for f in SRC.glob("*.txt"):
    TEXTS.setdefault(f.stem, squash(f.read_text(encoding="utf-8", errors="ignore")))


def q(src: str, text: str) -> dict[str, str]:
    assert squash(text) in TEXTS.get(src, ""), f"{src} 找不到：{text[:50]}"
    return {"src": src, "quote": text}


NEW_STEPS = [
    ("清真食堂是基本伙餐厅，供应清真餐；位置与美食广场（艺术与传播大楼地下一层）连通，"
     "可从楼外楼梯或艺传南侧楼梯下到 B1 层。",
     [
         q("loc-新生指南2026-水印版-76f3d8", "清真食堂也是基本伙，调料会比北苑加得多（更好吃）。"),
         q("loc-新生指南2026-水印版-76f3d8",
           "美食广场（下沉广场）位于艺术与传播大楼负一楼，里面有肯德基、米村拌饭、星巴克等连锁品牌，"
           "并且和清真食堂连通，可以直接从外面的楼梯走下去，也可以从艺传南面的楼梯坐到B1层。"),
     ]),
    ("清真餐消费提示：清真餐厅属基本伙食堂，无基本伙消费权限（如未用校园卡）就餐会加收 45% 成本补偿费。",
     [
         q("48e1da04",
           "非基本伙消费权限人员在基本伙食堂（北苑食堂、中蓝餐厅、清真餐厅）就餐会收取45%的成本补偿费。"),
     ]),
]

NEW_ALIASES = ["清真食堂", "清真餐厅", "清真食堂在哪", "清真食堂在哪儿", "清真食堂怎么走", "清真餐"]

NEW_SOURCE = {"title": "校园卡常见问题（食堂消费、补卡、充值）", "url": "", "checked": "2026-10-30"}


def main() -> None:
    p = ROOT / "items.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    item = next(it for it in data["items"] if it["id"] == "shitang-canting")

    for text, quotes in NEW_STEPS:
        i = len(item["steps"])
        item["steps"].append({"when": "清真食堂", "what": text})
        item["evidence"][f"steps.{i}"] = quotes[0] if len(quotes) == 1 else {"sources": quotes}

    added = 0
    for a in NEW_ALIASES:
        if a not in item["aliases"]:
            item["aliases"].append(a)
            added += 1

    if not any(s.get("title") == NEW_SOURCE["title"] for s in item["source"]):
        item["source"].append(NEW_SOURCE)

    data["updated"] = "2026-10-30"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"清真食堂：加 {len(NEW_STEPS)} 步，补别名 {added} 个，总计 {len(data['items'])}")


if __name__ == "__main__":
    main()
