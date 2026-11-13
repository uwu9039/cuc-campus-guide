"""复合题人工审阅集：脚本只负责把题跑出来、原样打印，对错由人读。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/synth_compound_probe.py [题号]
每轮改完检索/合成，跑一遍，逐题读结论与分层，记下：事实错、结论越界、概念混用、漏答。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

CASES = [
    "转专业后，我之前修的课还算数吗？奖学金还能申请吗？",
    "我是家庭经济困难生，体育课免修会影响助学金和保研吗？",
    "休学一年再回来，宿舍还能保留吗？学费怎么算？",
    "考试作弊被记过，还能转专业吗？还能保研吗？",
    "大四体育课还没修完，能正常毕业吗？体测没达标会怎样？",
    "校园卡丢了，体测报名截止了怎么办？",
]

only = int(sys.argv[1]) if len(sys.argv) > 1 else 0
for i, q in enumerate(CASES, 1):
    if only and i != only:
        continue
    s = app.synthesize_answer(q)
    print("=" * 18)
    print(f"[{i}] {q}")
    if not s:
        print("  [综合层没跑起来]")
        continue
    print("结论:", s["conclusion"])
    for l in s["layers"]:
        print(f"  [{l['name']}] {l['text']}")
    print("边界:", s["boundary"])
    print("证据:", [(e["doc"][:16], e.get("kind")) for e in s["evidence"]])
