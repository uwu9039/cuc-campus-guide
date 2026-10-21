"""新增两条：考试与学术违纪处理（2020 版，含废止旧版说明）、辅修报名（2026 招生口径）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}

WJ = "20201124-c6487a176027"      # 考试与学术违纪处理办法（2020，生效版本）
FX = "20250401-c6364a268919"      # 2026 年辅修招生信息

NEW = [
    {
        "id": "kaoshi-weiji",
        "title": "考试与学术违纪处理",
        "aliases": ["考试作弊", "考场上被发现", "学术不端", "抄袭认定", "违纪处分", "替考"],
        "keywords": ["作弊", "违纪", "抄袭", "学术不端", "处分"],
        "dept": "本科生院 / 学生工作部", "channel": ["线下窗口"],
        "audience": ["本科生"], "status": "verified", "confidence": "high",
        "materials": [],
        "steps": [
            {"when": "考试违纪/作弊", "what": "由考试工作人员按纪律处分程序调查取证，填写考场记录单与考试情况调查笔录",
             "where": "考场 → 主管职能部门"},
            {"when": "学术违纪", "what": "由学生所在单位或开课单位按纪律处分管理规定调查取证认定", "where": "学院 / 开课单位"},
        ],
        "fee": None, "location": None, "hours": None, "duration": None, "window": None,
        "pitfalls": [
            "提供虚假学业证明或其他学术水平证明：记过直至开除学籍，证件追回",
            "论文、报告、著作、创作作品被认定抄袭、篡改、伪造：严重警告直至开除学籍",
            "本办法经校长办公会批准，自 2020 年 5 月 1 日起执行，原 2017 年规定同时废止",
        ],
        "slots": [{"key": "kind", "ask": "是考场违纪，还是论文/作品被认定抄袭？", "options": ["考场违纪/作弊", "学术不端"], "required": True,
                   "decides": ["steps"], "why": "两类走的调查主体不同：考场由考试工作人员，学术由学院或开课单位"}],
        "draft": None,
        "source": [{"title": "中国传媒大学学生考试与学术违纪处理办法（中传教字〔2020〕63号，2020-05-01 起执行）",
                    "url": "https://jwc.cuc.edu.cn/2020/1124/c6487a176027/page.htm",
                    "checked": "2026-10-21", "effective": "2020-05-01", "supersedes": "中传教字〔2017〕242号"}],
        "evidence": {
            "steps.0": {"src": WJ, "quote": "由考试工作人员严格按照《中国传媒大学学生纪律处分程序（修订）》中“调查与取证”进行处理"},
            "steps.1": {"src": WJ, "quote": "由学生所在单位或开课单位按照《中国传媒大学学生纪律处分管理规定》"},
            "pitfalls.0": {"src": WJ, "quote": "提供虚假学业证明或其他有关学术水平证明的，视情节轻重情况给予记过直至开除学籍处分，有关证件追回"},
            "pitfalls.1": {"src": WJ, "quote": "经学院或专家小组认定存在抄袭、篡改、伪造等事实的行为，视情节给予严重警告直至开除学籍处分"},
            "pitfalls.2": {"src": WJ, "quote": "自2020年5月1日起执行。原《中国传媒大学学生考试违纪与学术违纪管理规定》（中传教字[2017]242号）同时废止"},
        },
    },
    {
        "id": "fuxiu-baoming",
        "title": "辅修报名",
        "aliases": ["辅修", "报辅修", "辅修专业", "辅修怎么报名"],
        "keywords": ["辅修", "辅修报名", "辅修专业"],
        "dept": "本科生院", "channel": ["线上系统", "线下窗口"],
        "audience": ["本科生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "各专业辅修招生简章（附件）"}, {"name": "辅修报名操作手册——学生版（附件）"}],
        "steps": [
            {"when": "2026 年", "what": "开放 3 个本科专业供辅修，4 月 15 日开启报名系统，4 月 23 日截止", "where": "报名系统"},
            {"when": "录取后", "what": "被录取者于秋季学期开始辅修学习，上课方式见各专业招生简章", "where": "辅修专业"},
        ],
        "fee": None, "location": "线上报名系统", "hours": None, "duration": None,
        "window": "以当年通知为准（2026 年为 4 月 15 日–4 月 23 日）",
        "pitfalls": ["报名方式与课程安排都在各专业招生简章附件里，不看简章容易报错", "招生专业每年不同，别照往年的名单准备"],
        "slots": [],
        "draft": None,
        "source": [{"title": "2026 年辅修招生信息 · 教务处",
                    "url": "https://jwc.cuc.edu.cn/2025/0401/c6364a268919/page.htm",
                    "checked": "2026-10-21"}],
        "evidence": {
            "steps.0": {"src": FX, "quote": "我校于2026年开放3个本科专业供同学们辅修，并于4月15日开启报名系统，4月23日截止"},
            "steps.1": {"src": FX, "quote": "本次被辅修专业录取的同学，将于秋季学期开始辅修学习"},
            "materials.0": {"src": FX, "quote": "详细报名方式、课程安排等信息请参见附件中各专业招生简章"},
            "materials.1": {"src": FX, "quote": "辅修报名操作手册见附件"},
            "location": {"src": FX, "quote": "并于4月15日开启报名系统"},
            "window": {"src": FX, "quote": "4月15日开启报名系统，4月23日截止"},
            "pitfalls.0": {"src": FX, "quote": "详细报名方式、课程安排等信息请参见附件中各专业招生简章"},
        },
    },
]

added = 0
for it in NEW:
    if it["id"] in have:
        continue
    d["items"].append(it)
    added += 1

d["updated"] = "2026-10-21"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增 {added} 条，累计 {len(d['items'])}")
