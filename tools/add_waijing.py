"""境外交流条目：申请条件、办理程序、学分认定、成绩转换、收费。

原文来自《中国传媒大学本科学生境外交流学习管理规定（修订）》，
引文直接从语料里按句提取，保证逐字一致。
"""
import json
import pathlib
import re

ROOT = pathlib.Path("D:/DSH/智能体节")
idx = json.loads((ROOT / "sources/extra-index.json").read_text(encoding="utf-8"))
slug = next(k for k, v in idx.items() if "境外交流" in v["title"])
body = (ROOT / "sources" / "extra" / f"{slug}.txt").read_text(encoding="utf-8")


def grab(anchor: str, limit: int = 120) -> str:
    """从原文里抠一句：从 anchor 开始，到句号/分号为止，保持逐字。"""
    i = body.find(anchor)
    if i < 0:
        raise SystemExit(f"找不到锚点：{anchor}")
    seg = body[i:i + limit]
    m = re.split(r"[。；\n]", seg, maxsplit=1)
    return m[0].strip()


Q = {
    "cond": grab("（二）学生在校学习时间满一年"),
    "proc1": grab("（一）学生在申请境外学习之前"),
    "proc2": grab("（二）所在学部/直属学院集中组织"),
    "proc3": grab("学生赴境外交流学习时间超过一学期"),
    "credit1": grab("（四）学生回国后，应及时办理复学手续"),
    "credit2": grab("（五）学生因在境外学习而错过的本专业培养计划中的专业核心课"),
    "grade": grab("境外大学的课程成绩由等级分换算为我校百分制成绩的标准为"),
    "fee1": grab("（一）属于对方收费的交流项目"),
    "fee2": grab("（二）属于免交学费的交流项目"),
    "ban": grab("（一）凡我校在读本科生，经学校批准"),
}

item = {
    "id": "waijing-jiaoliu",
    "title": "境外交流学习（申请、学分认定、成绩转换、收费）",
    "aliases": ["境外交流", "出国交换", "交流学习", "交换生申请", "学分互认", "境外成绩转换"],
    "keywords": ["境外交流", "交流学习", "学分互认", "成绩转换", "交换生"],
    "dept": "国际交流与合作处 / 教务处", "channel": ["线下窗口", "线上系统"],
    "audience": ["本科生"], "status": "verified", "confidence": "high",
    "materials": [
        {"name": "《中国传媒大学本科生境内外交流申请表》"},
        {"name": "《中国传媒大学本科生境外交流学习承诺书》"},
        {"name": "境外大学正式成绩单与课程简介（原始与复印件各一份）"},
        {"name": "《中国传媒大学本科生境内外交流访学修读课程认定申请表》（一式两份）"},
    ],
    "steps": [
        {"when": "申请前", "what": "先了解对方学校课程设置，对照本专业教学计划安排学习；向学部/学院主管教学领导提交学习计划",
         "where": "所在学部 / 直属学院"},
        {"when": "获批后", "what": "填写交流申请表与承诺书，签字盖章交教务处备案，并办理退课手续", "where": "教务处"},
        {"when": "超过一学期", "what": "赴境外交流超过一学期（含一学期）的，需办理保留学籍手续", "where": "教务处"},
        {"when": "报送审批", "what": "学部/学院集中报送国际交流部审批，获准后报教务处备案", "where": "国际交流部"},
        {"when": "回国后", "what": "先办复学，再登录教务在线「学分互认」模块填报课程与成绩，经学院审核后交纸质表到教务处终审",
         "where": "教务在线 / 教务处"},
    ],
    "fee": "对方收费项目按 60% 收取我校学费；免学费项目全额上交我校学费；互换奖学金项目按协议",
    "location": "国际交流与合作处 / 教务处", "hours": None, "duration": None, "window": None,
    "pitfalls": [
        "未经学校事先审批自主到境外大学学习的，学分不予认定",
        "境外没有对应课程的专业核心课，必须回国补修且合格才能毕业",
        "成绩转换按等级：A=95、B=85、C=75、D=65（A+、A- 均按 95 算）",
    ],
    "slots": [],
    "draft": None,
    "source": [{"title": "中国传媒大学本科学生境外交流学习管理规定（修订）",
                "url": idx[slug].get("url", ""), "checked": "2026-10-27"}],
    "evidence": {
        "steps.0": {"src": slug, "quote": Q["proc1"]},
        "steps.1": {"src": slug, "quote": Q["proc1"]},
        "steps.2": {"src": slug, "quote": Q["proc3"]},
        "steps.3": {"src": slug, "quote": Q["proc2"]},
        "steps.4": {"src": slug, "quote": Q["credit1"]},
        "fee": {"src": slug, "quote": Q["fee1"]},
        "pitfalls.0": {"src": slug, "quote": Q["ban"]},
        "pitfalls.1": {"src": slug, "quote": Q["credit2"]},
        "pitfalls.2": {"src": slug, "quote": Q["grade"]},
        "materials.2": {"src": slug, "quote": Q["credit1"]},
    },
    "advisory": ["《修学指南》是新生手册，不上官网正文；具体项目清单问国际交流与合作处"],
}

p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
if any(i["id"] == item["id"] for i in d["items"]):
    print("已存在")
else:
    d["items"].append(item)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"新增境外交流条目，共 {len(d['items'])} 条")
    for k, v in Q.items():
        print(f"  {k}: {v[:56]}")
