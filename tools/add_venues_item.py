"""把《位置文档》（教育服务中心答疑）做成「校园场馆在哪」条目。

来源：sources/wendao-text/c497abf6.txt，逐句核对后写入 evidence.answer。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "wendao-text" / "c497abf6.txt"

LINES = [
    "XR 演播室位于25 号楼一层。",
    "中传演播馆位于2 号楼A 座2 层，您可以从中传学术中心入口（2 号楼西门）进入。",
    "手球馆/羽毛球馆位于学校的东北角，您可以从游泳馆北侧的地下通道进入。",
    "中传礼堂/中传讲堂/1500 人报告厅/400 人报告厅/1500 报/400 报位于国重大楼的一层。",
    "400 报/小讲堂位于国重大楼的一层。",
    "1500 报/大报告厅/大报位于国重大楼的一层。",
    "25 号楼210 报告厅在25 号楼南侧2 层。您可以通过25 号楼外侧白色楼梯到达210 报告厅。",
    "艺术展览中心位于南操场西边，艺术与传播大楼（新建）的南边。",
    "大学生活动中心是55 号楼，位于学校东侧。",
]
PITFALLS = [
    "D5 演播馆不属于教育服务中心管辖范围。建议您在校园地图中查找。",
]

VENUES = [
    "中传礼堂", "中传讲堂", "1500报", "400报", "1500人报告厅", "400人报告厅",
    "大报告厅", "大报", "小讲堂", "中传演播馆", "1400演播馆", "1400平米演播馆",
    "XR演播馆", "手球馆", "羽毛球馆", "新利体育馆", "艺术展览中心", "艺展中心",
    "大学生活动中心", "大活", "25号楼210报告厅", "210报告厅",
]


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    body = squash(text)
    for one in LINES + PITFALLS:
        assert squash(one) in body, f"原文里找不到：{one}"

    aliases = []
    for v in VENUES:
        for suf in ("在哪", "在哪里", "位置", "怎么走"):
            a = v + suf
            if a not in aliases:
                aliases.append(a)

    item = {
        "id": "campus-changguan-weizhi",
        "title": "校园场馆在哪（礼堂 / 讲堂 / 演播馆 / 手球馆 / 艺展中心）",
        "aliases": aliases,
        "keywords": ["场馆位置"],
        "dept": "教育服务中心",
        "channel": ["线上"],
        "audience": "全校师生",
        "status": "verified",
        "confidence": "high",
        "materials": [],
        "steps": [],
        "pitfalls": PITFALLS,
        "location": "",
        "hours": "",
        "fee": "",
        "duration": "",
        "window": "",
        "draft": "",
        "answer": "；".join(LINES),
        "source": [
            {
                "label": "校园场馆位置（教育服务中心 · 位置文档）",
                "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=c497abf6d4d5447b9e5f46b8f08de183",
            }
        ],
        "evidence": {
            "answer": [{"src": "c497abf6", "quote": one} for one in LINES],
            "pitfalls.0": {"src": "c497abf6", "quote": PITFALLS[0]},
        },
    }

    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["items"] = [i for i in data["items"] if i["id"] != item["id"]] + [item]
    data["updated"] = "2026-10-29"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("已写入条目 campus-changguan-weizhi，别名", len(aliases), "条")


if __name__ == "__main__":
    main()
