"""校园楼宇位置速查：来自官方校园地图文档 + 简称对照表，同时修正校医院位置证据。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def verify(src: str, quote: str) -> None:
    coll, stem = src.split("/")
    text = squash((ROOT / "sources" / coll / f"{stem}.txt").read_text(encoding="utf-8"))
    assert squash(quote) in text, f"引文不在原文: {src} :: {quote[:60]}"


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = data["items"]
    by_id = {it["id"]: it for it in items}

    evidence_sources = [
        ("1b97d899", "校园地图官网：https://www.cuc.edu.cn/tsxy/list.htm"),
        ("1b97d899", "校医院的位置(办公地点)：\n位于校内20号楼（原幼儿园）"),
        ("1b97d899", "招生处的位置(办公地点)：\n位于主楼3层"),
        ("1b97d899", "位于2号楼（明德楼）9层913，914"),
        ("1b97d899", "位于22号楼（国重大楼）地下一层A102"),
        ("1b97d899", "位于27号楼（艺术与传播大楼）5层西侧509室"),
        ("cd72bce4", "立德楼\n立德楼=1 教=一教\n博学楼\n博学楼=48 教=四十八教"),
    ]
    for src, quote in evidence_sources:
        verify("wendao-text/" + src, quote)

    answer = (
        "校园地图官网：https://www.cuc.edu.cn/tsxy/list.htm。"
        "名称对应：立德楼 = 1教 = 一教；博学楼 = 48教 = 四十八教；2号楼 = 明德楼；"
        "22号楼 = 国重大楼；27号楼 = 艺术与传播大楼。"
        "常用地点：校医院位于校内20号楼（原幼儿园）；招生处位于主楼3层；"
        "信息化处办公室位于25号楼3层，学生服务大厅（校园卡管理中心）位于艺术与传播大楼1层。"
    )

    item = {
        "id": "campus-louming",
        "title": "校园楼宇名称与位置速查（一教 / 48教 / 明德楼 / 国重大楼）",
        "aliases": [
            "校园地图",
            "楼宇名称",
            "明德楼",
            "国重大楼",
            "艺术与传播大楼",
            "主楼",
            "校医院在哪",
            "招生处在哪",
            "教学楼叫什么",
            "楼号",
        ],
        "keywords": [],
        "dept": "校园地图",
        "channel": ["线上"],
        "audience": ["本科生", "研究生", "教职工"],
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
        "slots": [],
        "draft": None,
        "answer": answer,
        "kind": "service",
        "source": [
            {
                "title": "校园地图（附教学楼名称）· 问道中传",
                "url": "https://www.cuc.edu.cn/tsxy/list.htm",
                "checked": "2026-10-29",
            }
        ],
        "evidence": {
            "answer": {
                "sources": [{"src": s, "quote": q} for s, q in evidence_sources]
            }
        },
    }

    if "campus-louming" in by_id:
        items[items.index(by_id["campus-louming"])] = item
    else:
        items.append(item)

    xyy = by_id["xyy-jiuzhen"]
    xyy["location"] = "校内20号楼（原幼儿园）"
    xyy["evidence"]["location"] = {
        "src": "1b97d899",
        "quote": "校医院的位置(办公地点)：\n位于校内20号楼（原幼儿园）",
    }

    data["updated"] = "2026-10-29"
    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"新增校园楼宇速查 1 条，更新校医院位置；总计 {len(items)} 条")


if __name__ == "__main__":
    main()
