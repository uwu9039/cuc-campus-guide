"""修两处：毕业条目关键词收窄；拆出「复学」独立条目。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))
XJ = "xueji-2025"

for it in d["items"]:
    if it["id"] == "xueji-biye":
        # 「毕业证明书」这类词不该被毕业条目吸走
        it["keywords"] = ["结业", "毕业条件", "毕业证书"]
        it.pop("evidence", None) if False else None
    if it["id"] == "xueji-xiuxue":
        # 复学拆出去，休学条目不再带复学步骤
        it["steps"] = [s for s in it["steps"] if s["when"] != "复学"]
        it["evidence"].pop("steps.4", None)

fuxue = {
    "id": "xueji-fuxue",
    "title": "复学",
    "aliases": ["复学", "休学期满", "怎么回来上课", "病好了要复学", "复学手续"],
    "keywords": ["复学", "复学申请", "复学手续"],
    "dept": "学院 / 校医院 / 本科生院",
    "channel": ["线下窗口"],
    "audience": ["本科生"],
    "status": "verified",
    "confidence": "high",
    "materials": [
        {"name": "「可以正常学习」的诊断证明（因病休学复学时）"},
    ],
    "steps": [
        {"when": "时限", "what": "休学或保留学籍期满，原则上在新学期开学后两周内提出复学申请", "where": "学院"},
        {"when": "第 1 步", "what": "复学申请经所在学院审核，报本科生院和学校主管领导批准", "where": "学院 → 本科生院"},
        {"when": "第 2 步", "what": "因病休学的，须附二级甲等以上医院（含精神专科医院）「可以正常学习」的诊断证明，并经校医院复查合格", "where": "校医院"},
        {"when": "编入年级", "what": "按已修课程情况编入原专业相应年级；自费出国留学的须降入下一年级", "where": "学院"},
    ],
    "fee": None,
    "location": "学院 → 校医院 → 本科生院",
    "hours": None,
    "duration": None,
    "window": "休学或保留学籍期满后，新学期开学两周内提出",
    "pitfalls": [
        "逾期未提出复学申请，或复学申请审批不合格，可予退学处理",
        "伪造诊断证明或复查不合格者不得复学",
    ],
    "slots": [],
    "draft": None,
    "source": [{"title": "中国传媒大学本科生学籍管理规定（中传教字〔2025〕195号）",
                "url": "（本地文件，未入库）",
                "checked": "2026-10-21", "kind": "pdf"}],
    "evidence": {
        "steps.0": {"src": XJ, "quote": "学生原则上应在新学期开学后两周之内提出复学申请"},
        "steps.1": {"src": XJ, "quote": "复学申请须经学生所在学院审核，本科生院和学校主管领导批准"},
        "steps.2": {"src": XJ, "quote": "须同时附二级甲等以上医院（含精神专科医院）开具的“可以正常学习”的诊断证明，经校医院复查合格"},
        "steps.3": {"src": XJ, "quote": "自费出国留学的学生复学后须降入下一年级相关专业继续学习"},
        "materials.0": {"src": XJ, "quote": "开具的“可以正常学习”的诊断证明"},
        "location": {"src": XJ, "quote": "复学申请须经学生所在学院审核，本科生院和学校主管领导批准"},
        "window": {"src": XJ, "quote": "学生原则上应在新学期开学后两周之内提出复学申请"},
        "pitfalls.0": {"src": XJ, "quote": "逾期未提出复学申请或者申请审批不合格的，可予退学处理"},
        "pitfalls.1": {"src": XJ, "quote": "伪造诊断证明或复查不合格者不得复学"},
    },
}

if not any(i["id"] == "xueji-fuxue" for i in d["items"]):
    d["items"].append(fuxue)
    print("新增：复学")

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print("条目总数：", len(d["items"]))
