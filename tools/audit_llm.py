"""对比测试：规则路由 vs 规则 + LLM 兜底。

只对「规则拿不准」的问法调用模型（分数不足或前二分差 <8），
统计命中率提升、调用次数、采纳率与耗时。

用法：
    python tools/audit_llm.py --limit 400     # 抽样，省时间
    python tools/audit_llm.py                 # 全量 3346 条
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import app as core  # noqa: E402
from audit_routing import variants  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="每个事项最多取几条问法")
    ap.add_argument("--out", default="routing-llm-compare.md")
    args = ap.parse_args()

    data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
    hand = [i for i in data if not i.get("auto")]
    title = {i["id"]: i["title"] for i in data}

    cases: list[tuple[str, str]] = []
    for item in hand:
        qs = variants(item)
        if args.limit:
            qs = qs[: args.limit]
        cases += [(q, item["id"]) for q in qs]
    print(f"样本 {len(cases)} 条（{len(hand)} 个事项）")

    # ---- 第一轮：纯规则 ----
    os.environ.pop("ROUTER_LLM", None)
    t0 = time.time()
    rule_hits = 0
    sure: list[tuple[str, str]] = []      # 规则能稳稳命中的
    unsure: list[tuple[str, str]] = []    # 需要兜底的
    for q, want in cases:
        d = core.answer_question(q)
        got = (d.get("item") or {}).get("id")
        if got == want and not d.get("ambiguous"):
            rule_hits += 1
            sure.append((q, want))
        else:
            unsure.append((q, want))
    rule_time = time.time() - t0
    print(f"规则命中 {rule_hits}/{len(cases)} = {rule_hits/len(cases):.1%}，耗时 {rule_time:.1f}s")
    print(f"需要兜底的 {len(unsure)} 条")

    # ---- 第二轮：只对 unsure 调 LLM ----
    os.environ["ROUTER_LLM"] = "1"
    t0 = time.time()
    llm_hits = 0
    adopted = 0
    calls = 0
    recovered: Counter = Counter()
    still_wrong: Counter = Counter()
    for q, want in unsure:
        before = core.answer_question(q)
        got = (before.get("item") or {}).get("id")
        calls += 1
        if got == want:
            llm_hits += 1
            adopted += 1
            recovered[title.get(want, want)[:20]] += 1
        else:
            still_wrong[(title.get(want, want)[:18], title.get(got or "拒答", got or "拒答")[:18])] += 1
    llm_time = time.time() - t0

    total_hits = rule_hits + llm_hits
    print(f"兜底后 {total_hits}/{len(cases)} = {total_hits/len(cases):.1%}")
    print(f"模型调用 {calls} 次，救回 {llm_hits} 条（{llm_hits/max(1,len(unsure)):.0%}），耗时 {llm_time:.1f}s")

    lines = [
        "# 规则 vs 规则+LLM 对比", "",
        f"- 样本：{len(cases)} 条问法 / {len(hand)} 个事项",
        f"- 纯规则命中：**{rule_hits/len(cases):.1%}**（{rule_hits}/{len(cases)}），耗时 {rule_time:.1f}s",
        f"- 规则+LLM 命中：**{total_hits/len(cases):.1%}**（{total_hits}/{len(cases)}）",
        f"- 触发兜底：{len(unsure)} 条；模型救回 {llm_hits} 条（{llm_hits/max(1,len(unsure)):.0%}）",
        f"- 兜底耗时：{llm_time:.1f}s（平均 {llm_time/max(1,calls)*1000:.0f} ms/次）",
        "", "## 模型救回的典型", "",
    ]
    for k, v in recovered.most_common(12):
        lines.append(f"- {k}：{v} 条")
    lines += ["", "## 仍然错的", "", "| 期望 | 实际 | 次数 |", "|---|---|---|"]
    for (w, g), n in still_wrong.most_common(15):
        lines.append(f"| {w} | {g} | {n} |")
    (ROOT / args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已写入 {args.out}")


if __name__ == "__main__":
    main()
