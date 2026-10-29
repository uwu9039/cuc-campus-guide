"""路由回归：地点/办事问句不得被转专业计划劫持，真正的转专业问句仍要出计划。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

CASES = [
    ("饭卡丢了怎么办艺术与传播大楼 1 层 校园生活服务大厅在哪", "no-plan", "校园卡"),
    ("艺术与传播大楼", "no-plan", "艺术与传播大楼"),
    ("艺术与传播大楼怎么走", "no-plan", "艺术与传播大楼"),
    ("新闻学院在哪", "no-plan", "新闻学院"),
    ("校园生活服务大厅在哪", "no-plan", "校园卡"),
    ("校园卡服务中心", "no-plan", "校园卡"),
    ("饭卡丢了怎么办", "no-plan", "校园卡"),
    ("新闻学院研究生招生", "no-plan", ""),
    ("转专业到新闻学院要什么条件", "plan", "新闻学院"),
    ("传播学转专业什么条件", "plan", "传播"),
    ("新闻学院接收计划", "plan", "新闻学院"),
]

failed = 0
for text, want, needle in CASES:
    d = app.answer_question(text, {}, False)
    is_plan = bool(d.get("plan"))
    got = "plan" if is_plan else "no-plan"
    blob = str(d.get("normalized") or "")
    if is_plan:
        blob += str((d.get("plan") or {}).get("college") or "")
    ok = got == want and needle in blob
    if not ok:
        failed += 1
    # no-plan 的问句无论如何不能在答案标题里出现转专业计划
    if not is_plan and "转专业" in str(d.get("normalized") or ""):
        ok = False
        failed += 1
    print(("PASS" if ok else "FAIL"), text, "->", got, "|", blob[:60])

print("failed", failed, "of", len(CASES))
sys.exit(1 if failed else 0)
