"""检索层 hit@k：目标条目有没有落进 rank() 的前 k 名。

数据来源三套（都已有标注，不新造题）：
- `eval.py` 的 33 条 CASES（只算有期望 id 的；absent 那几条没有目标）
- `eval.py` 的 FAMILY_CASES 同族对照
- `_review_items/golden_20261111.json` 的 12 题（`src` 里写的是条目 id）

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_hit_at_k.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import app  # noqa: E402
import eval as ev  # noqa: E402


def ranks(q: str, want: str) -> int | None:
    """目标条目在 rank 里的名次（1 起）；不在前 50 就算 None。"""
    for i, (it, _sc) in enumerate(app.rank(q)[:50], 1):
        if it.get("id") == want:
            return i
    return None


def report(name: str, cases: list[tuple[str, str]]) -> None:
    n = len(cases)
    hits = {1: 0, 3: 0, 5: 0, 10: 0}
    miss = []
    for q, want in cases:
        r = ranks(q, want)
        for k in hits:
            if r is not None and r <= k:
                hits[k] += 1
        if r is None or r > 5:
            miss.append((q, want, r))
    print(f"\n== {name}（{n} 题）")
    for k in (1, 3, 5, 10):
        print(f"  hit@{k:<2} {hits[k]:>3}/{n} = {hits[k]/n:.1%}")
    if miss:
        print("  未进前 5：")
        for q, want, r in miss[:10]:
            print(f"    {q[:26]:28} 期望 {want:16} 实际名次 {r}")


def main() -> None:
    cases = [(q, exp) for q, exp, _kind in ev.CASES if exp]
    report("eval.py 主集（有期望 id）", cases)

    fam = [(q, exp) for _fam, items in ev.FAMILY_CASES for q, exp in items]
    report("eval.py 同族对照", fam)

    golden = json.loads((ROOT / "_review_items" / "golden_20261111.json")
                        .read_text(encoding="utf-8"))["cases"]
    g = []
    for c in golden:
        for pt in c["points"]:
            src = str(pt.get("src") or "").split("/")[0].strip()
            if src and src in app.ITEM_BY_ID:
                g.append((c["q"], src))
                break
    report("金标准 12 题（每题取首个可解析 src）", g)


if __name__ == "__main__":
    main()
