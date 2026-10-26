"""国家级学生政策条目：转学（跨校）、学生申诉。

原文来自教育部《普通高等学校学生管理规定》（教育部令第 41 号），
来源标注为「教育部 · 普通高等学校学生管理规定（第41号令）」。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
have = {i["id"] for i in d["items"]}

MOE = "moe-41"
SRC = [{"title": "普通高等学校学生管理规定（教育部令第41号，2017-09-01 施行）",
        "url": "http://www.moe.gov.cn/srcsite/A02/s5911/moe_621/201702/t20170216_296385.html",
        "checked": "2026-10-26", "effective": "2017-09-01"}]

ITEMS = [
    {
        "id": "moe-zhuanxue",
        "title": "转学（跨校转学）",
        "aliases": ["转学", "换学校", "转到别的学校", "跨校转学", "想转去其他大学"],
        "keywords": ["转学", "转校", "跨校", "换学校"],
        "dept": "学生所在学校 / 拟转入学校（依据教育部 41 号令）", "channel": ["线下窗口"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "转学申请（说明理由）"}, {"name": "相关证明材料"}],
        "steps": [
            {"when": "第一步", "what": "学生本人提出申请并说明理由", "where": "所在学校"},
            {"when": "第二步", "what": "所在学校与拟转入学校均同意，由转入学校审核转学条件及相关证明", "where": "两校"},
            {"when": "第三步", "what": "拟转入学校认为符合培养要求且有培养能力，经校长办公会或专题会议研究决定", "where": "拟转入学校"},
            {"when": "研究生", "what": "还应当经拟转入专业导师同意", "where": "拟转入专业"},
        ],
        "fee": None, "location": "两校学籍管理部门", "hours": None, "duration": None, "window": None,
        "pitfalls": [
            "因病或有特殊困难、无法继续在本校学习或不适应本校学习要求的，才可以申请转学",
            "以特殊招生形式录取的学生，国家有相关规定或录取前与学校有明确约定的，不得转专业",
            "转学必须两校都同意，单方同意办不成",
        ],
        "slots": [],
        "draft": None,
        "source": SRC,
        "evidence": {
            "steps.0": {"src": MOE, "quote": "第二十三条 学生转学由学生本人提出申请，说明理由"},
            "steps.1": {"src": MOE, "quote": "经所在学校和拟转入学校同意，由转入学校负责审核转学条件及相关证明"},
            "steps.2": {"src": MOE, "quote": "经学校校长办公会或者专题会议研究决定，可以转入"},
            "steps.3": {"src": MOE, "quote": "研究生转学还应当经拟转入专业导师同意"},
            "pitfalls.0": {"src": MOE, "quote": "因患病或者有特殊困难、特别需要，无法继续在本校学习或者不适应本校学习要求的，可以申请转学"},
            "pitfalls.1": {"src": MOE, "quote": "以特殊招生形式录取的学生，国家有相关规定或者录取前与学校有明确约定的，不得转专业"},
            "pitfalls.2": {"src": MOE, "quote": "经所在学校和拟转入学校同意"},
            "materials.0": {"src": MOE, "quote": "学生转学由学生本人提出申请，说明理由"},
        },
        "advisory": ["跨校转学极难，多数情况应优先考虑校内转专业；两者依据不同文件"],
    },
    {
        "id": "moe-shensu",
        "title": "学生申诉（对处分/处理决定不服）",
        "aliases": ["申诉", "处分不服", "被处分了怎么办", "学生申诉委员会", "对处分有异议"],
        "keywords": ["申诉", "处分不服", "有异议", "申诉委员会"],
        "dept": "学校学生申诉处理委员会（依据教育部 41 号令）", "channel": ["线下窗口"],
        "audience": ["本科生", "研究生"], "status": "verified", "confidence": "high",
        "materials": [{"name": "书面申诉"}, {"name": "学校处理或处分决定书"}],
        "steps": [
            {"when": "收到决定书起 10 日内", "what": "向学校学生申诉处理委员会提出书面申诉", "where": "学生申诉处理委员会"},
        ],
        "fee": None, "location": "学校学生申诉处理委员会", "hours": None,
        "duration": None, "window": "接到处理或处分决定书之日起 10 日内",
        "pitfalls": ["超过 10 日再提，可能不被受理", "处分决定书里应当写明申诉的途径和期限"],
        "slots": [],
        "draft": None,
        "source": SRC,
        "evidence": {
            "steps.0": {"src": MOE, "quote": "可以在接到学校处理或者处分决定书之日起10日内，向学校学生申诉处理委员会提出书面申诉"},
            "window": {"src": MOE, "quote": "接到学校处理或者处分决定书之日起10日内"},
            "pitfalls.0": {"src": MOE, "quote": "接到学校处理或者处分决定书之日起10日内"},
            "pitfalls.1": {"src": MOE, "quote": "（四）申诉的途径和期限"},
            "materials.0": {"src": MOE, "quote": "提出书面申诉"},
        },
        "advisory": ["校内申诉只针对处分/处理决定；对学籍处理（如退学）同样适用"],
    },
]

added = 0
for it in ITEMS:
    if it["id"] in have:
        continue
    d["items"].append(it)
    added += 1
d["updated"] = "2026-10-26"
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增 {added} 条国家级政策条目，共 {len(d['items'])} 条")
