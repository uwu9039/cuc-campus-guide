"""补录「调课」服务条目（内容出自 2014 年调课管理办法附件）。

只做 upsert，不删除任何已有条目。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
TEXT = (SRC / "attachments" / "text" / "att-1958c58b91.txt").read_text(encoding="utf-8")
SQUASHED = re.sub(r"\s+", "", TEXT)
SRC_ID = "att-1958c58b91"
SOURCE = {
    "title": "中国传媒大学本科生课程调课管理办法（中传教字〔2014〕118 号）",
    "url": "https://jwc.cuc.edu.cn/_upload/article/files/07/ae/1e8b47124898826a77d38cbf4354/8dccc906-e7ed-4147-84dc-b0823a85be3d.pdf",
    "checked": "2026-10-30",
}

STEPS = [
    ("常规", "教师须按课程表所排定的时间和地点上课。当课程授课时间、地点或任课教师任一项因故发生变化，则均需提前办理调课手续。"),
    ("提前量", "原则上任课教师应提前至少 1 个工作日填写《中国传媒大学调课单》，详细写明调课原因（请附相关证明），申请调课的同时应写明补课方式和时间安排。"),
    ("紧急情况", "如因紧急情况不能提前办理调课手续者，需由学部（院）第一时间口头报备教务处，并应在一个工作日内补办调课手续。"),
    ("审批", "申请调课时由任课教师报送申请表至学部（院），学部（院）主管教学领导审批后由开课学部（院）教学秘书至教务处进行手续办理，并将《中国传媒大学调课公布单》送至相应教学楼，申请表将由教务处留存备案。"),
    ("通知", "审批后的调课信息应由开课学部（院）教学秘书负责通知任课教师和学生。教务处将通过教学楼大屏幕向学生公布调课信息。"),
    ("公共选修课", "公共选修课的授课对象为全校各专业学生，为确保通知到位，应至少提前一周办理调课手续，调课手续办理完成后，将由教务处在教务处主页、教务在线登陆界面以及教学楼大屏幕发布调课信息公告。"),
    ("教室设备故障", "如因教室设备故障影响课程授课而需调课者，应第一时间告知教室管理科，如短期内确无法维修，则需教室管理科在调课单签字确认后方可进行调课。"),
]

PITFALLS = [
    "未经学部（院）和教务处批准，擅自变更主讲教师/擅自变更课程表安排的上课时间和地点的，按教学事故处理。",
    "任课教师如因紧急情况暂停课程时间超过 3 周者，学部（院）应安排其他教师临时代为授课。",
]

MATERIAL = "《中国传媒大学调课单》"


def main() -> None:
    for _, what in STEPS:
        assert re.sub(r"\s+", "", what) in SQUASHED, what[:40]
    for p in PITFALLS:
        assert re.sub(r"\s+", "", p) in SQUASHED, p[:40]
    assert MATERIAL in SQUASHED

    ev: dict[str, dict] = {}
    steps = []
    for i, (when, what) in enumerate(STEPS):
        ev[f"steps.{i}"] = {"src": SRC_ID, "quote": what}
        steps.append({"when": when, "what": what})
    for i, p in enumerate(PITFALLS):
        ev[f"pitfalls.{i}"] = {"src": SRC_ID, "quote": p}
    ev["materials.0"] = {"src": SRC_ID, "quote": MATERIAL}

    item = {
        "id": "jwc-tiaoke",
        "title": "调课（老师改上课时间 / 地点 / 代课）",
        "aliases": [
            "调课", "老师调课", "调课怎么办", "调课流程", "怎么调课",
            "调课要提前多久", "老师不来上课", "停课", "代课", "补课",
            "调课单", "调课公布单",
        ],
        "keywords": ["调课", "停课", "代课", "补课", "调课单", "调课公布单"],
        "dept": "教务处 / 本科生院",
        "channel": ["线下"],
        "audience": ["本科生"],
        "status": "verified",
        "confidence": "high",
        "materials": [{"name": MATERIAL}],
        "steps": steps,
        "fee": None,
        "location": None,
        "hours": None,
        "duration": None,
        "window": None,
        "pitfalls": PITFALLS,
        "contact": None,
        "slots": [],
        "draft": None,
        "answer": None,
        "kind": "service",
        "source": [SOURCE],
        "evidence": ev,
    }

    path = ROOT / "items.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"]
    for idx, old in enumerate(items):
        if old.get("id") == item["id"]:
            items[idx] = item
            print("已存在，覆盖更新：", item["id"])
            break
    else:
        items.append(item)
        print("新增：", item["id"], "总计", len(items), "条")
    data["updated"] = "2026-10-30"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
