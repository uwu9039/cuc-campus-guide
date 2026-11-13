"""综合层样例：三道关系题，看「拆前提 → 取证 → 推断」跑不跑得通。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/synth_probe.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

CASES = [
    "体育课免修对保研有影响吗",
    "重修对绩点有影响吗",
    "考试作弊会影响保研吗",
    "我现在是班长，转专业后综测分会继承吗",
]

bad = 0
for q in CASES:
    t0 = time.time()
    s = app.synthesize_answer(q)
    dt = time.time() - t0
    if not s:
        bad += 1
        print(f"BAD {q} | 综合层没跑起来（{dt:.1f}s）")
        continue
    cited = sum(1 for x in [s["conclusion"]] + [l["text"] for l in s["layers"]]
                if "[" in x)
    ok = bool(s["layers"]) and cited >= 2 and not s["warnings"]
    if not ok:
        bad += 1
    print(f"{'OK ' if ok else 'BAD'} {q} | {dt:.1f}s | 前提 {len(s['premises'])} 条，"
          f"证据 {len(s['evidence'])} 条，警告 {len(s['warnings'])}")
    print(f"    结论：{s['conclusion'][:80]}")
    for l in s["layers"]:
        print(f"    [{l['name']}] {l['text'][:70]}")
print(f"\n共 {len(CASES)} 题，不符合期望 {bad} 题")
raise SystemExit(1 if bad else 0)
