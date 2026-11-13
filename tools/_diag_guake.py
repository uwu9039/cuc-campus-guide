"""诊断：热题「挂科了还能保研吗」的四条要点，丢在哪一段。

链路三段分开看：plan（拆前提/检索短句）→ pool（候选池）→ pick（挑进证据）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

Q = "挂科了还能保研吗？补考通过算吗？"
KEYS = {
    "5项条件": "推荐对象须具备",
    "无挂科条款": "无挂科",
    "成绩优秀": "成绩优秀",
    "60分计入": "60 分",
    "GPA": "GPA",
    "综合成绩": "综合评价成绩",
}


def has(text: str) -> dict[str, bool]:
    return {k: (v in text) for k, v in KEYS.items()}


def main() -> None:
    ranked = app.rank(Q)
    print("rank top3:", [(i.get("title", "")[:26], s) for i, s in ranked[:3]])
    top, sc = ranked[0]
    print(f"top={top.get('id')} score={sc}\n")

    status: dict = {}
    premises, queries = app._synth_plan(Q, status)
    print("premises:")
    for p in premises:
        print("  -", p)
    print("queries:", queries, "\n")

    cands = app._synth_candidates(queries or premises, premises, question=Q, item=None)
    pool_text = " ".join(c.get("quote", "") for c in cands)
    print(f"pool={len(cands)} 条；池内命中:", has(pool_text))

    ev = app._synth_pick(premises, cands, queries)
    ev_text = " ".join(e.get("quote", "") for e in ev)
    print(f"picked={len(ev)} 条；证据内命中:", has(ev_text))
    print()
    for i, e in enumerate(ev, 1):
        print(f"[{i}] {str(e.get('doc'))[:14]} | {str(e.get('quote'))[:88].replace(chr(10),' ')}")

    # 池里到底有没有「推免基本条件」那条
    print("\n池内含『推荐对象须具备』的候选：")
    for c in cands:
        if "推荐对象须具备" in c.get("quote", ""):
            print("  ·", str(c.get("quote"))[:120].replace("\n", " "))


if __name__ == "__main__":
    main()
