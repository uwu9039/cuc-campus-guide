"""从路由审计里推导「敏感词」：凡是被测试证明会引起错误跳转的词，就算。

做法：
  1. 对每个事项生成变体问法（复用 audit_routing.variants）
  2. 只跑规则（不调模型），收集「期望 A 却落到 B」的失败问法
  3. 从失败问法里提取 n-gram，统计「出现该词时的失败率」
  4. 失败率显著高于基线的词 → 写进 sensitive.json，供界面提示

用法：
    python tools/derive_sensitive.py            # 重新推导
    python tools/derive_sensitive.py --report   # 只看结果不写文件
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import app as core  # noqa: E402
from audit_routing import variants  # noqa: E402

OUT = ROOT / "sensitive.json"
MIN_N, MAX_N = 2, 4          # 只在 2–4 字范围内找词
MIN_OCCUR = 5                # 至少出现这么多次才考虑
MIN_RATE = 0.18              # 出现该词时风险率 ≥18% 才算危险
MIN_LIFT = 2.0               # 且至少是基线风险率的 2 倍


def ngrams(text: str) -> set[str]:
    out = set()
    t = text.strip()
    for n in range(MIN_N, MAX_N + 1):
        for i in range(len(t) - n + 1):
            g = t[i:i + n]
            if g.isdigit() or all(c in "的了吗呢啊在是我你他这那个怎么办理申请问请" for c in g):
                continue
            out.add(g)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
    hand = [i for i in items if not i.get("auto")]
    title = {i["id"]: i["title"] for i in items}

    cases: list[tuple[str, str]] = []
    for it in hand:
        cases += [(q, it["id"]) for q in variants(it)]

    # 候选词限定为「事项自己的关键词 / 别名」，避免切出"学与复学"这种碎片
    vocab: set[str] = set()
    for it in items:
        for w in list(it.get("keywords") or []) + list(it.get("aliases") or []):
            w = (w or "").strip()
            if 2 <= len(w) <= 8:
                vocab.add(w)

    total = len(cases)
    # 风险 = 跳错 或 规则自己都拿不准（触发反问）。两种都由"某个词"引起就算
    fails: list[tuple[str, str, str]] = []      # (query, want, got)
    risky_q: list[str] = []
    for q, want in cases:
        d = core.answer_question(q)
        got = (d.get("item") or {}).get("id")
        if got != want or d.get("ambiguous"):
            fails.append((q, want, got or "反问"))
            risky_q.append(q)

    base_rate = len(fails) / total
    print(f"问法 {total}，风险 {len(fails)}（跳错+反问），基线 {base_rate:.1%}")

    occ = Counter()       # 词 -> 出现在多少问法里
    bad = Counter()       # 词 -> 其中失败多少次
    for q, want in cases:
        for g in ngrams(q) & vocab:
            occ[g] += 1
    for q, _w, _g in fails:
        for g in ngrams(q) & vocab:
            bad[g] += 1

    scored = []
    for g, n in occ.items():
        if n < MIN_OCCUR:
            continue
        rate = bad[g] / n
        lift = rate / base_rate if base_rate else 0
        if rate >= MIN_RATE and lift >= MIN_LIFT:
            scored.append((g, n, bad[g], rate, lift))
    # 长词优先，避免"复学"这种短词把"休学与复学"吃掉
    scored.sort(key=lambda x: (-len(x[0]), -x[3], -x[2]))

    # 去重：如果一个词是另一个更长词的子串且失败次数接近，只留长的
    picked: list[tuple[str, int, int, float]] = []
    for g, n, b, rate, lift in scored:
        if any(g in p[0] and b <= p[2] for p in picked):
            continue
        picked.append((g, n, b, rate))

    print(f"\n候选敏感词 {len(picked)} 个（失败率 ≥{MIN_RATE:.0%} 且 ≥{MIN_LIFT}× 基线）：")
    for g, n, b, rate in picked[:30]:
        print(f"  {g:<6} 出现 {n:>3} 次，错 {b:>2} 次，失败率 {rate:.0%}")

    if args.report:
        return

    payload = {
        "generated": "2026-10-26",
        "method": "routing audit: words whose presence raises misroute rate above baseline",
        "baseline_fail_rate": round(base_rate, 4),
        "total_queries": total,
        "words": [
            {"w": g, "seen": n, "wrong": b, "rate": round(rate, 3)}
            for g, n, b, rate in picked
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 {OUT.name}（{len(picked)} 个词）")


if __name__ == "__main__":
    main()
