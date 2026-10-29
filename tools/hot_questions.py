"""用「大学生最常问的问题」压测智能体：看命中 / 反问 / 拒答。"""
from __future__ import annotations

import json
import urllib.request

QUESTIONS = [
    "成绩单怎么打", "英文成绩单去哪办", "校园卡丢了怎么补", "校园卡余额在哪查",
    "选课什么时候截止", "想退一门课", "重修怎么报名", "四六级什么时候报名",
    "保研要什么条件", "推免名额怎么定", "转专业什么时候申请", "休学怎么办",
    "奖学金什么时候评", "助学金怎么申请", "助学贷款怎么办理",
    "宿舍报修找谁", "宿舍能不能换", "退宿怎么办",
    "在读证明怎么开", "学生证丢了", "毕业要多少学分", "体测不及格怎么办",
    "医保怎么报销", "校医院几点开门", "档案在哪", "户口怎么迁",
    "三方协议怎么签", "出国交流怎么申请", "图书馆怎么借书", "校园网连不上",
    "统一身份认证密码忘了", "教室怎么借", "体育场馆怎么预约", "快递在哪取",
]


def ask(q: str) -> dict:
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/ask",
        data=json.dumps({"text": q}).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=40).read())


def main() -> None:
    rows = []
    hit = clarify = refused = 0
    for q in QUESTIONS:
        d = ask(q)
        if d.get("clarify"):
            status, detail = "反问", (d.get("clarify") or "")[:30]
            clarify += 1
        elif d.get("matched"):
            status, detail = "命中", (d.get("item") or {}).get("title", "")[:26]
            hit += 1
        else:
            status, detail = "拒答", (d.get("reason") or "")[:24]
            refused += 1
        rows.append((q, status, detail))

    n = len(QUESTIONS)
    print(f"共 {n} 问：命中 {hit}、反问 {clarify}、拒答 {refused}")
    for q, s, d in rows:
        mark = "✓" if s == "命中" else ("?" if s == "反问" else "✗")
        print(f"  {mark} {q:<16}{s}  {d}")

    lines = ["# 高频问题压测", "", f"- 问题 {n}：命中 {hit}、反问 {clarify}、拒答 {refused}", "",
             "| 问题 | 结果 | 命中事项 / 说明 |", "|---|---|---|"]
    for q, s, d in rows:
        lines.append(f"| {q} | {s} | {d} |")
    open("hot-questions.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n已写入 hot-questions.md")


if __name__ == "__main__":
    main()
