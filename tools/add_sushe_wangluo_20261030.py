"""宿舍有没有校园网 / WiFi：把两种口径分开写清楚，别拿排障步骤当答案。

2022 新生指南：无线网未覆盖宿舍、宿舍校园网在规划建设中、可自选运营商。
2026-08-18 会议口径：计费范围包括宿舍、只提供无线接入、原则上不允许自建路由器。
只做 upsert / 追加别名，不删除条目。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"

MEETING = "会议纪要-2026-08-18-校园网相关会议内容总结"
GUIDE2022 = "20220922-c8498a199120"
NET2026 = "campus-net-2026"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


TEXTS: dict[str, str] = {}
for sub in ("wendao-text", "wendao-extra", "great", "local", "huibian", "crawl", "cdp",
            "extra", "wechat", "pdf", "chsi", "moe", "national"):
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
    ("有没有",
     "有：按 2026-08-18 校园网会议口径，校园网计费范围包括宿舍和校内，宿舍在校园网覆盖范围内",
     [q(MEETING, "校园网计费范围为校园网覆盖范围，包括宿舍和校内。")]),
    ("怎么连",
     "宿舍只提供无线接入，宿舍面板不提供有线接口；连「Wireless CUC」后，用统一身份认证账号密码完成认证",
     [q(MEETING, "校园网只提供无线接入，宿舍面板不提供有线接口。无线设备之间有隔离。"),
      q("20230221-c8498a202280",
        "校园网已与学校统一身份认证平台联通，师生员工通过统一身份认证平台的账号密码进行网络连接认证")]),
    ("路由器 / 宽带",
     "原则上不允许自建路由器；原有运营商宽带不拆除、可以继续使用，已续费不想继续用的可向运营商申请退费",
     [q(MEETING, "原则上不允许自建路由器。"),
      q(MEETING, "原有宽带不拆除，可以继续使用。已经续费原有宽带，不想继续使用的，可以和运营商申请退费。")]),
    ("旧口径",
     "2022 年新生指南当时写的是：校园无线网已覆盖除学生宿舍外的大部分区域，学生宿舍校园网在规划建设中，"
     "新生入校后可自主选购运营商网络服务",
     [q(GUIDE2022,
        "校园无线网已覆盖除学生宿舍外的大部分区域，包括教学楼、食堂、图书馆等。"
        "学生宿舍校园网在规划建设中，新生入校后可自主选购运营商网络服务。")]),
    ("报修",
     "网络问题可电话报修 65783878，或到线下窗口报修；宿舍网络报修：移动 13911312873、联通 15699840801",
     [q(MEETING, "校园网络出现问题有两个报修途径：电话报修 65783878 和线下窗口报修。"),
      q(GUIDE2022, "宿舍网络报修电话"),
      q(GUIDE2022, "移动：13911312873 联通：15699840801")]),
]

PITFALLS = [
    ("无线设备之间有隔离，宿舍里不同设备之间可能互相访问不了",
     [q(MEETING, "无线设备之间有隔离。")]),
    ("终端数量上限 10 个，超出后会自动退出最早的终端；理由充足可以申请扩容",
     [q(MEETING, "终端数量 10 个，个别不够的可以进行申请，理由充足的可以扩。终端数量超过上限后，会自动退出最早的终端。")]),
    ("带宽每个设备 100；暂时限时下行单个终端 100Mbps，可根据实际情况调整",
     [q(MEETING, "带宽保持每个设备 100。")]),
    ("新生「不建议」安装宽带（会议原文括号注明「不建议那就是能装」），需要时可直接找运营商办理",
     [q(MEETING, '新生"不建议"安装宽带（"不建议"那就是能装，新生不用担心）。')]),
]

ALIASES = [
    "宿舍有wifi吗", "宿舍有没有wifi", "宿舍wifi", "宿舍的wifi", "宿舍wifi怎么连",
    "宿舍有无线网吗", "宿舍有没有无线网", "宿舍无线网", "宿舍无线网怎么连",
    "宿舍有校园网吗", "宿舍有没有校园网", "宿舍能连校园网吗", "宿舍校园网",
    "宿舍校园网怎么连", "宿舍怎么连校园网", "宿舍怎么上网", "宿舍上网",
    "宿舍有网吗", "宿舍能上网吗", "宿舍能不能上网",
    "宿舍宽带", "宿舍能装宽带吗", "宿舍宽带怎么装", "宿舍路由器", "宿舍能装路由器吗",
    "宿舍能装wifi吗", "宿舍能自己装wifi吗", "宿舍网怎么连",
]

item = {
    "id": "it-sushe-wangluo",
    "title": "宿舍有校园网 / WiFi 吗",
    "aliases": ALIASES,
    "keywords": ["wifi", "无线网", "无线", "校园网", "宿舍wifi", "宽带", "路由器", "上网"],
    "dept": "信息化处",
    "channel": ["线上系统", "报修电话"],
    "audience": ["本科生", "研究生"],
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
        {"title": "校园网相关会议内容总结（共同奋斗的结果，2026-08-18）", "url": "",
         "checked": "2026-10-30", "kind": "会议纪要", "published": "2026-08-18"},
        {"title": "访问校园网 · 信息化处",
         "url": "https://its.cuc.edu.cn/2022/0922/c8498a199120/page.htm", "checked": "2026-10-30"},
    ],
    "evidence": {},
    "note": "宿舍是否覆盖两种口径并存：2022 官方页写“规划建设中”，2026-08-18 会议口径写计费范围包括宿舍；按时间较新的会议口径回答，并保留旧口径原文。",
}

for i, (when, what, quotes) in enumerate(STEPS):
    item["steps"].append({"when": when, "what": what})
    item["evidence"][f"steps.{i}"] = ev(*quotes)
for i, (text, quotes) in enumerate(PITFALLS):
    item["pitfalls"].append(text)
    item["evidence"][f"pitfalls.{i}"] = ev(*quotes)

data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
items = data["items"]
by_id = {it["id"]: it for it in items}

if "it-sushe-wangluo" in by_id:
    old = by_id["it-sushe-wangluo"]
    old.update(item)
else:
    idx = next((i for i, it in enumerate(items) if it["id"] == "it-wangluo"), len(items) - 1)
    items.insert(idx + 1, item)

# 三个问法从「连不上」挪到「宿舍有没有网」：排障步骤回答不了覆盖问题
wangluo = by_id["it-wangluo"]
moved = ["宿舍网怎么连", "宿舍怎么上网", "宿舍上网"]
wangluo["aliases"] = [a for a in wangluo["aliases"] if a not in moved]
for a in moved:
    if a not in ALIASES:
        raise SystemExit(f"别名没接住：{a}")

# 2023 页面的「每月赠送 50G、超出限速」已被 2026 计费公告取代（会议纪要也注明旧口径过时）
wangluo["pitfalls"][1] = "2026-11-01 起：每月 50GB 免费基础流量，超出后可自愿选购流量包或包月；超出后限制只能访问校内网络，未用完流量不结转"
wangluo["evidence"]["pitfalls.1"] = ev(
    q(NET2026, "每位用户每月享有50GB免费基础流量，超出后可根据个人使用需求，自愿选购以下流量包"),
    q(NET2026, "流量超出后，限制只能访问校内网络，所有未使用完的当月流量不结转至下月"),
)

(ROOT / "items.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"条目总数 {len(items)}；it-sushe-wangluo 步骤 {len(item['steps'])}，坑 {len(item['pitfalls'])}")
