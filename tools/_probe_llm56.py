# -*- coding: utf-8 -*-
"""补测：模型按补丁写的规则短句「追加进同一条检索 + cap 56」的召回，
并给一个噪声代理（池里与问句无关、且不含任何金标准 kw 的条数）。

只读。结果写 `_review_items/_plan_connector_llm56.json`。

用法（仓库根目录）：
    ./.venv/Scripts/python.exe -X utf8 tools/_probe_llm56.py
前置：先跑过一次 `tools/_plan_connector_probe.py`（它写 `_plan_connector_cache.json`）。
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOLDEN = "_review_items/golden_20261111.json"
CACHE = "_review_items/_plan_connector_cache.json"
OUT = "_review_items/_plan_connector_llm56.json"
CAP = 56


def norm(s) -> str:
    return "".join(str(s or "").split()).lower()


def alts(kw) -> list[str]:
    return [norm(x) for x in str(kw).split("|") if norm(x)]


def loose(point: dict, text: str) -> bool:
    return all(any(a in text for a in alts(k)) for k in (point.get("kw") or []))


def strict(point: dict, cands: list[dict]) -> bool:
    for c in cands:
        q = norm(c.get("quote"))
        if q and all(any(a in q for a in alts(k)) for k in (point.get("kw") or [])):
            return True
    return False


def noise(cands, question: str, pts) -> int:
    """与问句没有 ≥2 个二字组重合、且不含任何金标准 kw 的候选条数。"""
    import app  # noqa: E402  （延迟导入：只在真跑时加载 39274 条）

    qb = {g for g in app.bigrams(norm(question)) if g not in app._TOPIC_STOP}
    kws = [a for p in pts for k in (p.get("kw") or []) for a in alts(k)]
    n = 0
    for c in cands:
        q = norm(c.get("quote"))
        if any(a in q for a in kws):
            continue
        if len(qb & set(app.bigrams(q))) >= 2:
            continue
        n += 1
    return n


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    import app  # noqa: E402

    cache = json.load(open(CACHE, encoding="utf-8"))
    golden = json.load(open(GOLDEN, encoding="utf-8"))
    rows = []
    for ci, case in enumerate(golden["cases"], 1):
        q, pts = case["q"], case["points"]
        rec = cache[q]
        base_q, prem = rec["queries"], rec["premises"]
        llm_q = rec.get("llm_rules") or []
        print("[%d] %s + %r" % (ci, q, llm_q), flush=True)

        base = app._synth_candidates(base_q, prem, cap=48, question=q)
        conn = app._synth_candidates(base_q + llm_q, prem, cap=CAP, question=q)
        rows.append({
            "q": q, "llm_rules": llm_q,
            "base": {"n": len(base), "loose": sum(loose(p, norm(" ".join(
                c["quote"] for c in base))) for p in pts),
                "strict": sum(strict(p, base) for p in pts),
                "noise": noise(base, q, pts)},
            "conn": {"n": len(conn), "loose": sum(loose(p, norm(" ".join(
                c["quote"] for c in conn))) for p in pts),
                "strict": sum(strict(p, conn) for p in pts),
                "noise": noise(conn, q, pts)},
            "n_points": len(pts),
            "new_strict": [i + 1 for i in range(len(pts))
                           if strict(pts[i], conn) and not strict(pts[i], base)],
            "lost_strict": [i + 1 for i in range(len(pts))
                            if strict(pts[i], base) and not strict(pts[i], conn)],
        })

    tot = sum(r["n_points"] for r in rows)
    for k in ("base", "conn"):
        print("%-5s strict %d/%d = %.1f%%  loose %d/%d = %.1f%%  pool %.1f  noise %.1f"
              % (k,
                 sum(r[k]["strict"] for r in rows), tot,
                 100.0 * sum(r[k]["strict"] for r in rows) / tot,
                 sum(r[k]["loose"] for r in rows), tot,
                 100.0 * sum(r[k]["loose"] for r in rows) / tot,
                 sum(r[k]["n"] for r in rows) / len(rows),
                 sum(r[k]["noise"] for r in rows) / len(rows)))
    for r in rows:
        if r["new_strict"] or r["lost_strict"]:
            print("  %-24s new=%s lost=%s" % (r["q"][:22], r["new_strict"],
                                               r["lost_strict"]))

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"rows": rows}, f, ensure_ascii=False, indent=1)
    print("wrote", OUT)

    # 单点补测：case11 再加一条「标准金额」规则（第三个槽），看 8000 能不能回来
    q = "国家奖学金和国家励志奖学金能同时拿吗"
    rec = cache[q]
    extra = ["国家奖学金 国家励志奖学金 标准 每生每学年 元 金额"]
    c = app._synth_candidates(rec["queries"] + rec["llm_rules"] + extra,
                              rec["premises"], cap=CAP, question=q)
    print("case11 + 标准金额规则 -> 8000 in pool:",
          any("8000" in norm(x["quote"]) for x in c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
