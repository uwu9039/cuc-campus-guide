"""看闸门之前模型到底写了什么：把 _gate_negatives 短路掉重跑，对比闸门砍了什么。"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

CASES = ["校园卡冻结了，奖学金还能打进卡里吗？", "推免和支教保研能同时报吗？"]

orig = app._gate_negatives
app._gate_negatives = lambda text, evidence, verdict="": (text, [])  # type: ignore
try:
    for q in CASES:
        t0 = time.time()
        s = app.synthesize_answer(q)
        print("=" * 76)
        print(f"{round(time.time() - t0, 1)}s  {q}")
        if not s:
            print("  None")
            continue
        print("  结论:", s["conclusion"])
        for one in s["layers"]:
            print(f"  · {one['name']}[{one.get('verdict')}]: {one['text']}")
        print("  边界:", s["boundary"])
        print("  提醒:", s["warnings"])
finally:
    app._gate_negatives = orig  # type: ignore
