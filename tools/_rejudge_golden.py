"""用保存过的答案重新判读金标准（不重跑综合层），并支持完整答案长度。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_rejudge_golden.py [score.json]
说明：答案截断从 1500 字放宽到 5000 字——补充层在答案末尾，
      长度一截就把「160 小时」这类最后补上的点判成未命中。
"""
import glob
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

PROMPT = (
    "下面一条【要点】和一段【回答】。回答问题：回答里有没有把这条要点答出来"
    "（同义改写算答到，只说方向但没给具体内容不算）。只输出 JSON："
    "{\"hit\": true/false, \"why\": \"不超过 20 字\"}"
)


def judge(point: str, answer: str) -> dict:
    try:
        raw = app.ds_chat([{"role": "system", "content": PROMPT},
                           {"role": "user", "content": f"【要点】{point}\n\n【回答】{answer[:5000]}"}],
                          max_tokens=100, json_mode=True)
        d = json.loads(raw) or {}
        return {"hit": bool(d.get("hit")), "why": str(d.get("why") or "")[:24]}
    except Exception as e:  # noqa: BLE001
        return {"hit": False, "why": f"err:{type(e).__name__}"}


def main() -> None:
    files = sys.argv[1:] or sorted(
        glob.glob(str(ROOT / "_review_items" / "golden_score_*.json")),
        key=os.path.getmtime)[-1:]
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        tot = hit = 0
        print("=" * 72)
        print(Path(f).name)
        for row in d["rows"]:
            h = 0
            for p in row["points"]:
                p["judge_full"] = judge(p["p"], row["answer"])
                tot += 1
                hit += p["judge_full"]["hit"]
                h += p["judge_full"]["hit"]
                if not p["judge_full"]["hit"]:
                    print(f"    ✗ {p['p'][:40]:42} {p['judge_full']['why'][:20]}")
            print(f"  {h}/{len(row['points'])} | {row['q'][:30]}")
        d["judge_full_cover"] = hit
        out = Path(f).with_name(f"rejudged_{Path(f).name}")
        out.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"覆盖率（判读/不截断）{hit}/{tot} = {round(100 * hit / tot)}% -> {out.name}")


if __name__ == "__main__":
    main()
