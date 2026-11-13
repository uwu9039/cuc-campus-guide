"""不调模型，只按新规则重算已判记录里的「越界」字段（改判据后补算用）。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_recheck_overclaim.py judged_*.jsonl
原地覆盖对应文件的 overclaim 字段，并在 stdout 打一张表。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from _judge30 import overclaim  # noqa: E402


def main() -> None:
    for name in sys.argv[1:]:
        p = Path(name)
        if not p.exists():
            p = ROOT / "_review_items" / name
        rows = [json.loads(line) for line in p.open(encoding="utf-8")]
        hits = 0
        for rec in rows:
            rec["overclaim"] = overclaim(rec)
            if rec["overclaim"]:
                hits += 1
                print(f"  · {rec['q'][:30]} → {rec['overclaim']}")
        with p.open("w", encoding="utf-8") as fh:
            for rec in rows:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{p.name}] 越界 {hits}/{len(rows)}")


if __name__ == "__main__":
    main()
