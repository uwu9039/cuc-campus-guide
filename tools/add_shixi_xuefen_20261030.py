"""补录「实习要求与实习学分」条目，正文取自 534a4add（本科学生实习工作暂行规定）。

实习证明的开具在公开制度里查不到，条目只答实习安排、学分与成绩，缺的部分写进 scope_note。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "items.json"
SRC_ID = "534a4add"

STEPS = [
    ("安排", "除毕业实习外，集中实习一般安排在夏季学期进行；毕业实习由各学院根据专业特点安排在 7、8 学期，一般需安排 1.5—2 个月",
     "除毕业实习外，集中实习一般安排在夏季学期进行", "学院"),
    ("学分", "按《实习计划》完成各类实习任务，经考试或考查后综合评定成绩合格者，获得相应学分",
     "学生按照《实习计划》完成各类实习任务，经考试或考查后综合评定成绩合格者，获得相应学分", "学院 / 教务处"),
    ("不及格", "未参加实习或实习成绩不及格者需再修，再修可在假期或毕业后一年内进行，经考核合格后按学籍管理办法处理",
     "未参加实习或实习成绩不及格者需再修。再修可在假期或毕业后一年内进行，经考核合格后按学籍管理办法处理", "学院"),
    ("成绩构成", "实习成绩由考核成绩和平时表现两部分组成，平时表现包括遵守纪律情况、考核意见和学生的实习笔记等，所占比例不超过 30%",
     "实习的成绩评定，由考核成绩和平时表现两部分组成", "学院"),
    ("请假", "因病、因故不能参加实习者，要有医院证明或书面陈述报告，向学院办理请假手续；实习期间请假应经指导教师同意，未经批准不得擅离实习单位；无故缺课达三分之一者，不予评定实习成绩",
     "因病、因故不能参加实习者，要有医院证明或书面陈述报告，向学院办理请假手续", "学院"),
]

item = {
    "id": "shixi-xuefen",
    "title": "实习要求与实习学分",
    "dept": "教务处 / 学院",
    "channel": ["线下窗口"],
    "audience": ["本科生"],
    "status": "verified",
    "confidence": "high",
    "materials": [{"name": "医院证明或书面陈述报告（因病、因故不能参加实习时）"}],
    "steps": [{"when": w, "what": what, "where": loc} for w, what, _quote, loc in STEPS],
    "fee": None,
    "location": "学院教务 / 教务处",
    "hours": None,
    "duration": None,
    "window": None,
    "pitfalls": ["实习成绩评定原则上应呈正态分布，严格控制优秀成绩的比例，一般不超过 20%，优良率不超过 65%"],
    "slots": [],
    "draft": None,
    "scope_note": "官方公开的实习规定只写了实习学分与成绩怎么算，没有写实习证明由哪个部门开具，这一项需要问学院教务",
    "source": [{
        "title": "中国传媒大学本科学生实习工作暂行规定（修订）",
        "url": "https://aihub.cuc.edu.cn/doc/view/fileview?fileId=534a4addd913433bba6bde3d8097e920",
        "checked": "2026-10-30",
    }],
    "aliases": ["实习学分", "实践学分", "实习成绩", "实习考核", "实习再修", "实习要求"],
    "keywords": ["实习", "实习计划", "实践学分", "实习成绩"],
    "exclude": ["受伤", "急诊", "报销", "保险", "住宿", "工资", "劳动", "合同", "招聘"],
    "evidence": {
        "materials.0": {"src": SRC_ID, "quote": "要有医院证明或书面陈述报告"},
        "location": {"src": SRC_ID, "quote": "校级实习管理由教务处负责"},
        "pitfalls.0": {"src": SRC_ID, "quote": "学生实习成绩评定原则上应呈正态分布，严格控制优秀成绩的比例，一般不超过20%，优良率不超过65%"},
    },
}
for i, (_w, _what, quote, _loc) in enumerate(STEPS):
    item["evidence"][f"steps.{i}"] = {"src": SRC_ID, "quote": quote}

data = json.loads(PATH.read_text(encoding="utf-8"))
data["items"] = [it for it in data["items"] if it["id"] != item["id"]] + [item]
PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("upsert", item["id"], "条目数", len(data["items"]))