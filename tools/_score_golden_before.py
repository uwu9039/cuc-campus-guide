"""用「改前快照」（_app_before.py）跑同一套金标准，供前后对比。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_score_golden_before.py
输出：_review_items/golden_before_<时间>.json（含答案与逐点判读，判读不截断答案）
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import app  # noqa: E402
from _judge30 import overclaim  # noqa: E402

PROMPT = (
    "下面一条【要点】和一段【回答】。回答问题：回答里有没有把这条要点答出来"
    "（同义改写算答到，只说方向但没给具体内容不算）。只输出 JSON："
    "{\"hit\": true/false, \"why\": \"不超过 20 字\"}"
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


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
    old = load(ROOT / "_app_before.py", "app_before")
    golden = json.loads((ROOT / "_review_items" / "golden_20261111.json")
                        .read_text(encoding="utf-8"))["cases"]
    rows = []
    hit = tot = 0
    for case in golden:
        s = old.synthesize_answer(case["q"])
        answer = "" if not s else (s["conclusion"] + "\n" +
                                   "\n".join(x["text"] for x in s["layers"]))
        pts = []
        for p in case["points"]:
            j = judge(p["p"], answer)
            pts.append({"p": p["p"], "judge": j["hit"], "why": j["why"]})
            tot += 1
            hit += j["hit"]
        rows.append({"q": case["q"], "answer": answer, "points": pts})
        print(f"  {sum(x['judge'] for x in pts)}/{len(pts)} | {case['q'][:26]}")
    out = ROOT / "_review_items" / f"golden_before_{time.strftime('%H%M%S')}.json"
    out.write_text(json.dumps({"rows": rows, "cover": hit, "total": tot},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"改前覆盖率 {hit}/{tot} = {round(100 * hit / tot)}% -> {out.name}")


if __name__ == "__main__":
    main()
