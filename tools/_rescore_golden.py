"""从已保存的 golden_score_*.json 重算覆盖率（不调模型）。

用途：改了关键词判据后，复用当时的答案与模型判读结果重新汇总，避免再花一次生成。
用法：./.venv/Scripts/python.exe -X utf8 -u tools/_rescore_golden.py [score.json ...]
"""
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "_review_items" / "golden_20261111.json"


def kw_hit(tokens: list[str], ans: str) -> bool:
    """token 之间是 AND，token 内用 | 表示 OR。"""
    for tok in tokens:
        if not any(alt.strip() and alt.strip() in ans for alt in tok.split("|")):
            return False
    return True


def main() -> None:
    gold = {c["q"]: c for c in json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]}
    files = sys.argv[1:] or sorted(
        glob.glob(str(ROOT / "_review_items" / "golden_score_*.json")),
        key=os.path.getmtime)[-1:]
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        tot = strict = loose = 0
        print("=" * 70)
        print(Path(f).name)
        for row in d["rows"]:
            case = gold.get(row["q"], {})
            points = case.get("points", [])
            s = l = 0
            for i, p in enumerate(row["points"]):
                kw = kw_hit(points[i].get("kw", []) if i < len(points) else [], row["answer"])
                jd = p["judge"]
                tot += 1
                s += kw and jd
                l += kw or jd
            strict += s
            loose += l
            print(f"  {s}/{len(row['points'])} 严格（宽松 {l}） | {row['q'][:26]}")
        print(f"总覆盖率 {strict}/{tot} = {round(100*strict/tot)}%（宽松 {round(100*loose/tot)}%）")


if __name__ == "__main__":
    main()
