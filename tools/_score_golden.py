"""金标准覆盖率评分：系统答案 vs 人工写的「全面答案要点」。

两条判据同时用：
  · 关键词：要点里给的 kw 是否都出现（确定性，会漏同义写法）
  · 模型判读：把要点和答案交给模型，问「这条要点被答到了吗」（认同义改写）
只要有任一条判「覆盖」就算覆盖？不——**两条都判覆盖才算**，宁可算缺口，让缺口暴露出来。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_score_golden.py [answers.jsonl]
  不给 answers.jsonl 时现跑综合层（每题约 15s）并落盘 _review_items/golden_answers_<时间>.jsonl
输出：_review_items/golden_score_<时间>.json + 屏上表格
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

GOLDEN = ROOT / "_review_items" / "golden_20261111.json"
PROMPT = (
    "下面一条【要点】和一段【回答】。回答问题：回答里有没有把这条要点答出来（同义改写算答到，"
    "只说方向但没给具体内容不算）。只输出 JSON：{\"hit\": true/false, \"why\": \"不超过 20 字\"}"
)


def judge_point(point: str, answer: str) -> dict:
    try:
        raw = app.ds_chat([{"role": "system", "content": PROMPT},
                           {"role": "user", "content": f"【要点】{point}\n\n【回答】{answer[:1500]}"}],
                          max_tokens=100, json_mode=True)
        d = json.loads(raw) or {}
        return {"hit": bool(d.get("hit")), "why": str(d.get("why") or "")[:24]}
    except Exception as e:  # noqa: BLE001
        return {"hit": False, "why": f"judge_err:{type(e).__name__}"}


def main() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
    stamp = time.strftime("%H%M%S")
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    answers: dict[str, str] = {}
    if src:
        for line in src.open(encoding="utf-8"):
            r = json.loads(line)
            blob = (r.get("conclusion") or "") + "\n" + "\n".join(
                x.get("text") or "" for x in (r.get("layers") or []))
            answers[r["q"]] = blob
    out_rows = []
    for case in golden:
        q = case["q"]
        if q not in answers:
            s = app.synthesize_answer(q)
            answers[q] = ((s["conclusion"] + "\n" + "\n".join(
                x["text"] for x in s["layers"])) if s else "")
        ans = answers[q]
        rows = []
        for pt in case["points"]:
            kw_hit = all(k in ans for k in pt.get("kw") or [])
            jd = judge_point(pt["p"], ans)
            rows.append({"p": pt["p"], "kw": kw_hit, "judge": jd["hit"],
                         "why": jd["why"], "src": pt.get("src", "")})
        cov = sum(1 for r in rows if r["kw"] and r["judge"])
        loose = sum(1 for r in rows if r["kw"] or r["judge"])
        out_rows.append({"q": q, "answer": ans, "points": rows,
                         "cover": cov, "loose": loose, "total": len(rows)})
        print(f"{cov}/{len(rows)} 严格（宽松 {loose}） | {q}")
        for r in rows:
            mark = "✓" if (r["kw"] and r["judge"]) else ("~" if (r["kw"] or r["judge"]) else "✗")
            print(f"    {mark} {r['p'][:38]:40} kw={int(r['kw'])} judge={int(r['judge'])} {r['why']}")
    tot = sum(r["total"] for r in out_rows)
    got = sum(r["cover"] for r in out_rows)
    loose = sum(r["loose"] for r in out_rows)
    print(f"\n总覆盖率 {got}/{tot} = {round(100 * got / tot)}%（宽松 {round(100 * loose / tot)}%）")
    dst = ROOT / "_review_items" / f"golden_score_{stamp}.json"
    dst.write_text(json.dumps({"rows": out_rows, "cover": got, "loose": loose, "total": tot},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("score ->", dst)


if __name__ == "__main__":
    main()
