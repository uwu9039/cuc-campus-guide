"""把所有测试问题汇总成一份题库（JSON + Markdown）。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/build_question_bank.py

读（只读）：
  eval.py                                  事项路由 33 / 聚焦 12 / 同族 29
  _review_items/eval_sections_20.json      章级 20
  _review_items/eval_compete_15_20261112.json   稳定性 15
  _review_items/_ablation_nosec_20261112.json + _content5   消融 15
  _review_items/eval_compound_pilot8_20261112.json      复合 8
  _review_items/eval_compound_extra9_20261112.json      复合 1（第 9 题）
  _review_items/compound30_after_v7.jsonl               复合 30
  _review_items/eval100_synth_after8_20261110.jsonl     综合 100
  _review_items/ab_gate_206_after_20261105.json         A/B 回归 206（键=问题）
  _review_items/prompt_golden_20261106.json             路由 golden 48（case 字段里取问题）

写：
  _review_items/题库_20261113.json
  _review_items/题库_20261113.md
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "_review_items"


def norm(q: str) -> str:
    return re.sub(r"[\s　]+", "", q or "")


def from_eval_py() -> list[dict]:
    src = (ROOT / "eval.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    vals: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            try:
                vals[node.target.id] = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                pass
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                vals[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                pass
    out: list[dict] = []
    for q, exp, kind in vals.get("CASES") or []:
        out.append({"set": "eval33", "q": q, "expect": exp or "拒答", "extra": f"类型={kind}"})
    for q, focus in vals.get("FOCUS_CASES") or []:
        out.append({"set": "focus12", "q": q, "expect": f"聚焦={focus}", "extra": ""})
    for fam, cases in vals.get("FAMILY_CASES") or []:
        for q, exp in cases:
            out.append({"set": "family29", "q": q, "expect": exp, "extra": f"同族={fam}"})
    return out


def from_sections20() -> list[dict]:
    d = json.loads((R / "eval_sections_20.json").read_text(encoding="utf-8"))
    return [{"set": "sections20", "q": c["q"],
             "expect": f'{c.get("expect_doc")} · {"/".join(c.get("expect_sections") or [])}',
             "extra": c.get("why", "")[:80]} for c in d.get("cases") or []]


def from_compete15() -> list[dict]:
    d = json.loads((R / "eval_compete_15_20261112.json").read_text(encoding="utf-8"))
    return [{"set": "compete15", "q": c["q"],
             "expect": f'{c.get("expect_doc")} · {"/".join(c.get("expect_sections") or [])}',
             "extra": "关键事实：" + "、".join(c.get("key_facts") or [])[:60]} for c in d.get("cases") or []]


def from_ablation() -> list[dict]:
    out = []
    for f, tag in (("_ablation_nosec_20261112.json", "消融10"), ("_ablation_nosec_content5_20261112.json", "消融5")):
        p = R / f
        if not p.exists():
            continue
        for c in json.loads(p.read_text(encoding="utf-8")):
            out.append({"set": "ablation15", "q": c["q"],
                        "expect": "/".join(c.get("expect_sections") or []),
                        "extra": tag})
    return out


def from_compound9() -> list[dict]:
    out = []
    for f in ("eval_compound_pilot8_20261112.json", "eval_compound_extra9_20261112.json"):
        d = json.loads((R / f).read_text(encoding="utf-8"))
        for c in d.get("cases") or []:
            subs = c.get("subs") or []
            out.append({"set": "compound9", "q": c["q"],
                        "expect": f"{len(subs)} 个子问题",
                        "extra": " ｜ ".join(s.get("ask", "") for s in subs)[:80]})
    return out


def from_jsonl(name: str, setname: str) -> list[dict]:
    p = R / name
    out = []
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        out.append({"set": setname, "q": d.get("q") or "",
                    "expect": (d.get("kind") or d.get("mode") or ""),
                    "extra": (d.get("conclusion") or d.get("item") or "")[:60]})
    return out


def from_ab206() -> list[dict]:
    d = json.loads((R / "ab_gate_206_after_20261105.json").read_text(encoding="utf-8"))
    return [{"set": "ab206", "q": q, "expect": (v or {}).get("id") or "",
             "extra": (v or {}).get("title", "")[:40]} for q, v in d.items()]


def from_golden48() -> list[dict]:
    d = json.loads((R / "prompt_golden_20261106.json").read_text(encoding="utf-8"))
    # 48 条是「同一问题 × 不同历史/路由变体」，按问题去重，变体数记在 extra
    counts: dict[str, int] = {}
    for row in d:
        case = str(row.get("case") or "")
        parts = case.split("/")
        q = (parts[1] if len(parts) > 1 else case).strip()
        counts[q] = counts.get(q, 0) + 1
    return [{"set": "golden48", "q": q, "expect": "路由 golden（无固定期望）",
             "extra": f"{n} 个历史/路由变体"} for q, n in counts.items()]


def main() -> None:
    all_cases = (from_eval_py() + from_sections20() + from_compete15() + from_ablation()
                 + from_compound9() + from_jsonl("compound30_after_v7.jsonl", "compound30")
                 + from_jsonl("judged_eval100.jsonl", "eval100")
                 + from_ab206() + from_golden48())

    by_set: dict[str, list[dict]] = {}
    seen: dict[str, list[str]] = {}
    for c in all_cases:
        by_set.setdefault(c["set"], []).append(c)
        seen.setdefault(norm(c["q"]), []).append(c["set"])

    uniq = len(seen)
    dup = {k: sorted(set(v)) for k, v in seen.items() if len(set(v)) > 1}

    payload = {
        "generated": "2026-11-13",
        "note": "全部测试问题汇总；同一问题出现在多个集合时在 duplicates 里列出。expect 字段是「期望落点」，口径随来源不同（事项 id / 章条 / 复合子问）。",
        "totals": {"raw": len(all_cases), "unique": uniq, "dup_questions": len(dup),
                   "sets": {k: len(v) for k, v in by_set.items()}},
        "sets": by_set,
        "duplicates": dup,
    }
    (R / "题库_20261113.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 题库 · 2026-11-13", "",
         f"- 原始条目 **{len(all_cases)}** 条，去重后 **{uniq}** 个问题（跨集重复 {len(dup)} 个）",
         "- 来源与口径：见每节表头；`expect` 的「期望落点」按来源不同（事项 id / 章·条 / 复合子问）",
         "", "## 汇总", "", "| 集合 | 条数 | 口径 | 来源文件 |", "|---|---|---|---|"]
    desc = {
        "eval33": ("事项路由", "eval.py CASES：期望事项 id，None=应拒答"),
        "focus12": ("聚焦点", "eval.py FOCUS_CASES：期望聚焦字段"),
        "family29": ("同族对照", "eval.py FAMILY_CASES：近邻问题不许互抢"),
        "sections20": ("章/节级", "eval_sections_20：期望文档 + 章/条"),
        "compete15": ("稳定性复测", "eval_compete_15：含 key_facts"),
        "ablation15": ("消融对照", "ablation 10 + content5"),
        "compound9": ("复合问（9）", "pilot8 + 第 9 题，含 subs 子问"),
        "compound30": ("复合问（30）", "compound30_after_v7.jsonl"),
        "eval100": ("综合 100（50 单问 + 50 复合）", "judged_eval100.jsonl；其中 50 条有 synth 标注"),
        "ab206": ("A/B 回归 206", "ab_gate_206_after：键=问题，值为命中条目"),
        "golden48": ("路由 golden（48 case / 6 问）", "prompt_golden_20261106：同问 8 个变体"),
    }
    for k, v in by_set.items():
        d, src = desc.get(k, ("", ""))
        L.append(f"| `{k}` | {len(v)} | {d} | {src} |")

    for k, v in by_set.items():
        d, src = desc.get(k, ("", ""))
        L += ["", f"## {k} · {d}（{len(v)} 条）", "", f"> {src}", "",
              "| # | 问题 | 期望落点 | 备注 |", "|---|---|---|---|"]
        for i, c in enumerate(v, 1):
            q = str(c["q"]).replace("|", "｜")
            e = str(c.get("expect") or "").replace("|", "｜")
            x = str(c.get("extra") or "").replace("|", "｜")
            L.append(f"| {i} | {q} | {e} | {x} |")

    if dup:
        L += ["", "## 跨集重复的问题", "", "| 问题 | 出现在 |", "|---|---|"]
        for q, sets in sorted(dup.items(), key=lambda kv: -len(kv[1]))[:60]:
            L.append(f"| {q[:40]} | {'、'.join(sets)} |")

    L += ["", "## 怎么跑", "",
          "```bash",
          "# 事项路由 33 + 聚焦 12 + 同族 29（约 6 分钟，rank 每问 3 秒）",
          "./.venv/Scripts/python.exe -X utf8 eval.py",
          "",
          "# 章/节级 20 条：规则腿 / 向量腿",
          "SECTIONS_BOOST=0 ./.venv/Scripts/python.exe -X utf8 tools/eval_sections.py",
          "SECTIONS_BOOST=1 ./.venv/Scripts/python.exe -X utf8 tools/eval_sections.py",
          "./.venv/Scripts/python.exe -X utf8 tools/eval_sections.py --vector --sections-only",
          "",
          "# 其余集合是数据文件，按各自的 runner/报告里的命令跑（compound30 / eval100 / ab206 见对应报告）",
          "```", ""]

    (R / "题库_20261113.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"raw {len(all_cases)} | unique {uniq} | dup {len(dup)}")
    for k, v in by_set.items():
        print(f"  {k:12s} {len(v):4d}")


if __name__ == "__main__":
    main()
