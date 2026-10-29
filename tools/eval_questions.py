"""用问道 204 题跑本地问答，输出可逐条阅读的结构化结果。

用法：
    python tools/eval_questions.py                 # 规则模式
    python tools/eval_questions.py --llm           # 开启模型裁决 / Rerank
    python tools/eval_questions.py --llm --out aia-runs/local-answers-llm.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402

QFILE = ROOT / "aia-runs" / "questions-expanded.txt"


def first_text(resp: dict) -> str:
    for a in resp.get("answers") or []:
        t = a.get("text")
        if t:
            return t
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    qs = [ln.strip() for ln in QFILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if args.limit:
        qs = qs[: args.limit]
    out_path = Path(args.out) if args.out else (
        ROOT / "aia-runs" / ("local-answers-llm.jsonl" if args.llm else "local-answers-rule.jsonl"))

    rows = []
    t0 = time.time()
    stats = {"n": 0, "matched": 0, "info": 0, "ambiguous": 0, "quotes": 0,
             "disambiguate": 0, "original": 0, "llm": 0, "empty_answer": 0}
    for n, q in enumerate(qs, 1):
        try:
            r = app.answer_question(q, {}, router_llm=args.llm)
        except Exception as e:  # noqa: BLE001
            r = {"matched": False, "error": f"{type(e).__name__}: {e}", "answers": []}
        item = r.get("item") or {}
        text = first_text(r)
        row = {
            "n": n, "q": q,
            "matched": bool(r.get("matched")),
            "item": item.get("id") or "",
            "title": item.get("title") or "",
            "confidence": r.get("confidence"),
            "band": r.get("band"),
            "ambiguous": bool(r.get("ambiguous")),
            "disambiguate": len(r.get("disambiguate") or []),
            "answer": text,
            "answers_n": len(r.get("answers") or []),
            "quotes": len(r.get("quotes") or []),
            "original_search": len(r.get("original_search") or []),
            "related_items": len(r.get("related_items") or []),
            "rule_unsure": bool(r.get("rule_unsure")),
            "resolved_by_llm": bool(r.get("resolved_by_llm")),
            "llm_answer": bool(r.get("llm_answer")),
            "error": r.get("error") or "",
        }
        rows.append(row)
        stats["n"] += 1
        stats["matched"] += row["matched"]
        stats["info"] += bool(text)
        stats["ambiguous"] += row["ambiguous"]
        stats["quotes"] += row["quotes"] > 0
        stats["disambiguate"] += row["disambiguate"] > 0
        stats["original"] += row["original_search"] > 0
        stats["llm"] += row["resolved_by_llm"] or row["llm_answer"]
        stats["empty_answer"] += row["matched"] and not text

    out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    dur = time.time() - t0
    print(f"题目 {stats['n']}，用时 {dur:.1f}s，平均 {dur / max(1, stats['n']):.2f}s/题")
    print(f"命中事项 {stats['matched']} / 有答案正文 {stats['info']} / 命中但无正文 {stats['empty_answer']}")
    print(f"反问/歧义 {stats['ambiguous']}（选项 {stats['disambiguate']}）/ 带原文引文 {stats['quotes']}")
    print(f"仅原文线索 {stats['original']} / 模型参与 {stats['llm']}")
    print(f"结果写入 {out_path}")


if __name__ == "__main__":
    main()
