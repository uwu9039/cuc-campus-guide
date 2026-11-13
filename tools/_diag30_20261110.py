"""第二批 30 题的取证诊断：拆前提 → 取证 → 挑证据，落盘条款、枚举标注与锚点条款。

目的：**先看条款、后看模型输出**，据此判每题「该答 / 该拒」，避免用模型答案反推标注。
用法：./.venv/Scripts/python.exe -X utf8 -u tools/_diag30_20261110.py
输出：_review_items/compound30_evidence.jsonl
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import app  # noqa: E402
from compound30_20261110 import QUESTIONS  # noqa: E402


def main() -> None:
    out = ROOT / "_review_items/compound30_evidence.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for n, (kind, q) in enumerate(QUESTIONS, 1):
            t0 = time.time()
            status: dict = {}
            try:
                premises, queries = app._synth_plan(q, status)
                cands = app._synth_candidates(queries or premises, premises,
                                              question=q) if premises else []
                ev = app._synth_pick(premises, cands, queries) if cands else []
            except Exception as e:  # noqa: BLE001
                fh.write(json.dumps({"type": kind, "q": q, "error": repr(e)[:160]},
                                    ensure_ascii=False) + "\n")
                print(f"[{n}] ERR {q[:28]}")
                continue
            picked = []
            for i, e in enumerate(ev, 1):
                info = app._closed_enum(e["quote"]) or {}
                picked.append({"idx": i, "doc": e["doc"][:36],
                               "quote": e["quote"][:260],
                               "closed": info.get("closed"),
                               "count": info.get("count"),
                               "must": bool(e.get("must"))})
            rec = {"type": kind, "q": q, "sec": round(time.time() - t0, 1),
                   "premises": premises, "queries": queries,
                   "cands": len(cands), "picked": picked}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            closed = sum(1 for p in picked if p["closed"])
            print(f"[{n}] {rec['sec']}s {kind} picked={len(picked)} enum={closed} | {q[:28]}")
    print("done ->", out)


if __name__ == "__main__":
    main()
