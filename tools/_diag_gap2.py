"""诊断两个漏点：国奖 10000 的干净条款为什么进不了池；转专业宿舍的答案条目在哪。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402


def which_item(pid: str) -> dict | None:
    for it in app.ITEMS:
        for v in (it.get("evidence") or {}).values():
            for one in app._ev_items(v):
                if str((one or {}).get("src") or "") == pid:
                    return it
    return None


def main() -> None:
    print("== 国奖：干净的 10000 条款在哪条 item 里，它进没进 rank/bm25")
    for pid in ("pt-1cafb5ca2f", "pt-491944ac4a", "pt-0ff9259129"):
        it = which_item(pid)
        print(f"  {pid} -> item={it.get('id') if it else None} title={str((it or {}).get('title'))[:30]}")
    q = "国家奖学金一年发多少钱"
    st: dict = {}
    prem, qs = app._synth_plan(q, st)
    for t in qs:
        ids = [i.get("id") for i, _ in app.rank(t)[:8]]
        bm = [i.get("id") for i, _ in app.bm25_hits(t, k=20)]
        print(f"  [{t[:26]}] rank={ids[:4]} bm25in={[x for x in bm if x][:4]}")

    cands = app._synth_candidates(qs, prem, question=q, item=None)
    quotes = " ".join(c.get("quote", "") for c in cands)
    print("  pool:", len(cands), "| 干净条款在池:", "每年奖励12万名" in quotes,
          "| 碎片在池:", "勤奋学习积极进取" in quotes)

    print("\n== 转专业宿舍：sushe-huansu 在不在池里")
    q2 = "转专业以后宿舍要换吗"
    st2: dict = {}
    prem2, qs2 = app._synth_plan(q2, st2)
    cands2 = app._synth_candidates(qs2, prem2, question=q2, item=None)
    ids2 = {c.get("item_id") for c in cands2}
    print("  pool:", len(cands2), "| sushe-huansu 在池:", "sushe-huansu" in ids2)
    for c in cands2:
        if c.get("item_id") == "sushe-huansu":
            print("   ·", str(c.get("quote"))[:80])


if __name__ == "__main__":
    main()
