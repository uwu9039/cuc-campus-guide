"""扩展版高频问题压测：覆盖新生到毕业的常见事务（60 问）。

问题来源：北理工计算机学院《学生事务办理流程》、上海师大教务处 Q&A 栏目、
各校 AI 助手的公开使用报告，以及本校语料中高频出现的办事名目。
"""
from __future__ import annotations

import json
import urllib.request

GROUPS: dict[str, list[str]] = {
    "新生与入学": [
        "新生什么时候报到", "军训要准备什么", "新生怎么选课", "入学要带哪些材料",
        "户口要不要迁到学校", "团组织关系怎么转",
    ],
    "教务与选课": [
        "课表在哪看", "教材在哪买", "教室怎么借", "选课学分不够怎么办",
        "辅修和双学位有什么区别", "微专业怎么报", "通识课有哪些",
    ],
    "成绩与考试": [
        "成绩什么时候出", "绩点怎么算", "成绩复核怎么申请", "缓考怎么申请",
        "重修和补考有什么区别", "四六级没过能毕业吗", "考试违纪会怎么处理",
    ],
    "学籍与毕业": [
        "转专业什么时候能申请", "休学最多能休多久", "复学要办什么手续",
        "毕业要修满多少学分", "毕业论文什么时候开题", "学位证和毕业证有什么区别",
        "结业能换毕业证吗",
    ],
    "就业与档案": [
        "三方协议怎么签", "档案毕业去哪了", "报到证还要办吗",
        "就业推荐表在哪开", "实习证明怎么开",
    ],
    "奖助与资助": [
        "奖学金什么时候评", "助学金要什么条件", "助学贷款怎么还",
        "勤工助学怎么申请", "临时困难补助怎么申请",
    ],
    "生活与后勤": [
        "宿舍怎么换", "退宿怎么办", "宿舍报修找谁", "宿舍电费怎么交",
        "食堂几点开饭", "快递在哪取", "校园卡丢了怎么办", "校园卡怎么充值",
    ],
    "网络与信息化": [
        "校园网怎么连", "网费怎么交", "统一身份认证密码忘了",
        "校园邮箱怎么开通", "VPN怎么用",
    ],
    "医疗与心理": [
        "校医院几点开门", "医保怎么报销", "心理预约怎么约",
    ],
    "安全与户籍": [
        "户籍卡怎么借", "无犯罪记录证明怎么开", "访客怎么进校",
    ],
    "出国与交流": [
        "出国交流怎么申请", "交换学分怎么认定", "留学要准备什么材料",
    ],
    "场馆与图书馆": [
        "体育场馆怎么预约", "图书馆怎么借书", "研修间怎么预约",
    ],
}


def ask(q: str) -> dict:
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/ask",
        data=json.dumps({"text": q}).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=40).read())


def main() -> None:
    rows, stat = [], {"命中": 0, "反问": 0, "拒答": 0}
    for group, qs in GROUPS.items():
        for q in qs:
            d = ask(q)
            if d.get("clarify"):
                s, detail = "反问", (d.get("clarify") or "")[:28]
            elif d.get("matched"):
                s, detail = "命中", (d.get("item") or {}).get("title", "")[:24]
            else:
                s, detail = "拒答", (d.get("reason") or "")[:22]
            stat[s] += 1
            rows.append((group, q, s, detail))

    total = len(rows)
    print(f"共 {total} 问：命中 {stat['命中']}、反问 {stat['反问']}、拒答 {stat['拒答']}")
    for group in GROUPS:
        sub = [r for r in rows if r[0] == group]
        ok = sum(1 for r in sub if r[2] == "命中")
        print(f"  {group:<10}{ok}/{len(sub)}")

    lines = ["# 扩展高频问题压测", "",
             f"- 问题 {total}：命中 {stat['命中']}、反问 {stat['反问']}、拒答 {stat['拒答']}", ""]
    for group in GROUPS:
        lines += [f"## {group}", "", "| 问题 | 结果 | 命中事项 / 说明 |", "|---|---|---|"]
        for g, q, s, d in rows:
            if g == group:
                lines.append(f"| {q} | {s} | {d} |")
        lines.append("")
    open("hot-questions-2.md", "w", encoding="utf-8").write("\n".join(lines))
    print("\n已写入 hot-questions-2.md")


if __name__ == "__main__":
    main()
