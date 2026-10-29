"""读取《本科专业简称（2026年版）》并生成 major-aliases.json。

103 行全部保留：学院、专业、简称、停招年份、对应接收计划专业、歧义与备注。
原文件留在 sources/reference/，随时可重新导入。
用法：python tools/import_major_aliases.py
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "sources" / "reference" / "本科专业简称（2026年版）.docx"
OUT = ROOT / "major-aliases.json"
PLANS = ROOT / "transfer-plans.json"

PLAN_COLLEGE = {
    "新闻学院": "新闻学院",
    "电视学院": "电视学院",
    "戏剧影视学院": "戏剧影视学院",
    "播音主持艺术学院": "播音主持艺术学院",
    "动画与数字艺术学院": "动画与数字艺术学院",
    "音乐与录音艺术学院": "音乐与录音艺术学院",
    "信息与通信工程学院": "信息与通信工程学院",
    "计算机与网络空间安全学院": "计算机与网络空间安全学院",
    "数据科学与智能媒体学院": "数据科学与智能媒体学院",
    "人文学院": "人文学院",
    "国际传播学院": "外国语言文化学院",
    "经济与管理学院": "经济与管理学院",
    "政府与公共事务学院": "政府与公共事务学院",
    "广告与品牌学院": "广告与品牌学院",
    "文化产业管理学院": "文化产业管理学院",
    "信息传播学院": "信息传播学院",
    "国际传媒教育学院": "",
    "海南国际教育学院": "",
}

COLLEGE_ALIASES = {
    "新闻学院": ["新闻"],
    "电视学院": ["电视"],
    "戏剧影视学院": ["戏影", "戏影学院"],
    "播音主持艺术学院": ["播院", "播音学院", "播音"],
    "动画与数字艺术学院": ["动院", "动画学院"],
    "音乐与录音艺术学院": ["音录", "音录学院"],
    "信息与通信工程学院": ["信通", "信通学院"],
    "计算机与网络空间安全学院": ["计网", "计网院", "网安学院", "计算机学院"],
    "数据科学与智能媒体学院": ["数智", "数智学院", "数据学院"],
    "人文学院": ["人文"],
    "国际传播学院": ["外院", "外语学院", "外国语言文化学院", "外国语言文化"],
    "经济与管理学院": ["经管", "经管学院"],
    "政府与公共事务学院": ["政院", "政府学院"],
    "广告与品牌学院": ["广告学院"],
    "文化产业管理学院": ["文产", "文产学院"],
    "信息传播学院": ["信传", "信传学院"],
    "国际传媒教育学院": ["国际传媒", "国传学院"],
    "海南国际教育学院": ["海南学院", "海南国际"],
}

SPECIAL_NOTES = {
    ("动画与数字艺术学院", "数字媒体技术（游戏科学与技术方向）"): (
        "「游技」在动画与数字艺术学院，不是信息与通信工程学院的数字媒体技术（数媒技）"),
    ("播音主持艺术学院", "播音与主持艺术"): "「播本」指播音与主持艺术本科",
    ("音乐与录音艺术学院", "作曲与作曲技术理论（电子音乐方向）"): (
        "「电音」是电子音乐方向，不是电子竞技"),
    ("戏剧影视学院", "环境设计（光影空间艺术方向）"): (
        "「光环境」是光影空间艺术方向，属戏剧影视学院"),
    ("新闻学院", "传播学（舆情分析方向）（至2024）"): (
        "「舆情」旧属新闻学院，该方向2024年停招；现行方向在信息传播学院"),
    ("信息传播学院", "传播学（舆情与社会治理方向）"): (
        "「舆情」现行方向，属信息传播学院"),
    ("动画与数字艺术学院", "动画（游戏艺术方向）（至2025）"): (
        "「游艺」旧名，2025年停招；现行专业为游戏艺术设计"),
    ("动画与数字艺术学院", "游戏艺术设计"): (
        "「游艺」现行专业，前身为动画（游戏艺术方向）"),
    ("信息与通信工程学院", "人工智能（智能视听卓越人才实验班）"): (
        "2025接收计划按人工智能整体列出，未单列实验班"),
    ("信息与通信工程学院", "人工智能（数字演艺工程方向）"): (
        "2025接收计划按人工智能整体列出，未单列该方向"),
    ("计算机与网络空间安全学院", "网络空间安全（AI治理与视听安全方向）"): (
        "2026年版原表未给简称；2025接收计划按网络空间安全整体列出，未单列该方向"),
    ("人文学院", "汉语言（语言数据与智能应用方向）"): (
        "2025接收计划按汉语言整体列出，未单列该方向"),
    ("经济与管理学院", "大数据管理与应用（智能商务分析方向）"): (
        "2025接收计划按大数据管理与应用整体列出，未单列该方向"),
    ("经济与管理学院", "工商管理（智能商业管理方向）"): (
        "2025接收计划按工商管理整体列出，未单列该方向"),
    ("电视学院", "国际新闻与传播（卓越人才实验班）"): (
        "2025接收计划按国际新闻与传播整体列出，未单列实验班"),
    ("戏剧影视学院", "戏剧影视导演"): "接收计划中写作「导演」",
    ("音乐与录音艺术学院", "音乐学（音乐编导与传播方向）"): (
        "2025接收计划分列音乐学（音乐编导方向）与音乐学（音乐编辑方向）"),
    ("国际传播学院", "播音与主持艺术（中英双语播音主持方向）"): (
        "学院2026年由外国语言文化学院更名；2025接收计划仍用旧名"),
}

PLAN_MAJOR_OVERRIDES = {
    ("动画与数字艺术学院", "动画（游戏艺术方向）（至2025）"): "动画（游戏艺术）",
    ("动画与数字艺术学院", "游戏艺术设计"): "动画（游戏艺术）",
    ("戏剧影视学院", "环境设计（光影空间艺术方向）"): "环境设计（光影空间艺术）",
    ("音乐与录音艺术学院", "音乐学（音乐编导与传播方向）"): "音乐学（音乐编导方向）",
    ("新闻学院", "新闻学（新闻舆论学方向）"): "新闻学（新闻舆论学）",
    ("计算机与网络空间安全学院", "网络空间安全（AI治理与视听安全方向）"): "网络空间安全",
    ("人文学院", "汉语言（语言数据与智能应用方向）"): "汉语言",
    ("信息与通信工程学院", "人工智能（智能视听卓越人才实验班）"): "人工智能",
    ("信息与通信工程学院", "人工智能（数字演艺工程方向）"): "人工智能",
    ("经济与管理学院", "大数据管理与应用（智能商务分析方向）"): "大数据管理与应用",
    ("经济与管理学院", "工商管理（智能商业管理方向）"): "工商管理",
    ("电视学院", "国际新闻与传播（卓越人才实验班）"): "国际新闻与传播",
    ("戏剧影视学院", "戏剧影视导演"): "导演",
}


def key_text(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[（(]\s*至\s*\d{4}\s*[)）]", "", s)
    s = s.replace("专业", "").replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", "", s)


def score(a: str, b: str) -> int:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0
    if na == nb:
        return 100
    if na in nb or nb in na:
        return 80 + int(10 * min(len(na), len(nb)) / max(len(na), len(nb)))
    base_a, base_b = na.split("(")[0], nb.split("(")[0]
    if base_a == base_b:
        dirs_a = set("".join(re.findall(r"\(([^()]*)\)", na)))
        dirs_b = set("".join(re.findall(r"\(([^()]*)\)", nb)))
        return 60 + min(10, len(dirs_a & dirs_b))
    return 0


def parse_college(label: str) -> tuple[str, str]:
    m = re.match(r"(.+?)[（(](.+?)[)）]$", label)
    return (m.group(1), m.group(2)) if m else (label, "")


NOTES = {(c, key_text(k)): v for (c, k), v in SPECIAL_NOTES.items()}
OVERRIDES = {(c, key_text(k)): v for (c, k), v in PLAN_MAJOR_OVERRIDES.items()}


def main() -> None:
    plans = json.loads(PLANS.read_text(encoding="utf-8")) if PLANS.exists() else {}
    doc = Document(DOCX)
    table = doc.tables[0]
    rows = [[unicodedata.normalize("NFKC", c.text).strip() for c in r.cells]
            for r in table.rows][1:]

    majors: list[dict] = []
    for i, (label, major, abbr) in enumerate(rows, 1):
        college, college_alias = parse_college(label)
        plan_college = PLAN_COLLEGE.get(college, "")
        has_plan = bool(plan_college and plan_college in plans)
        until_m = re.search(r"[（(]至(\d{4})[)）]", major)
        until = int(until_m.group(1)) if until_m else None

        plan_major = ""
        if has_plan:
            cands = [m["name"] for m in plans[plan_college].get("majors", [])]
            plan_major = OVERRIDES.get((college, key_text(major)), "")
            if not plan_major:
                exact = [c for c in cands if norm(c) == norm(major)]
                if exact:
                    plan_major = exact[0]
                elif until is None:
                    best = max(cands, key=lambda c: score(major, c), default="")
                    if best and score(major, best) >= 80:
                        plan_major = best

        if not has_plan:
            status = "no_plan"
        elif until is not None:
            status = "until_listed" if plan_major else "until"
        else:
            status = "current" if plan_major else "unlisted"

        note = NOTES.get((college, key_text(major)), "")
        if not abbr and "未给" not in note:
            note = "；".join(x for x in [note, "2026年版原表未给该方向简称"] if x)
        if not has_plan:
            note = "；".join(x for x in [
                note, "本次16份2025接收计划未包含该学院"] if x)
        elif until is None and not plan_major:
            note = "；".join(x for x in [
                note, "2025接收计划未单列此专业，以学院当年通知为准"] if x)
        if plan_college == "外国语言文化学院":
            note = "；".join(x for x in [
                "学院2026年由外国语言文化学院更名，2025接收计划仍用旧名",
                note] if x)

        majors.append({
            "id": i,
            "college": college,
            "college_label": label,
            "college_alias": college_alias,
            "major": major,
            "abbr": abbr,
            "until": until,
            "plan_college": plan_college,
            "has_plan": has_plan,
            "plan_major": plan_major,
            "status": status,
            "note": note,
        })

    abbr_index: dict[str, list[int]] = {}
    for m in majors:
        if m["abbr"]:
            abbr_index.setdefault(m["abbr"], []).append(m["id"])
    for m in majors:
        if len(abbr_index.get(m["abbr"], [])) > 1:
            others = [x for x in abbr_index[m["abbr"]] if x != m["id"]]
            names = [f"{x['major']}（{x['college']}）" for x in majors if x["id"] in others]
            m["ambiguous"] = True
            m["note"] = "；".join(x for x in [
                m["note"], "简称重复：" + "、".join(names)] if x)
        else:
            m["ambiguous"] = False

    colleges = {}
    for m in majors:
        if m["college"] in colleges:
            continue
        aliases = list(dict.fromkeys([
            m["college"],
            m["college"].replace("学院", ""),
            *COLLEGE_ALIASES.get(m["college"], []),
        ]))
        if m["college_alias"]:
            aliases.append(m["college_alias"])
        colleges[m["college"]] = {
            "label": m["college_label"],
            "aliases": aliases,
            "plan_college": m["plan_college"],
            "has_plan": m["has_plan"],
        }

    data = {
        "_meta": {
            "title": "中国传媒大学本科专业简称（2026年版）",
            "source": str(DOCX.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(DOCX.read_bytes()).hexdigest(),
            "rows": len(majors),
            "generated_by": "tools/import_major_aliases.py",
        },
        "colleges": colleges,
        "majors": majors,
        "abbr_index": abbr_index,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"导入 {len(majors)} 条专业简称、{len(colleges)} 个学院 → {OUT.name}")
    dup = {k: v for k, v in abbr_index.items() if len(v) > 1}
    print("重复简称：", "、".join(f"{k}({len(v)})" for k, v in dup.items()) or "无")
    print("无简称：", "、".join(m["major"] for m in majors if not m["abbr"]) or "无")


if __name__ == "__main__":
    main()
