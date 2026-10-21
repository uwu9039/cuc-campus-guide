"""生成预置问法库 presets.json：给每个事项生成多种自然问法，并逐条验证路由。

用法：
    python tools/gen_presets.py            # 生成并验证
    python tools/gen_presets.py --keep-miss # 连没命中的也写进报告，便于修关键词

产物：
    presets.json        给界面用（只放验证通过的）
    presets-report.md   覆盖情况：哪些事项有问法、哪些问法会跑偏
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app as core  # noqa: E402

# 问法模板：{t}=标题，{a}=别名，{k}=关键词
TEMPLATES = [
    "{a}怎么办",
    "我想{t}",
    "{a}怎么弄",
    "{t}要带什么",
    "{t}在哪办",
    "{t}怎么办",
    "{t}怎么办理",
    "{t}流程",
    "{t}需要什么材料",
    "{t}要带什么",
    "{t}在哪办",
    "{t}去哪里办",
    "{t}要多久",
    "{t}多少钱",
    "{t}什么时候能办",
    "{t}找谁",
    "{t}该找哪个部门",
    "{t}截止时间",
    "{a}怎么办",
    "{a}怎么弄",
    "{a}流程",
]

GROUPS = [
    ("校园卡 / 信息化", re.compile(r"校园卡|一卡通|网络|邮箱|身份认证|人脸|交通卡|VPN|账号|密码|无感知")),
    ("学籍 / 证明", re.compile(r"学籍|休学|复学|退学|留级|转专业|证明|学位|毕业|结业|肄业|成绩单|在读")),
    ("选课 / 考试", re.compile(r"选课|退课|重考|重修|缓考|考试|四六级|CET|考场|违纪|学分|辅修|微专业")),
    ("体测 / 体育", re.compile(r"体测|体质|体育")),
    ("后勤 / 生活", re.compile(r"后勤|报修|购电|宿舍|食堂|住宿|维修")),
    ("其他", re.compile(r".")),
]


def group_of(title: str) -> str:
    for name, pat in GROUPS:
        if pat.search(title):
            return name
    return "其他"


def variants(item: dict) -> list[str]:
    t = item["title"]
    t = re.sub(r"[（(].*?[）)]", "", t).strip()      # 去掉括号补充
    aliases = [a for a in item.get("aliases", []) if 2 <= len(a) <= 10][:2]
    out = []
    for tpl in TEMPLATES:
        if "{a}" in tpl:
            for a in aliases:
                out.append(tpl.format(t=t, a=a, k=""))
        elif tpl == "我想{t}" and re.search(r"指南|办理|证明|申请|登记|补卡|办法|规定", t):
            continue   # 名词性标题加"我想"不通顺
        else:
            out.append(tpl.format(t=t, a="", k=""))
    return out


SUFFIX = re.compile(r"(怎么办|怎么办理|怎么弄|流程|要带什么|需要什么材料|在哪办|去哪里办|要多久|多少钱|什么时候能办|找谁|该找哪个部门|截止时间)$")


def stem(q: str) -> str:
    return SUFFIX.sub("", q)


def main() -> None:
    data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    presets, misses = [], []
    by_group: dict[str, list] = defaultdict(list)

    hand = [i for i in data["items"] if not i.get("auto")]
    auto_n = len(data["items"]) - len(hand)
    print(f"人工条目 {len(hand)} 条参与生成（机器抽取的 {auto_n} 条不预设问法，它们是原句摘要）")

    for item in hand:
        ok_here = 0
        seen_stems: set[str] = set()
        for q in dict.fromkeys(variants(item)):     # 去重保序
            d = core.answer_question(q)
            hit = (d.get("item") or {}).get("id")
            if not d.get("matched"):
                continue
            if hit == item["id"] and not d.get("disambiguate"):
                if stem(q) in seen_stems:   # 同一种说法只留一条（别再出"怎么办/怎么弄"重复）
                    continue
                if ok_here < 4:          # 每个事项最多留 4 条最自然的问法
                    seen_stems.add(stem(q))
                    presets.append({"q": q, "item": item["id"], "group": group_of(item["title"])})
                    ok_here += 1
            elif hit and hit != item["id"]:
                misses.append({"q": q, "want": item["id"], "got": hit,
                               "want_title": item["title"], "got_title": d["item"]["title"]})
        if ok_here == 0:
            misses.append({"q": f"（无可用问法）{item['title']}", "want": item["id"], "got": "-",
                           "want_title": item["title"], "got_title": "-"})

    for p in presets:
        by_group[p["group"]].append(p["q"])

    out = {"version": "1", "generated": "2026-10-21",
           "total": len(presets),
           "groups": [{"name": k, "items": v} for k, v in by_group.items()]}
    (ROOT / "presets.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    covered = len({p["item"] for p in presets})
    total_items = len(hand)
    lines = ["# 预置问法验证报告", "",
             f"- 事项总数：{total_items}",
             f"- 可用问法：**{len(presets)}** 条",
             f"- 有问法可命中的事项：**{covered}/{total_items}**",
             f"- 跑偏/缺失：{len(misses)}",
             "", "## 分组分布", "", "| 分组 | 问法数 |", "|---|---|"]
    for k, v in by_group.items():
        lines.append(f"| {k} | {len(v)} |")
    if misses:
        lines += ["", "## 需要修的事项（问法命不中自己）", "", "| 问法 | 期望 | 实际命中的是 |", "|---|---|---|"]
        for m in misses[:60]:
            lines.append(f"| {m['q'][:40]} | {m['want_title'][:20]} | {m['got_title'][:20]} |")
    (ROOT / "presets-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"问法 {len(presets)} 条，覆盖 {covered}/{total_items} 个事项，跑偏 {len(misses)} 条")
    if "--keep-miss" in sys.argv and misses:
        for m in misses[:15]:
            print(f"  ✗ {m['q'][:32]:<34} 期望 {m['want_title'][:14]}  实际 {m['got_title'][:14]}")


if __name__ == "__main__":
    main()
