"""金标准单臂跑分：指定 app.py 副本、每题重复 N 次、逐点多数表决。

为什么要它：
- `_score_golden.py` 每题只生成一次，44 点里单点抖动就能让总分上下 3 点，
  没法判断「改动是否真的提升」。
- 这里同一题跑 N 次，某点被 ≥ceil(N/2) 次判到才算「答到」，把生成随机性压下去。

用法：
    ./.venv/Scripts/python.exe -X utf8 -u tools/_golden_arm.py --app app.py --repeat 3 --out _review_items/arm_now.json
    ./.venv/Scripts/python.exe -X utf8 -u tools/_golden_arm.py --app _baseline_app.py --repeat 3 --out _review_items/arm_base.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from _score_golden import judge_point  # noqa: E402


def load_app(path: Path):
    spec = importlib.util.spec_from_file_location("arm_app", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", default=str(ROOT / "app.py"))
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    app = load_app(Path(args.app))
    golden = json.loads((ROOT / "_review_items" / "golden_20261111.json")
                        .read_text(encoding="utf-8"))["cases"]
    rows = []
    t0 = time.time()
    for case in golden:
        q = case["q"]
        answers = []
        for _ in range(args.repeat):
            s = app.synthesize_answer(q)
            if not s:
                answers.append("")
                continue
            answers.append(s["conclusion"] + "\n"
                           + "\n".join(x["text"] for x in s["layers"]) + "\n"
                           + (s.get("boundary") or ""))
        pts = []
        for pt in case["points"]:
            judges = [judge_point(pt["p"], a)["hit"] for a in answers]
            kws = [all(any(x in a for x in k.split("|")) for k in pt.get("kw") or [])
                   for a in answers]
            need = (args.repeat + 1) // 2
            pts.append({"p": pt["p"], "judge": sum(judges) >= need,
                        "kw": sum(kws) >= need,
                        "hits": sum(judges), "n": args.repeat})
        cov = sum(1 for x in pts if x["judge"] and x["kw"])
        loose = sum(1 for x in pts if x["judge"] or x["kw"])
        rows.append({"q": q, "points": pts, "cover": cov,
                     "loose": loose, "total": len(pts)})
        print(f"{cov}/{len(pts)} | {q}  ({time.time()-t0:.0f}s)", flush=True)

    tot = sum(r["total"] for r in rows)
    cov = sum(r["cover"] for r in rows)
    loose = sum(r["loose"] for r in rows)
    judge = sum(1 for r in rows for x in r["points"] if x["judge"])
    print(f"\n严格 {cov}/{tot} = {cov/tot:.0%}　宽松 {loose}/{tot} = {loose/tot:.0%}　"
          f"判读 {judge}/{tot} = {judge/tot:.0%}")
    Path(args.out).write_text(json.dumps(
        {"rows": rows, "cover": cov, "loose": loose, "judge": judge, "total": tot,
         "repeat": args.repeat, "app": args.app}, ensure_ascii=False, indent=1),
        encoding="utf-8")


if __name__ == "__main__":
    main()
