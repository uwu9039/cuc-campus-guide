"""军训要准备什么：用学校 2025 年参训学生应备物资清单（附件5）成条，不再只回时间。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"

LIST = "loc-附件5-中国传媒大学2025年参训学生应备物资清单-fd6bb2"
GUIDE = "loc-新生指南2026-水印版-76f3d8"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


TEXTS: dict[str, str] = {}
for sub in ("local", "wendao-text", "wendao-extra", "crawl", "extra", "wechat", "pdf"):
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


def ev(*quotes: dict[str, str]) -> dict:
    return quotes[0] if len(quotes) == 1 else {"sources": list(quotes)}


STEPS = [
    ("军训服装",
     "军训服装由学校统一发放（每人一套，无特殊原因不可多定）：帽子 1 顶、上衣 1 件、裤子 1 条、鞋 1 双、"
     "编织外腰带 1 条、内腰带 1 条、T 恤 2 件、短裤 1 条、领章 1 对、臂章 1 个",
     [q(LIST, "帽子1顶学校统一发放（每人一套，无特殊原因不可多定）2上衣1件3裤子1条4鞋1双"
              "5编织外腰带1条6内腰带1条7T恤2件8短裤1条9领章1对10臂章1个")]),
    ("床上用品",
     "床上用品自备或到基地自费购买：床单（床尺寸 0.9m×1.9m，素色深色系）、被罩（被子由基地提供，"
     "2m×1.5m，素色深色系）、枕头 1 个",
     [q(LIST, "床单（床尺寸0.9m×1.9m，床单颜色为素色深色系）1床学生自备或到基地自费购买",
        ),
      q(LIST, "被罩（被子由基地提供，尺寸为2mx1.5m，被罩颜色为素色深色系)1床13枕头1个")]),
    ("生活用品",
     "生活用品学生自备：餐具（饭盒、筷子、勺子，避免玻璃材质）、脸盆、漱口杯、牙膏、牙刷、洗碗布、"
     "洗发水、沐浴露/香皂、洗衣液、卫生纸、拖鞋、晾衣架、水杯、袜子、换洗内衣等",
     [q(LIST, "餐具（饭盒、筷子、勺子，避免玻璃材质）1套15脸盆1个16漱口杯1个17牙膏1个18牙刷1个"
              "19洗碗布1个20洗发水1瓶21沐浴露/香皂1瓶/个22洗衣液1瓶23卫生纸2卷24拖鞋1双25晾衣架若干个"
              "26水杯1个学生自备27袜子若干双28换洗内衣等若干套")]),
    ("可备物资",
     "可备物资（供参考）：毛巾、洗澡巾、防晒霜、洗面奶、风油精、鞋垫 2 对、梳子、针线、创可贴、运动鞋、刮须刀",
     [q(LIST, "毛巾1条学生自备30洗澡巾1条31防晒霜1瓶32洗面奶1瓶33风油精1瓶34鞋垫2对35梳子1把"
              "36针线1套37创可贴若干个38运动鞋1双39刮须刀1个")]),
    ("禁携物资",
     "禁携物资：吹风机、插线板、酒精等易燃易爆品、化学试剂、酒类（各类含酒精饮品）、弹簧刀、水果刀",
     [q(LIST, "吹风机——41电子配件类产品插线板——42易燃易爆酒精等——43有毒有害化学试剂——"
              "44酒类各类含酒精饮品——45利器弹簧刀——46水果刀——")]),
    ("清单版本",
     "以上是学校 2025 年参训学生应备物资清单；军训前学校可能会再发当年的应备物资清单，届时以新清单为准",
     [q(GUIDE, "军训前学校可能会发学生应备物资清单，到时候参照清单即可。")]),
]

PITFALLS = [
    ("军训服装外衣裤只有一套，军训过程中大概率没有机会洗",
     [q(GUIDE, "军训服装由学校统一订购，外衣裤只有一套，还会有帽子腰带等配套服装及一双没有鞋垫的鞋子，"
               "在军训过程中大概率没有机会洗")]),
    ("军训基地的插线板属于禁携物资，别带",
     [q(LIST, "电子配件类产品插线板——")]),
]

ALIASES = [
    "军训要准备什么", "军训准备什么", "军训要带什么", "军训带什么", "军训要带什么东西",
    "军训应备物资", "军训物资", "军训清单", "军训物品", "军训物品清单", "军训要准备哪些东西",
    "军训不能带什么", "军训禁带物品", "军训禁携物资", "军训能带吹风机吗", "军训能带插线板吗",
    "军训床上用品要自己带吗", "军训服装", "军训要自己买衣服吗",
]

item = {
    "id": "xinsheng-junxun-wupin",
    "title": "军训要带什么（应备物资 / 禁携物品）",
    "aliases": ALIASES,
    "keywords": ["军训物资", "应备物资", "军训清单", "禁携", "插线板", "军训服装", "被罩", "鞋垫"],
    "dept": "学生工作部",
    "channel": ["线下"],
    "audience": ["本科生"],
    "status": "verified",
    "confidence": "high",
    "materials": [],
    "steps": [],
    "fee": None,
    "location": None,
    "hours": None,
    "duration": None,
    "window": None,
    "pitfalls": [],
    "contact": None,
    "slots": [],
    "draft": None,
    "answer": None,
    "kind": "service",
    "source": [
        {"title": "中国传媒大学2025年参训学生应备物资清单（附件5）", "url": "", "checked": "2026-10-30"},
        {"title": "中传新生指南 2026（学生经验整理，非学校公开文件）", "url": "", "checked": "2026-10-30"},
    ],
    "evidence": {},
    "note": "物资清单以学校 2025 年参训学生应备物资清单为准；2026 年军训前学校可能另发新清单。",
}

for i, (when, what, quotes) in enumerate(STEPS):
    item["steps"].append({"when": when, "what": what})
    item["evidence"][f"steps.{i}"] = ev(*quotes)
for i, (text, quotes) in enumerate(PITFALLS):
    item["pitfalls"].append(text)
    item["evidence"][f"pitfalls.{i}"] = ev(*quotes)

TAGS = [
    ["服装", "军训服", "衣服", "帽子", "T恤", "鞋"],
    ["床单", "被罩", "被子", "枕头", "床上用品"],
    ["生活用品", "洗漱", "盆", "拖鞋", "餐具", "饭盒", "水杯"],
    ["可备", "防晒", "鞋垫", "风油精", "创可贴"],
    ["禁携", "禁止", "不能带", "吹风机", "插线板", "可以带吗", "能带"],
    ["清单", "通知", "2026", "最新"],
]
for s, t in zip(item["steps"], TAGS):
    s["tags"] = t

data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
items = data["items"]
by_id = {it["id"]: it for it in items}
if "xinsheng-junxun-wupin" in by_id:
    by_id["xinsheng-junxun-wupin"].update(item)
else:
    idx = next((i for i, it in enumerate(items) if it["id"] == "xinsheng-junxun"), len(items) - 1)
    items.insert(idx + 1, item)

(ROOT / "items.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"条目总数 {len(items)}；xinsheng-junxun-wupin 步骤 {len(item['steps'])}，坑 {len(item['pitfalls'])}")
