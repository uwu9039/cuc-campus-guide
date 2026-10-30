"""宿舍类长条目按步骤打 tags，让 _narrow_steps 能收窄；家具条目移出被褥、补床铺类型。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
PATH = ROOT / "items.json"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def q(src: str, quote: str) -> dict:
    return {"src": src, "quote": quote}


data = json.loads(PATH.read_text(encoding="utf-8"))
by_id = {it["id"]: it for it in data["items"]}

# ---------- sushe-jiaju：去掉被褥两步（已由 sushe-chuangpin 承载），补床铺类型 ----------
jiaju = by_id["sushe-jiaju"]
old_steps = jiaju["steps"]
old_ev = jiaju["evidence"]
keep = [0, 1, 2, 3, 6, 7]
mapping = {old: new for new, old in enumerate(keep)}
steps = [old_steps[i] for i in keep]
ev = {}
for k, v in old_ev.items():
    m = re.fullmatch(r"steps\.(\d+)", k)
    if m:
        oi = int(m.group(1))
        if oi not in mapping:
            continue
        ev[f"steps.{mapping[oi]}"] = v
    else:
        ev[k] = v

TAGS_JIAJU = [
    ["桌子", "椅子", "柜子", "桌椅"],
    ["中蓝宿舍一期", "中蓝一期", "桌子"],
    ["床", "衣柜", "电脑桌"],
    ["上下铺", "上铺", "下铺", "床位"],
    ["房间配置", "配套"],
    ["中蓝二期", "床"],
]
for i, tags in enumerate(TAGS_JIAJU):
    steps[i]["tags"] = tags

src_f = "d940cbae"
new_rows = [
    (
        "床铺类型（中蓝 F 区）",
        "中蓝 F 区分两种床：上下铺、上床下桌；上床下桌房间 4 人间配 4 套、6 人间配 6 套。",
        "2、F 区（分两种床）:（1）上下铺，（2）上床下桌；3、上床下桌房间：4 人间就是4 套，6 人间6 套。",
        ["上床下桌", "床铺类型"],
    ),
    (
        "上床下桌尺寸",
        "上床下桌外框长 200 × 宽 90 × 高 200 厘米，上铺到房顶 145、上铺到地面 170；上下铺外框 200 × 90 × 220 厘米，上下铺间距 100。",
        "上床下桌尺寸：外框长200 `*`宽90 `*`高200；上铺到房顶高度：145，上铺到地面高度：170；上下铺尺寸：长200 `*`宽90 `*`高220，上下铺之间高度：100",
        ["上床下桌", "尺寸"],
    ),
    (
        "床位分布",
        "中蓝 F 区 4 人间上床下桌：2、3 号床靠窗，1、4 号床靠门；6 人间上床下桌：3、4 靠窗，1、6 靠门，2、5 中间。",
        "4 人间上床下桌：2、3 靠窗，1、4 靠门，4 人间上下铺：1、2 靠门，3、4靠窗。6 人间上床下桌：3、4 靠窗，1、6 靠门，2、5 中间。",
        ["床位", "上床下桌"],
    ),
]
text_d940 = squash((SRC / "wendao-text" / f"{src_f}.txt").read_text(encoding="utf-8"))
for when, what, quote, tags in new_rows:
    assert squash(quote) in text_d940, f"quote 不在原文: {quote[:30]}"
    steps.append({"when": when, "what": what, "tags": tags})
    ev[f"steps.{len(steps) - 1}"] = q(src_f, quote)

jiaju["steps"] = steps
jiaju["evidence"] = ev
for a in ["上床下桌", "宿舍是上床下桌吗", "上床下桌吗", "宿舍床铺类型", "床铺类型",
          "上下铺还是上床下桌", "宿舍的床是上床下桌吗", "中蓝是上床下桌吗"]:
    if a not in jiaju["aliases"]:
        jiaju["aliases"].append(a)

# ---------- sushe-sheshi：给九步打 tags，并接收泛问法 ----------
sheshi = by_id["sushe-sheshi"]
TAGS_SHESHI = [
    ["空调"],
    ["卫浴", "卫生间", "浴室", "独立卫浴"],
    ["卫浴", "卫生间", "浴室", "独立卫浴"],
    ["卫浴", "卫生间", "浴室", "独立卫浴"],
    ["阳台"],
    ["直饮水", "饮水机", "洗衣机"],
    ["几人间", "房型", "人间"],
    ["床帘", "改造", "挪床", "挪柜子"],
    ["查寝", "查卫生"],
]
assert len(sheshi["steps"]) == len(TAGS_SHESHI)
for step, tags in zip(sheshi["steps"], TAGS_SHESHI):
    step["tags"] = tags
for a in ["宿舍怎么样", "宿舍好不好", "宿舍环境怎么样", "宿舍环境",
          "宿舍住宿条件", "宿舍怎么样啊", "宿舍好吗", "宿舍情况"]:
    if a not in sheshi["aliases"]:
        sheshi["aliases"].append(a)

# ---------- sushe-fangxing：补自然问法 ----------
fangxing = by_id["sushe-fangxing"]
for a in ["宿舍住几个人", "宿舍几个人", "宿舍多少人", "宿舍人数", "几个人一间", "宿舍几人间啊"]:
    if a not in fangxing["aliases"]:
        fangxing["aliases"].append(a)

PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("jiaju steps:", len(jiaju["steps"]), "| sheshi tags:", sum(1 for s in sheshi["steps"] if s.get("tags")))
