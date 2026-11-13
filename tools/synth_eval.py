"""综合层评测：同一批关系题，看结论/分层里有没有把关键事实说出来。

指标：命中词数 / 期望词数；是否退成「证据里没有写」；校验警告数；耗时。
用法：./.venv/Scripts/python.exe -X utf8 -u tools/synth_eval.py [重复次数]
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

CASES = [
    ("体育课免修对保研有影响吗", ["60", "平均分", "推免"]),
    ("我现在是班长，转专业后综测分会继承吗", ["不继承", "排名", "原专业"]),
    ("重修对绩点有影响吗", ["60", "GPA"]),
    ("考试作弊会影响保研吗", ["作弊", "推免"]),
    ("辅修成绩转专业后还能用吗", ["辅修", "置换"]),
    ("体育课免修和保研冲突吗", ["免修", "推免"]),
    ("转专业后奖学金还能评吗", ["奖学金"]),
    ("宿舍电器超了会处分吗", ["处分"]),
]

reps = int(sys.argv[1]) if len(sys.argv) > 1 else 1
tot_hit = tot_want = 0
cons = 0
tt = 0.0
for r in range(reps):
    for q, keys in CASES:
        t0 = time.time()
        s = app.synthesize_answer(q)
        dt = time.time() - t0
        tt += dt
        if not s:
            print(f"FAIL {q} | 综合层没跑起来（{dt:.1f}s）")
            tot_want += len(keys)
            continue
        blob = s["conclusion"] + " " + " ".join(l["text"] for l in s["layers"])
        hit = [k for k in keys if k in blob]
        miss = [k for k in keys if k not in blob]
        tot_hit += len(hit)
        tot_want += len(keys)
        if "证据里没有写" in s["conclusion"] or "没有直接写" in s["conclusion"]:
            cons += 1
        print(f"{'OK ' if not miss else 'MISS'} {q} | {dt:.1f}s | 命中 {len(hit)}/{len(keys)}"
              + (f" 缺 {'、'.join(miss)}" if miss else "")
              + (f" | 警告 {len(s['warnings'])}" if s["warnings"] else "")
              + (" | 结论未推断" if "证据里没有写" in s["conclusion"] else ""))

n = len(CASES) * reps
print(f"\n共 {n} 次：关键词命中 {tot_hit}/{tot_want}（{100 * tot_hit / max(1, tot_want):.0f}%），"
      f"保守结论 {cons} 次，平均 {tt / max(1, n):.1f}s")
