"""按人工标注汇总判读结果：该答未答 / 该拒乱答 / 越界，可对任意题目集合跑。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_score_sets.py <labels.json> <judged1.jsonl> [...]
labels.json 需要 answer / either / refuse 三个数组（问题原文，与评测集里的 q 一致）。
输出：每题一行的判定 + 汇总表；汇总另存 _review_items/score_<judged 名>.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def report(labels: dict, rows: list[dict], name: str) -> dict:
    by_q = {r["q"]: r for r in rows}
    ans, ref, eth = labels["answer"], labels["refuse"], labels["either"]

    def kind(q: str) -> str:
        r = by_q.get(q)
        if r is None:
            return "missing"
        return (r.get("judge") or {}).get("kind") or "no_output"

    out = {"name": name, "n": len(rows),
           "answer_n": len([q for q in ans if q in by_q]),
           "answer_ok": [q for q in ans if kind(q) == "answered"],
           "answer_mixed": [q for q in ans if kind(q) == "mixed"],
           "answer_refused": [q for q in ans if kind(q) == "refused"],
           "refuse_n": len([q for q in ref if q in by_q]),
           "refuse_ok": [q for q in ref if kind(q) == "refused"],
           "refuse_mixed": [q for q in ref if kind(q) == "mixed"],
           "refuse_answered": [q for q in ref if kind(q) == "answered"],
           "either_answered": [q for q in eth if kind(q) == "answered"],
           "either_mixed": [q for q in eth if kind(q) == "mixed"],
           "either_refused": [q for q in eth if kind(q) == "refused"],
           "overclaim": {q: r.get("overclaim") for q, r in by_q.items() if r.get("overclaim")}}
    return out


def show(o: dict) -> None:
    a, r = o["answer_n"], o["refuse_n"]
    print("=" * 78)
    print(f"[{o['name']}] 共 {o['n']} 题；标注覆盖 该答 {a} / 该拒 {r}")
    if a:
        print(f"  该答未答 {len(o['answer_refused'])}/{a}"
              f"（作答 {len(o['answer_ok'])}、含糊 {len(o['answer_mixed'])}、"
              f"拒答 {len(o['answer_refused'])}）")
    if r:
        print(f"  该拒乱答 {len(o['refuse_answered'])}/{r}"
              f"（拒答 {len(o['refuse_ok'])}、含糊 {len(o['refuse_mixed'])}、"
              f"作答 {len(o['refuse_answered'])}）")
    if o["overclaim"]:
        print(f"  越界（回答里的数字/条款号不在证据里）{len(o['overclaim'])} 题")
    if o["answer_refused"]:
        print("  该答未答：")
        for q in o["answer_refused"]:
            print("    ·", q[:40])
    if o["refuse_answered"]:
        print("  该拒乱答（给了库里没有的结论）：")
        for q in o["refuse_answered"]:
            print("    ·", q[:40])


def main() -> None:
    labels = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for name in sys.argv[2:]:
        p = Path(name)
        if not p.exists():
            p = ROOT / "_review_items" / name
        rows = [json.loads(line) for line in p.open(encoding="utf-8")]
        o = report(labels, rows, p.stem)
        show(o)
        (ROOT / "_review_items" / f"score_{p.stem}.json").write_text(
            json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
