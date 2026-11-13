"""复合题回归：同一套 50 题重跑综合层，落盘与 eval_100.py 同口径（便于前后对比）。

用法：.venv/Scripts/python.exe -X utf8 -u tools/eval_synth_after_20261110.py <输出文件名>
输出：_review_items/<输出文件名>，每题一行，字段与 eval100.jsonl 的 compound 行对齐，
      另加 verdicts / warnings / enum_closed / must 四个新字段。
"""
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import app  # noqa: E402
from eval_100 import COMPOUND_PLAIN, COMPOUND_VAGUE  # noqa: E402


def run(q: str, kind: str) -> dict:
    t0 = time.time()
    try:
        s = app.synthesize_answer(q)
    except Exception:  # noqa: BLE001
        return {"mode": "compound", "kind": kind, "q": q,
                "error": traceback.format_exc()[-200:]}
    sec = round(time.time() - t0, 1)
    if not s:
        return {"mode": "compound", "kind": kind, "q": q, "sec": sec, "synth": None}
    return {
        "mode": "compound", "kind": kind, "q": q, "sec": sec,
        "conclusion": s["conclusion"],
        "layers": [{"name": x["name"], "verdict": x.get("verdict"), "text": x["text"]}
                   for x in s["layers"]],
        "boundary": s["boundary"], "warnings": s["warnings"],
        "verdicts": s.get("verdicts"),
        "evidence_count": len(s["evidence"]),
        "enum_closed": sum(1 for e in s["evidence"] if (e.get("enum") or {}).get("closed")),
        "must": sum(1 for e in s["evidence"] if e.get("must")),
        "evidence_docs": [e["doc"][:30] for e in s["evidence"]],
    }


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "eval100_synth_after_20261110.jsonl"
    out = Path("_review_items") / name
    n = ok = cons = 0
    with out.open("w", encoding="utf-8") as fh:
        for kind, group in (("plain", COMPOUND_PLAIN), ("vague", COMPOUND_VAGUE)):
            for q in group:
                rec = run(q, kind)
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                n += 1
                if rec.get("conclusion"):
                    ok += 1
                    if ("证据里没有写" in rec["conclusion"]
                            or "没有直接写" in rec["conclusion"]):
                        cons += 1
                print(f"[{n}] {rec.get('sec')}s "
                      f"{'保守' if rec.get('conclusion') and ('证据里没有写' in rec['conclusion'] or '没有直接写' in rec['conclusion']) else ('失败' if not rec.get('conclusion') else '作答')}"
                      f" | {q}")
    print(f"done {n} -> {out}")
    print(f"复合成功 {ok}/{n}，其中结论含保守语 {cons}/{ok} "
          f"({round(100 * cons / ok, 1) if ok else 0}%)")


if __name__ == "__main__":
    main()
