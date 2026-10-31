"""路由审计：对每个事项生成大量变体问法，压测意图识别，输出混淆矩阵。

用法：
    python tools/audit_routing.py                # 全量
    python tools/audit_routing.py --top 25       # 只看最严重的前 25 组混淆

变体生成策略（比 presets 更狠）：
  1. 标题 / 别名 / 关键词原样
  2. 模板：「X 怎么办 / X 流程 / X 要带什么 / 在哪办 / 多少钱 / 要多久 / 什么时候能办 / 找谁」
  3. 加料：在问题前加「请问」「我想问一下」；加后缀「啊」「呢」
  4. 删词：把标题里连续的修饰词删掉一个字（制造口语残缺）
  5. 跨域探针：用 A 的关键词 + B 的语境词，看会不会被抢

只做判定，不渲染答案，所以很快。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import app as core  # noqa: E402

TEMPLATES = [
    "{x}", "{x}怎么办", "{x}怎么办理", "{x}流程", "{x}要带什么", "{x}需要什么材料",
    "{x}在哪办", "{x}去哪里办", "{x}多少钱", "{x}要多久", "{x}什么时候能办",
    "{x}找谁", "我想{x}", "请问{x}怎么办", "{x}呢",
]

FILLERS = ["请问", "我想问一下", "问一下", ""]


def norm_title(t: str) -> str:
    t = re.sub(r"[（(].*?[）)]", "", t)
    return t.strip()


def variants(item: dict) -> list[str]:
    outs: list[str] = []
    base = norm_title(item["title"])
    stems = [base] + [a for a in item.get("aliases", []) if 2 <= len(a) <= 12][:3]
    stems += [k for k in item.get("keywords", []) if 2 <= len(k) <= 8][:2]
    for s in stems:
        for tpl in TEMPLATES:
            outs.append(tpl.format(x=s))
    # 删词变体：制造口语残留
    if len(base) >= 5:
        for i in range(1, len(base) - 1, max(1, len(base) // 4)):
            outs.append(base[:i] + base[i + 1:] + "怎么办")
    # 前缀加料
    outs += [f + base + "怎么办" for f in FILLERS if f]
    return list(dict.fromkeys(outs))


def _run_chunk(queries: list[str]) -> list[tuple[str | None, bool, bool]]:
    import app as core  # 子进程各自加载一遍条目，避免跨进程共享可变状态

    rows: list[tuple[str | None, bool, bool]] = []
    for q in queries:
        d = core.answer_question(q)
        rows.append(((d.get("item") or {}).get("id"),
                     bool(d.get("disambiguate")), bool(d.get("ambiguous"))))
    return rows


def run_cases(queries: list[str], workers: int = 1) -> list[tuple[str | None, bool, bool]]:
    """按原顺序返回 (命中条目, 是否反问, 是否歧义)；并行与串行结果一致。"""
    if workers <= 1 or len(queries) < 50:
        return _run_chunk(queries)
    from concurrent.futures import ProcessPoolExecutor

    size = max(20, len(queries) // (workers * 6))
    chunks = [queries[i:i + size] for i in range(0, len(queries), size)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        parts = list(ex.map(_run_chunk, chunks))
    return [row for part in parts for row in part]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()

    data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
    hand = [i for i in data if not i.get("auto")]
    print(f"参与审计的事项：{len(hand)} 条（人工条目）")

    cases: list[tuple[str, str]] = []
    case_total: dict[str, int] = {}
    for item in hand:
        qs = variants(item)
        if args.limit:
            qs = qs[: args.limit]
        case_total[item["id"]] = len(qs)
        cases += [(q, item["id"]) for q in qs]
    total = len(cases)
    print(f"总问法 {total}，并行进程 {args.workers}")
    results = run_cases([q for q, _ in cases], args.workers)

    ok = 0
    miss_by_item: Counter = Counter()
    confusions: Counter = Counter()      # (期望, 实际) -> 次数
    examples: dict[tuple[str, str], list[str]] = defaultdict(list)
    ambiguous = 0

    for (q, want), (got, dis, _amb) in zip(cases, results):
        if dis:
            ambiguous += 1
        if got == want:
            ok += 1
        else:
            miss_by_item[want] += 1
            key = (want, got or "拒答")
            confusions[key] += 1
            if len(examples[key]) < 2:
                examples[key].append(q)

    print(f"\n总问法 {total}，命中 {ok} = {ok/total:.1%}")
    print(f"触发反问（gap<8）：{ambiguous} 条 = {ambiguous/total:.1%}")

    title = {i["id"]: i["title"] for i in data}
    print(f"\n最严重的 {args.top} 组混淆（期望 → 实际）：")
    for (want, got), n in confusions.most_common(args.top):
        print(f"  {n:>4} 次  {title.get(want, want)[:22]:<24} → {title.get(got, got)[:24]}")
        for q in examples[(want, got)]:
            print(f"         例：{q}")

    print("\n命中率最低的事项：")
    for iid, n in miss_by_item.most_common(8):
        print(f"  {title.get(iid, iid)[:26]:<28} 失手 {n}/{case_total.get(iid, 0)}")

    out = ROOT / "routing-audit.md"
    lines = ["# 路由审计报告", "",
             f"- 事项：{len(hand)}", f"- 问法：{total}", f"- 命中率：**{ok/total:.1%}**",
             f"- 反问触发率：{ambiguous/total:.1%}",
             "", "## 混淆 Top", "", "| 次数 | 期望 | 实际 | 例 |", "|---|---|---|---|"]
    for (want, got), n in confusions.most_common(40):
        lines.append(f"| {n} | {title.get(want, want)} | {title.get(got, got)} | {examples[(want, got)][0][:28]} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n已写入 {out.name}")


if __name__ == "__main__":
    main()
