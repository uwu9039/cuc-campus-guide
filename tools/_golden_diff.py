"""金标准两次跑分的逐点对照：谁从「没答到」变成「答到」，谁掉了。

用法：
    ./.venv/Scripts/python.exe -X utf8 -u tools/_golden_diff.py <before.json> <after.json>

两份 JSON 都是 `tools/_score_golden.py` 的产物（_review_items/golden_score_*.json）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str) -> dict[tuple[str, str], dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for row in data["rows"]:
        for pt in row["points"]:
            out[(row["q"], pt["p"])] = pt
    return out


def total(data_path: str) -> tuple[int, int, int, int]:
    d = json.loads(Path(data_path).read_text(encoding="utf-8"))
    rows = d["rows"]
    judge = sum(1 for r in rows for p in r["points"] if p["judge"])
    both = sum(1 for r in rows for p in r["points"] if p["kw"] and p["judge"])
    loose = sum(1 for r in rows for p in r["points"] if p["kw"] or p["judge"])
    return both, loose, judge, d["total"]


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    a, b = load(sys.argv[1]), load(sys.argv[2])
    keys = sorted(set(a) | set(b))

    gained, lost = [], []
    for k in keys:
        pa, pb = a.get(k), b.get(k)
        before = bool(pa and pa["kw"] and pa["judge"])
        after = bool(pb and pb["kw"] and pb["judge"])
        if not before and after:
            gained.append(k)
        elif before and not after:
            lost.append(k)

    for name, path in (("前", sys.argv[1]), ("后", sys.argv[2])):
        both, loose, judge, tot = total(path)
        print(f"{name}：严格 {both}/{tot} = {both/tot:.0%}　宽松 {loose}/{tot} = {loose/tot:.0%}　"
              f"判读 {judge}/{tot} = {judge/tot:.0%}")

    print(f"\n新增答到（{len(gained)}）")
    for q, p in gained:
        print(f"  + {q[:20]} | {p[:52]}")
    print(f"\n掉下来的（{len(lost)}）")
    for q, p in lost:
        print(f"  - {q[:20]} | {p[:52]}")

    per_q: dict[str, list[int]] = {}
    for k, pt in b.items():
        q = k[0]
        cur = per_q.setdefault(q, [0, 0])
        cur[1] += 1
        if pt["kw"] and pt["judge"]:
            cur[0] += 1
    print("\n逐题（后）")
    for q, (c, t) in sorted(per_q.items(), key=lambda x: x[1][0] / x[1][1]):
        print(f"  {c}/{t}  {q}")


if __name__ == "__main__":
    main()
