"""学院转专业问法回归：规则路由 vs 向量检索。

规则读 transfer-plans.json 的学院名与简称；向量用同一问题直接检索原文。
规则必须全中；向量只做对照，证明它是否该当主系统。
退出码：规则漏一条即 1。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app  # noqa: E402
import vector_index  # noqa: E402


def cases() -> list[tuple[str, str]]:
    plans = json.loads((ROOT / "transfer-plans.json").read_text(encoding="utf-8"))
    out: list[tuple[str, str]] = []
    for college, plan in plans.items():
        if college == "_mtime":
            continue
        short = college.replace("学院", "").replace("学部", "")
        aliases = plan.get("aliases") or []
        out.extend([
            (f"转专业去{college}有什么要求", college),
            (f"转去{short}要什么条件", college),
            (f"我想转去{aliases[0]}，需要准备什么", college),
            (f"转专业到{college}，具体要求和材料", college),
            (f"{college}接收计划在哪看", college),
        ])
    out.extend([
        ("转专业具体要求，我要转去动院", "动画与数字艺术学院"),
        ("我要转游技", "动画与数字艺术学院"),
        ("播本要什么条件", "播音主持艺术学院"),
        ("电音怎么转", "音乐与录音艺术学院"),
        ("光环境接收条件", "戏剧影视学院"),
        ("数媒技", "信息与通信工程学院"),
        ("游艺", "动画与数字艺术学院"),
    ])
    return out


def main() -> None:
    plans = json.loads((ROOT / "transfer-plans.json").read_text(encoding="utf-8"))
    missing_files = [c for c, p in plans.items() if c != "_mtime" and not p.get("file")]
    if missing_files:
        raise SystemExit("接收计划缺 PDF：" + "、".join(missing_files))

    missing_full = [c for c, p in plans.items() if c != "_mtime" and not p.get("full_text")]
    if missing_full:
        raise SystemExit("接收计划缺整份全文：" + "、".join(missing_full))

    # 整份 PDF 转出全文必须与逐字稿完全一致；每个专业、每个年级块都要在
    bad: list[str] = []
    for college, plan in plans.items():
        if college == "_mtime":
            continue
        src = ROOT / "sources" / "local" / f"{plan['slug']}.txt"
        source = src.read_text(encoding="utf-8")
        if re.sub(r"\s+", "", plan["full_text"]) != re.sub(r"\s+", "", source):
            bad.append(f"{college} 整份全文与逐字稿不一致")
        if not plan.get("majors"):
            bad.append(f"{college} 没有专业行")
        for major in plan.get("majors") or []:
            if not major.get("blocks"):
                bad.append(f"{college} / {major.get('name')} 没有年级块")
            for block in major.get("blocks") or []:
                for key in ("conditions", "materials", "exam", "contacts", "note"):
                    raw = (block.get("raw") or {}).get(key, "")
                    if raw and not block.get(key):
                        bad.append(f"{college} / {major['name']} / {key} 有原文没抽出条目")
    if bad:
        print("计划数据不完整：")
        for b in bad[:20]:
            print("  ✗", b)
        raise SystemExit(1)

    # 每条摘录必须是原文件的逐字片段（去掉空白后比对）
    bad_quotes: list[str] = []
    for college, plan in plans.items():
        if college == "_mtime":
            continue
        src = ROOT / "sources" / "local" / f"{plan['slug']}.txt"
        raw = re.sub(r"\s+", "", src.read_text(encoding="utf-8"))
        for key in ("conditions", "materials", "exam", "contacts"):
            for line in plan.get(key) or []:
                if re.sub(r"\s+", "", line) not in raw:
                    bad_quotes.append(f"{college} {key}: {line[:40]}")
    if bad_quotes:
        print("引文不在原文：")
        for b in bad_quotes[:20]:
            print("  ✗", b)
        raise SystemExit(1)

    rows = cases()
    rule_ok = vec1 = vec3 = exp1 = exp3 = 0
    misses: list[str] = []
    for q, college in rows:
        tp = app.transfer_plan(q)
        got = tp["college"] if tp else None
        if got == college:
            rule_ok += 1
        else:
            misses.append(f"{q} → {got or '未命中'}（应为 {college}）")

        hits = vector_index.search(q, k=3, min_score=0)
        titles = [h["title"] for h in hits]
        vec1 += bool(titles and college in titles[0])
        vec3 += any(college in t for t in titles)

        exp = vector_index.search(f"转专业 接收计划 {college} {q}", k=3, min_score=0)
        etitles = [h["title"] for h in exp]
        exp1 += bool(etitles and college in etitles[0])
        exp3 += any(college in t for t in etitles)

    total = len(rows)
    print(f"学院转专业问法 {total} 条")
    print(f"  规则路由      {rule_ok}/{total}")
    print(f"  向量原句 top1 {vec1}/{total} · top3 {vec3}/{total}")
    print(f"  向量扩写 top1 {exp1}/{total} · top3 {exp3}/{total}")
    if misses:
        print("\n规则漏项：")
        for m in misses[:20]:
            print("  ✗", m)
        raise SystemExit(1)
    print("✓ 规则路由全部命中；向量只作兜底")


if __name__ == "__main__":
    main()
