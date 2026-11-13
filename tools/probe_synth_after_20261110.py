"""人审对照：5 个已知失败案例 + 1 个「本来就该拒答」的对照，逐题跑新链路并打印。

用法：.venv/Scripts/python.exe -X utf8 -u tools/probe_synth_after_20261110.py
输出：_review_items/synth_after_spot_20261110.jsonl（同时打印摘要）
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

CASES = [
    "挂科了还能保研吗？补考通过算吗？",                    # 本可推断（成绩优秀＋重考60分）
    "四六级没过能毕业吗？能保研吗？",                      # 本可否定（条款未列四六级）
    "校园卡冻结了，奖学金还能打进卡里吗？",                # 本可两步推断
    "辅修和微专业能同时修吗？成绩怎么算？",                # 本可分开说范围
    "推免和支教保研能同时报吗？",                          # 未发现互斥条款
    "我宿舍电费超了，学校会不会直接断电？怎么恢复？",      # 对照：数据本身没有，应继续拒答
]


def main() -> None:
    out = Path("_review_items/synth_after_spot_20261110.jsonl")
    with out.open("w", encoding="utf-8") as fh:
        for n, q in enumerate(CASES, 1):
            t0 = time.time()
            try:
                s = app.synthesize_answer(q)
            except Exception as e:  # noqa: BLE001
                print(f"[{n}] ERR {e!r}")
                continue
            sec = round(time.time() - t0, 1)
            if not s:
                print(f"[{n}] {sec}s 综合层未返回")
                continue
            rec = {"q": q, "sec": sec, "conclusion": s["conclusion"],
                   "layers": s["layers"], "boundary": s["boundary"],
                   "warnings": s["warnings"], "verdicts": s["verdicts"],
                   "evidence": [{"doc": e["doc"][:30], "quote": e["quote"][:90],
                                 "enum": (e.get("enum") or {}).get("count") if e.get("enum") else None,
                                 "closed": (e.get("enum") or {}).get("closed"),
                                 "must": bool(e.get("must"))} for e in s["evidence"]]}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print("=" * 76)
            print(f"[{n}] {sec}s  {q}")
            print("  结论:", s["conclusion"])
            for one in s["layers"]:
                print(f"  · {one['name']}[{one.get('verdict')}]: {one['text']}")
            print("  边界:", s["boundary"])
            print("  裁决:", s["verdicts"], "| 证据",
                  sum(1 for e in s["evidence"] if (e.get("enum") or {}).get("closed")), "条穷尽枚举")
            print("  提醒:", s["warnings"])
    print("done ->", out)


if __name__ == "__main__":
    main()
