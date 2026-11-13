"""把「判读结果」按人工标注汇总成两张表：该答未答 / 该拒乱答。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_score30.py before after
      （每个参数是 judged_ 后面的文件名片段，如 before / after）
输入：_review_items/judged_compound30_<tag>.jsonl、judged_controls6_<tag>.jsonl（有则读）
      _review_items/compound30_labels_20261110.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = json.loads((ROOT / "_review_items/compound30_labels_20261110.json")
                    .read_text(encoding="utf-8"))


def load(tag: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for name in (f"judged_compound30_{tag}.jsonl", f"judged_controls6_{tag}.jsonl"):
        p = ROOT / "_review_items" / name
        if not p.exists():
            continue
        for line in p.open(encoding="utf-8"):
            rec = json.loads(line)
            rows[rec["q"]] = rec
    return rows


def report(tag: str) -> dict:
    rows = load(tag)
    out = {"tag": tag, "n": len(rows)}
    ans = LABELS["answer"]
    ref = LABELS["refuse"]
    eth = LABELS["either"]
    got = {q: rows.get(q) for q in ans + ref + eth}
    miss = [q for q, r in got.items() if r is None]
    out["missing"] = len(miss)

    def kind(q: str) -> str:
        r = got.get(q) or {}
        return (r.get("judge") or {}).get("kind") or "no_output"

    out["answer_n"] = len([q for q in ans if q in rows])
    out["answer_refused"] = [q for q in ans if kind(q) == "refused"]
    out["answer_mixed"] = [q for q in ans if kind(q) == "mixed"]
    out["answer_ok"] = [q for q in ans if kind(q) == "answered"]
    out["refuse_n"] = len([q for q in ref if q in rows])
    out["refuse_answered"] = [q for q in ref if kind(q) == "answered"]
    out["refuse_mixed"] = [q for q in ref if kind(q) == "mixed"]
    out["refuse_ok"] = [q for q in ref if kind(q) == "refused"]
    out["either_answered"] = [q for q in eth if kind(q) == "answered"]
    out["either_refused"] = [q for q in eth if kind(q) == "refused"]
    out["either_mixed"] = [q for q in eth if kind(q) == "mixed"]
    out["overclaim"] = {q: r.get("overclaim") for q, r in got.items()
                        if r and r.get("overclaim")}
    return out


def show(o: dict) -> None:
    print("=" * 74)
    print(f"[{o['tag']}] 已判 {o['n']} 题（缺 {o['missing']}）")
    a = o["answer_n"]
    print(f"  该答（{a} 题）：作答 {len(o['answer_ok'])} / 含糊 {len(o['answer_mixed'])}"
          f" / 拒答 {len(o['answer_refused'])}  → 该答未答 {len(o['answer_refused'])}")
    r = o["refuse_n"]
    print(f"  该拒（{r} 题）：拒答 {len(o['refuse_ok'])} / 含糊 {len(o['refuse_mixed'])}"
          f" / 作答 {len(o['refuse_answered'])}  → 该拒乱答 {len(o['refuse_answered'])}")
    print(f"  半答类（{len(o['either_answered']) + len(o['either_mixed']) + len(o['either_refused'])} 题）："
          f"作答 {len(o['either_answered'])} / 含糊 {len(o['either_mixed'])}"
          f" / 拒答 {len(o['either_refused'])}")
    if o["overclaim"]:
        print(f"  越界（数字/条款号不在证据里）{len(o['overclaim'])} 题：")
        for q, bad in list(o["overclaim"].items())[:6]:
            print(f"    · {q[:26]} → {bad}")
    if o["answer_refused"]:
        print("  该答未答明细：")
        for q in o["answer_refused"]:
            print(f"    · {q[:34]}")
    if o["refuse_answered"]:
        print("  该拒乱答明细：")
        for q in o["refuse_answered"]:
            print(f"    · {q[:34]}")


if __name__ == "__main__":
    for tag in (sys.argv[1:] or ["before", "after"]):
        o = report(tag)
        show(o)
        (ROOT / "_review_items" / f"score_{tag}_20261110.json").write_text(
            json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
