"""诊断：30 条「保守」复合题的取证全貌 —— 逐条跑 拆前提→取证→挑证据，
落盘 picked evidence 与「闭集枚举」标注，用来判断 62% 里有多少是 could-answer、
多少是该继续拒答。

只读 app 的现有函数，不改任何东西。
用法：.venv/Scripts/python.exe -X utf8 -u tools/_synth_diag_20261110.py
输出：_review_items/synth_diag_20261110.jsonl
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

# —— 闭集枚举检测（候选实现，先在这里验证，再决定是否进 app.py） ——
_MARKS = [
    re.compile(r"[（(]\s*([一二三四五六七八九十]{1,2}|\d{1,2})\s*[）)]"),
    re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]"),
    re.compile(r"(?<![0-9])([1-9])[.、](?=[^\d])"),
]
_CLOSED_INTRO = re.compile(
    r"(具备以下|符合以下|下列|以下基本条件|以下条件|具备下列|符合下列|之一者|以下之一"
    r"|须同时|应同时|均须|必须同时|条件者)")
_OPEN_HINT = re.compile(r"(包括但不限于|诸如|例如|参照执行|等[。；;]?$)")
_TAIL_OK = re.compile(r"[。；;]$")


def enum_of(quote: str) -> dict | None:
    """从一段引文里切出枚举项；≥3 项才算「列表」，带穷尽引语才算「闭集」。"""
    best = None
    for pat in _MARKS:
        marks = list(pat.finditer(quote))
        if len(marks) < 3:
            continue
        items = []
        for i, m in enumerate(marks):
            s = m.start()
            e = marks[i + 1].start() if i + 1 < len(marks) else len(quote)
            items.append(quote[s:e].strip(" 　；;。"))
        head = quote[:marks[0].start()]
        closed = bool(_CLOSED_INTRO.search(head)) and not _OPEN_HINT.search(head)
        # 引文被截断时最后一项没有标点，不能断言「就这些」
        if not _TAIL_OK.search(quote.strip()):
            closed = False
        info = {"count": len(items), "closed": closed,
                "scope": head[-30:].strip(), "items": items}
        if best is None or (info["closed"], info["count"]) > (best["closed"], best["count"]):
            best = info
    return best


def terms_of(text: str) -> set[str]:
    return {g for g in app.bigrams(app.norm(text)) if g not in app._TOPIC_STOP}


def main() -> None:
    rows = [json.loads(l) for l in
            open("_review_items/eval100.jsonl", encoding="utf-8")]
    cons = [r for r in rows if r["mode"] == "compound" and r.get("conclusion")
            and ("证据里没有写" in r["conclusion"] or "没有直接写" in r["conclusion"])]
    out = Path("_review_items/synth_diag_20261110.jsonl")
    with out.open("w", encoding="utf-8") as fh:
        for n, r in enumerate(cons, 1):
            q = r["q"]
            t0 = time.time()
            status = {}
            try:
                premises, queries = app._synth_plan(q, status)
                cands = app._synth_candidates(queries or premises, premises, question=q) if premises else []
                ev = app._synth_pick(premises, cands, queries) if cands else []
            except Exception as e:  # noqa: BLE001
                fh.write(json.dumps({"q": q, "error": repr(e)[:200]}, ensure_ascii=False) + "\n")
                print(f"[{n}] ERR {q}")
                continue
            qb = terms_of(q)
            picked = []
            for i, e in enumerate(ev, 1):
                info = enum_of(e["quote"])
                picked.append({
                    "idx": i, "doc": e["doc"][:34], "quote": e["quote"][:280],
                    "enum": info,
                    "overlap": len(qb & terms_of(e["quote"])),
                })
            rec = {"q": q, "sec_retrieval": round(time.time() - t0, 1),
                   "premises": premises, "queries": queries,
                   "cands": len(cands), "picked": len(ev),
                   "closed_enums": sum(1 for p in picked if p["enum"] and p["enum"]["closed"]),
                   "picked_ev": picked,
                   "old_conclusion": r["conclusion"]}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{n}] {rec['sec_retrieval']}s picked={rec['picked']} "
                  f"closed={rec['closed_enums']} | {q[:34]}")
    print("done ->", out)


if __name__ == "__main__":
    main()
