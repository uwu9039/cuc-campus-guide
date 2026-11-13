"""复现：关闭综合层时，含「转专业」的问句有多少被强行反问「转去哪个学院」。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/_probe_transfer_clarify.py
只读，不写任何东西。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

QS = [
    "转专业",
    "我想转专业",
    "转专业怎么办",
    "转专业多久能批下来",
    "转专业后宿舍还能住吗？",
    "转专业以后宿舍要换吗",
    "转专业会影响保研吗",
    "转专业后已经修的课还算数吗",
    "转专业了图书馆借的书要还吗",
    "转专业以后班长加分还算吗",
    "大二转专业来得及吗",
    "转专业能跨学院吗",
    "转专业失败还能再申请吗",
    "转专业之后辅导员是谁",
    "转专业要不要面试",
    "转专业名额有多少",
    "转专业接收计划在哪看",
    "转专业什么时候报名",
    "转专业需要什么条件",
]


def main() -> None:
    clarify_n = 0
    for q in QS:
        d = app.answer_question(q, router_llm=False)
        c = (d.get("clarify") or "").strip()
        hit = "学院" in c and "转去" in c
        clarify_n += hit
        title = (d.get("item") or {}).get("title") or ""
        ans = ""
        for a in d.get("answers") or []:
            ans = (a.get("text") or "")[:40]
            break
        print(f"{'反问学院' if hit else '正常回答'} | {q[:22]:24} | 条目={title[:20]:22} | "
              f"{(c or ans)[:44]}")
    print(f"\n{clarify_n}/{len(QS)} 题被反问「转去哪个学院」")


if __name__ == "__main__":
    main()
