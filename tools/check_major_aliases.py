"""核对 2026 版专业简称表：行数、学院、计划专业对应，以及每条简称的实际路由。

退出码：任一映射或路由不一致即 1。
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402


def key(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[（(]\s*至\s*\d{4}\s*[)）]", "", s)
    s = re.sub(r"\s+", "", s)
    return s[:-2] if s.endswith("专业") else s


def main() -> None:
    aliases = json.loads((ROOT / "major-aliases.json").read_text(encoding="utf-8"))
    plans = json.loads((ROOT / "transfer-plans.json").read_text(encoding="utf-8"))
    majors = aliases.get("majors") or []

    if len(majors) != 103 or aliases["_meta"].get("rows") != 103:
        raise SystemExit(f"简称表应为 103 条，实际 {len(majors)} 条")
    if len(aliases.get("colleges") or {}) != 18:
        raise SystemExit(f"简称表应为 18 个学院，实际 {len(aliases.get('colleges') or {})} 个")

    bad: list[str] = []
    for college, meta in (aliases.get("colleges") or {}).items():
        if meta.get("has_plan") and meta.get("plan_college") not in plans:
            bad.append(f"{college} 指向不存在的计划 {meta.get('plan_college')}")

    plan_major_keys: dict[str, set[str]] = {}
    for college, plan in plans.items():
        if college == "_mtime":
            continue
        plan_major_keys[college] = {key(m["name"]) for m in plan.get("majors") or []}
        if not plan.get("full_text"):
            bad.append(f"{college} 缺整份 PDF 转出全文")
        if not plan.get("majors"):
            bad.append(f"{college} 没有专业行")

    for m in majors:
        pc = m.get("plan_college") or ""
        if m.get("plan_major") and pc:
            if pc not in plan_major_keys:
                bad.append(f"{m['id']} {m['major']} 的计划学院不存在：{pc}")
            elif key(m["plan_major"]) not in plan_major_keys[pc]:
                bad.append(f"{m['id']} {m['major']} 计划专业不存在：{pc} / {m['plan_major']}")
        if m.get("status") not in {"current", "until", "until_listed", "unlisted", "no_plan"}:
            bad.append(f"{m['id']} 状态未知：{m.get('status')}")
        if m.get("has_plan") and m.get("status") == "no_plan":
            bad.append(f"{m['id']} 有学院计划却标成 no_plan")

    abbrs = [m["abbr"] for m in majors if m.get("abbr")]
    dup = {k: v for k, v in Counter(abbrs).items() if v > 1}
    if set(dup) != {"舆情", "游艺"}:
        bad.append(f"重复简称与预期不符：{dup}")
    empty = [m for m in majors if not m.get("abbr")]
    if len(empty) != 1 or empty[0]["id"] != 51:
        bad.append(f"空简称与预期不符：{[m['id'] for m in empty]}")

    # 每条简称/专业名都要真的能路由回它自己的学院与计划专业
    routes = 0
    for m in majors:
        name = m.get("abbr") or m.get("major")
        q = f"转专业到{m['college']}{name}"
        tp = app.transfer_plan(q)
        routes += 1
        if not tp:
            bad.append(f"路由未命中：{q}")
            continue
        want_college = m.get("plan_college") or m.get("college")
        if tp["college"] != want_college:
            bad.append(f"路由学院错：{q} → {tp['college']}（应为 {want_college}）")
            continue
        focus = tp.get("focus") or {}
        if m.get("plan_major"):
            if key(focus.get("plan_major", "")) != key(m["plan_major"]):
                bad.append(f"路由专业错：{q} → {focus.get('plan_major') or '无'}（应为 {m['plan_major']}）")
        elif not focus:
            bad.append(f"路由没有识别出专业：{q}")
        if m.get("status") == "no_plan" and not tp.get("no_plan"):
            bad.append(f"无计划学院却给出了文件：{q}")

    # 用户点名的几个简称，逐一固定预期
    fixed = {
        "游技": ("动画与数字艺术学院", "数字媒体技术（游戏科学与技术方向）"),
        "播本": ("播音主持艺术学院", "播音与主持艺术专业"),
        "电音": ("音乐与录音艺术学院", "作曲与作曲技术理论（电子音乐方向）"),
        "光环境": ("戏剧影视学院", "环境设计（光影空间艺术）"),
        "数媒技": ("信息与通信工程学院", "数字媒体技术"),
        "游艺": ("动画与数字艺术学院", "动画（游戏艺术）"),
    }
    for abbr, (college, plan_major) in fixed.items():
        tp = app.transfer_plan(f"我要转{abbr}")
        if not tp or tp["college"] != college or key((tp.get("focus") or {}).get("plan_major", "")) != key(plan_major):
            bad.append(f"点名简称未对上：{abbr} → {tp and tp['college']}")

    # 重复简称：默认取现行；点名学院时按学院取旧/新
    checks = [
        ("我想转舆情", "信息传播学院", "传播学(舆情与社会治理方向)"),
        ("新闻学院舆情", "新闻学院", "传播学(舆情分析方向)(至2024)"),
        ("信传舆情", "信息传播学院", "传播学(舆情与社会治理方向)"),
    ]
    for q, college, major in checks:
        tp = app.transfer_plan(q)
        got = (tp.get("focus") or {}).get("major") if tp else None
        if not tp or tp["college"] != college or got != major:
            bad.append(f"重复简称路由错：{q} → {tp and tp['college']} / {got}")

    print(f"专业简称 {len(majors)} 条 · 学院 {len(aliases.get('colleges') or {})} 个 · 路由 {routes} 条")
    print(f"  重复简称：{'、'.join(f'{k}({v})' for k, v in dup.items()) or '无'}")
    print(f"  无简称：{'、'.join(m['major'] for m in empty) or '无'}")
    if bad:
        print("\n不一致：")
        for b in bad[:30]:
            print("  ✗", b)
        raise SystemExit(1)
    print("✓ 简称、学院、计划专业三者全部对上；路由逐条命中")


if __name__ == "__main__":
    main()
