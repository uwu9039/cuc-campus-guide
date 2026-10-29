"""出国留学 / 交流项目条目：区分校际交流与自费留学，引《制度汇编》原文（带页码）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}

HB_YJS = "hb08f9e95ed1"     # 研究生学籍管理规定（第三十条、三十一条）
HB_KECHENG = "hba17981ab81"  # 本科学生课程置换及学分认定管理办法（试行）
YJS_NUM = "hb08f9e95ed1"
KC_NUM = "hba17981ab81"

SRC = [
    {"title": "中国传媒大学学生工作规章制度汇编 2025 · 研究生学籍管理规定（p.98）",
     "url": "https://xsc.cuc.edu.cn/2023/0904/c2753a259796/page.htm", "checked": "2026-10-27",
     "note": "第三十条、第三十一条"},
    {"title": "中国传媒大学学生工作规章制度汇编 2025 · 本科学生课程置换及学分认定管理办法（试行）（p.135）",
     "url": "https://xsc.cuc.edu.cn/2023/0904/c2753a259796/page.htm", "checked": "2026-10-27",
     "note": "第三条、第四条"},
]

item = {
    "id": "liuxue-jiaoliu",
    "title": "出国留学 / 交流项目（保留学籍、学分认定）",
    "aliases": ["留学", "出国留学", "申请留学", "自费留学", "交流项目", "交换生", "出国交流",
                "境外学习", "留学要准备什么"],
    "keywords": ["留学", "出国", "交流项目", "交换", "境外学习", "保留学籍", "学分认定"],
    "dept": "国际交流与合作处 / 本科生院 / 研究生院", "channel": ["线下窗口", "线上系统"],
    "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
    "materials": [
        {"name": "中英文成绩单"},
        {"name": "在读证明 / 学历学位证明"},
        {"name": "保留学籍审批材料（学籍异动）"},
    ],
    "steps": [
        {"when": "第一步：选路径", "what": "走学校组织或备案的交流项目，还是自费出国留学——这决定学分能不能认",
         "where": "国际交流与合作处"},
        {"when": "因公（校际交流 / 联合培养）", "what": "出国（境）前办理保留学籍手续，在外学习时间计入学习年限", "where": "研究生院"},
        {"when": "因私（自费留学）", "what": "出国（境）前同样要办保留学籍，但在外学习时间不计入学习年限", "where": "研究生院"},
        {"when": "办保留学籍", "what": "走学籍异动审批，经导师和所在培养单位同意，报研究生院审核批准；以学期为单位",
         "where": "导师 → 培养单位 → 研究生院"},
        {"when": "回国/返校后", "what": "按学校规定办理复学；交流课程申请置换或学分认定", "where": "本科生院 / 研究生院"},
    ],
    "fee": None,
    "location": "国际交流与合作处 / 本科生院 / 研究生院",
    "hours": None, "duration": None, "window": None,
    "pitfalls": [
        "未经国际交流与合作处或本科生院批准、自己联系的自费项目，课程和学分一律不予置换或认定",
        "因私出国留学的时间不计入学习年限，因公才算",
        "因私出国留学期间，原则上不具备研究生国家奖学金参评资格",
        "保留学籍要导师和培养单位同意、研究生院批准，不是自己写个申请就行",
    ],
    "slots": [
        {"key": "kind", "ask": "你是走校际交流/联合培养，还是自费出国留学？", "required": True,
         "options": ["校际交流 / 联合培养（因公）", "自费出国留学（因私）"],
         "decides": ["steps", "pitfalls"],
         "why": "只有经批准的项目学分才认；且因私的时间不计入学习年限"},
        {"key": "who", "ask": "你是本科生还是研究生？", "required": False,
         "options": ["本科生", "研究生"], "decides": ["steps"],
         "why": "研究生走研究生院审批，本科生的学分认定走本科生院"},
    ],
    "draft": None,
    "source": SRC,
    "evidence": {
        "steps.1": {"src": HB_YJS, "quote": "经批准因公出国（境）联合培养或执行合作科研任务，出国（境）前须办理保留学籍手续，在外学习时间计入学习年限"},
        "steps.2": {"src": HB_YJS, "quote": "在校学习期间办理因私出国（境）留学，出国（境）前须办理保留学籍手续，在外学习时间不计入学习年限"},
        "steps.3": {"src": HB_YJS, "quote": "研究生保留学籍应办理学籍异动审批手续，经导师和所在培养单位同意，报研究生院审核批准"},
        "steps.4": {"src": HB_KECHENG, "quote": "学生参加由学校国际交流与合作处组织或备案的境（内）外交流学期项目所修读的课程"},
        "pitfalls.0": {"src": HB_KECHENG, "quote": "未经国际交流与合作处或本科生院批准，学生自行联系并参加的境（内）外交流项目或自费赴境（内）外大学学习，所修读课程及学分不予置换或认定"},
        "pitfalls.1": {"src": HB_YJS, "quote": "在外学习时间不计入学习年限"},
        "pitfalls.3": {"src": HB_YJS, "quote": "经导师和所在培养单位同意，报研究生院审核批准"},
        "materials.2": {"src": HB_YJS, "quote": "出国（境）前须办理保留学籍手续"},
    },
    "advisory": [
        "选校、文书、语言考试这些「策略」不在学校文件里，我只能给流程与材料；具体项目清单问国际交流与合作处",
        "签约前先确认项目是否在学校备案——这是学分能不能认的唯一分界线",
    ],
}

if item["id"] not in have:
    d["items"].append(item)
    d["updated"] = "2026-10-27"
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"新增出国留学条目，共 {len(d['items'])} 条")
else:
    print("已存在")
