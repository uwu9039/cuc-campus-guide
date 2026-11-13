"""把一批问句的 rank() 结果 dump 成 JSON，给「开关关掉是否等于改动前」做 diff。

用法（两个独立进程，各自跑一遍，再 diff 输出）：

    ./.venv/Scripts/python.exe -X utf8 tools/probe_rank_diff.py --out _before.json
    SECTIONS_BOOST=0 ./.venv/Scripts/python.exe -X utf8 tools/probe_rank_diff.py --out _after_off.json

    ./.venv/Scripts/python.exe -X utf8 tools/probe_rank_diff.py --diff _before.json _after_off.json

--module 可以换成任何与 app 接口相同的模块（如把改动前的 app.py 存成 _ref_app.py），
这样「关＝原样」就是在两份代码之间比，而不是自己跟自己比。

只比 id 与分数：rank() 返回的条目对象里其他字段不参与排序，改它不算回归。
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

TOP = 8
DEFAULT_QS = ROOT / "_review_items" / "diff_queries_50.txt"


def load_queries(path: Path) -> list[str]:
    out = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    return [q for q in out if q and not q.startswith("#")]


def dump(module: str, queries: list[str]) -> dict:
    mod = importlib.import_module(module)
    res: dict[str, list] = {}
    for q in queries:
        ranked = mod.rank(q)
        res[q] = [[it["id"], int(sc)] for it, sc in ranked[:TOP]]
    return res


def do_diff(a: Path, b: Path) -> int:
    da = json.loads(a.read_text(encoding="utf-8"))
    db = json.loads(b.read_text(encoding="utf-8"))
    keys = list(dict.fromkeys(list(da) + list(db)))
    bad = 0
    for q in keys:
        ra, rb = da.get(q), db.get(q)
        if ra != rb:
            bad += 1
            print(f"✗ {q}\n   {a.name}: {ra}\n   {b.name}: {rb}")
    if not bad:
        print(f"✓ {len(keys)} 条问句，top{TOP} 的 id 与分数完全一致（{a.name} vs {b.name}）")
    else:
        print(f"✗ {bad}/{len(keys)} 条不一致")
    return 1 if bad else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", default="app")
    ap.add_argument("--queries", default=str(DEFAULT_QS))
    ap.add_argument("--out", default="")
    ap.add_argument("--diff", nargs=2, metavar=("A", "B"))
    args = ap.parse_args()

    if args.diff:
        sys.exit(do_diff(Path(args.diff[0]), Path(args.diff[1])))

    res = dump(args.module, load_queries(Path(args.queries)))
    out = Path(args.out) if args.out else ROOT / f"_rank_{args.module}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {len(res)} 条问句 → {out}")


if __name__ == "__main__":
    main()
