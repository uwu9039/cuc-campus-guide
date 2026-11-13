"""对照：金标准「裸调 synthesize_answer」vs「走真实入口（首轮锚定 + 条目证据注入）」。

金标准脚本 `_score_golden.py` 直接调 `app.synthesize_answer(q)`，不给 item；
产品里 `/api/ask` 会先用 rank 锚定条目再调。这两个口径差多少，这里量一下。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import app  # noqa: E402
from _score_golden import judge_point  # noqa: E402

CASES = ["转专业以后宿舍要换吗", "勤工助学一小时多少钱？一个月最多干多久",
         "记过处分会影响入党吗", "国家奖学金一年发多少钱"]


def anchor(q: str):
    ranked = app.rank(q)
    if not ranked:
        return None, ""
    top, sc = ranked[0]
    if sc < 85 or top.get("auto") or top.get("clause") or top.get("para"):
        return None, f"top={sc} 不锚"
    lead = sc - (ranked[1][1] if len(ranked) > 1 else 0)
    qb = app.bigrams(app.norm(q))
    tb = app.bigrams(app.norm(str(top.get("title") or "") + " " + " ".join(top.get("aliases") or [])))
    shared = (qb & tb) - app.NOISE_BIGRAMS
    if lead >= 10 or len(shared) >= 2:
        return top, f"锚定 {top['id']} (sc={sc}, lead={lead}, shared={len(shared)})"
    return None, f"不锚 {top['id']} (lead={lead}, shared={len(shared)})"


def main() -> None:
    import json
    golden = json.loads((Path(app.__file__).parent / "_review_items" /
                         "golden_20261111.json").read_text(encoding="utf-8"))["cases"]
    for q in CASES:
        case = next(c for c in golden if c["q"] == q)
        it, why = anchor(q)
        print(f"\n=== {q}\n  锚定: {why}")
        for tag, item in (("裸调", None), ("带锚点", it)):
            s = app.synthesize_answer(q, item=item)
            if not s:
                print(f"  [{tag}] synth 失败"); continue
            ans = s["conclusion"] + "\n" + "\n".join(x["text"] for x in s["layers"])
            cov = 0
            for pt in case["points"]:
                kw = all(any(x in ans for x in k.split("|")) for k in pt.get("kw") or [])
                jd = judge_point(pt["p"], ans)["hit"]
                cov += 1 if (kw and jd) else 0
            judge = sum(1 for pt in case["points"] if judge_point(pt["p"], ans)["hit"])
            print(f"  [{tag}] 严格 {cov}/{len(case['points'])}　判读 {judge}/{len(case['points'])}")


if __name__ == "__main__":
    main()
