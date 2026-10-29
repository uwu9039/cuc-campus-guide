"""把问道《QA知识模板》逐条转成条目（answer 字段存官方原答复）。

用法：python tools/import_qa_template.py
"""
import json
import re
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
SRC = ROOT / "sources" / "wendao-text" / "18fe5c7d.txt"

DEPT_RULES = [
    (r"校园卡|畅课|教务系统无法登录|信息化|统一身份", "信息化处"),
    (r"户口|户籍", "保卫处"),
    (r"交换项目|出国|留学", "国际交流与合作处"),
    (r"实验室", "实验室与设备管理处"),
    (r"评教", "评估督导部门"),
    (r"教室|报告厅|场馆", "教育服务中心"),
    (r"学生证|勤工|奖学金|助学金|困难补助|综测|请假|心理", "学生工作部"),
    (r"体育|体测|四六级|成绩单|在读证明|毕业证|学位|转专业|休学|选课|考试|缓考|重修|重考|推免|保研|培养方案|辅修|微专业|挂科|GPA|成绩|学籍|预毕业|学科证明|大创|实践学分|军事理论|英语拓展|通识", "本科生院"),
]


def dept_of(q: str, a: str) -> str:
    t = q + a
    for pat, d in DEPT_RULES:
        if re.search(pat, t):
            return d
    return "中国传媒大学"


def clean_answer(a: str) -> str:
    a = a.strip()
    a = re.sub(r"^同学你好[，,]", "", a)
    a = re.sub(r"如果后续还有其他问题.*$", "", a, flags=re.S).strip()
    a = re.sub(r"祝学习顺利、生活愉快！?$", "", a).strip()
    return a


def main() -> None:
    lines = [l.strip() for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    pairs = []
    for line in lines:
        if "|" not in line or line.startswith("#") or line.startswith("问题"):
            continue
        q, a = [x.strip() for x in line.split("|", 1)]
        if len(q) < 4 or len(a) < 10:
            continue
        pairs.append((q, a))

    items_p = ROOT / "items.json"
    data = json.loads(items_p.read_text(encoding="utf-8"))
    have = {i["id"] for i in data["items"]}
    titles = {re.sub(r"\W+", "", i["title"]) for i in data["items"]}

    added = 0
    for n, (q, raw) in enumerate(pairs, 1):
        title = q.rstrip("？?")
        key = re.sub(r"\W+", "", title)
        iid = f"qa-18fe5c7d-{n:02d}"
        if iid in have or key in titles:
            continue
        answer = clean_answer(raw)
        if len(answer) < 8:
            continue
        item = {
            "id": iid,
            "title": title,
            "aliases": [q],
            "keywords": [],
            "dept": dept_of(q, raw),
            "channel": ["线上/线下按原文"],
            "audience": ["本科生", "研究生"],
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
            "kind": "qa",
            "source": [{"title": "问道中传 · QA 知识模板", "url": "", "checked": "2026-10-29"}],
            "evidence": {"answer": {"src": "18fe5c7d", "quote": raw}},
            "auto": True,
        }
        data["items"].append(item)
        have.add(iid)
        titles.add(key)
        added += 1

    data["updated"] = "2026-10-29"
    items_p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"解析 {len(pairs)} 条，新增 {added} 条，总计 {len(data['items'])}")


if __name__ == "__main__":
    main()
