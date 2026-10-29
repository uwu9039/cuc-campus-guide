"""把官方校园地图文档解析成 POI 清单，供地图面板与“XX 在哪”问答使用。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "wendao-text"


def clean_name(s: str) -> str:
    s = re.sub(r"^\d+、", "", s.strip())
    s = re.sub(r"的位置$", "", s)
    return s.strip()


def kind_of(name: str, place: str) -> str:
    if any(k in name for k in ("医院", "驿站", "服务大厅", "食堂", "餐厅")):
        return "服务"
    if "实验室" in name:
        return "实验室"
    if any(k in name for k in ("学院", "研究院", "学部")):
        return "学院"
    if any(k in name for k in ("馆", "厅", "场", "中心")):
        return "场馆"
    if any(k in name for k in ("处", "办公室", "部", "委", "室")):
        return "机关"
    if place:
        return "楼宇"
    return "其他"


def main() -> None:
    text = (SRC / "1b97d899.txt").read_text(encoding="utf-8")
    pattern = re.compile(r"([^\n]{2,60}?)的位置\(办公地点\)：\s*\n?\s*位于([^\n]+)")
    pois = []
    for raw_name, place in pattern.findall(text):
        name = clean_name(raw_name)
        place = place.strip().rstrip("。")
        pois.append(
            {
                "name": name,
                "place": place,
                "kind": kind_of(name, place),
                "src": "1b97d899",
                "amap": f"https://uri.amap.com/search?keyword={quote('中国传媒大学' + name)}&city=北京",
            }
        )

    # 简称与楼宇别名（来自官方简称对照表）
    alias = {
        "立德楼": ["1教", "一教"],
        "博学楼": ["48教", "四十八教"],
        "中传礼堂": ["1500报", "大报告厅", "大礼堂"],
        "中传讲堂": ["400报", "小讲堂"],
        "中传演播馆": ["1400平米演播室", "4K演播馆"],
        "手球馆": ["羽毛球馆", "新利体育馆"],
        "游泳馆": ["游泳池", "水立方"],
        "大学生活动中心": ["大活", "活动中心"],
        "操场": ["风雨操场", "南操场", "田径场"],
        "艺术展览中心": ["艺展中心"],
        "2号楼": ["明德楼"],
        "22号楼": ["国重大楼"],
        "27号楼": ["艺术与传播大楼"],
        "20号楼": ["原幼儿园", "校医院"],
    }
    for p in pois:
        for full, als in alias.items():
            if p["name"] == full or p["place"].startswith(full):
                p["aliases"] = als
                break

    extras = [
        {
            "name": "校医院",
            "place": "20号楼（原幼儿园）",
            "kind": "服务",
            "src": "1b97d899",
            "amap": f"https://uri.amap.com/search?keyword={quote('中国传媒大学校医院')}&city=北京",
        },
        {
            "name": "校内菜鸟驿站",
            "place": "临建1（47号楼东侧，44号楼北侧）",
            "kind": "服务",
            "src": "1b97d899",
            "amap": f"https://uri.amap.com/search?keyword={quote('中国传媒大学菜鸟驿站')}&city=北京",
        },
        {
            "name": "学生服务大厅（校园卡管理中心）",
            "place": "艺术与传播大楼1层",
            "kind": "服务",
            "src": "252a96fb",
            "amap": f"https://uri.amap.com/search?keyword={quote('中国传媒大学学生服务大厅')}&city=北京",
        },
    ]
    seen = {p["name"] for p in pois}
    pois.extend(x for x in extras if x["name"] not in seen)

    out = {
        "updated": "2026-10-29",
        "center": {"name": "中国传媒大学", "lng": 116.5536, "lat": 39.9137},
        "note": "坐标只用于地图定位，楼内位置以 place 字段的官方原文为准。",
        "count": len(pois),
        "pois": pois,
    }
    (ROOT / "sources" / "campus-pois.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"校园 POI {len(pois)} 条 → sources/campus-pois.json")


if __name__ == "__main__":
    main()
