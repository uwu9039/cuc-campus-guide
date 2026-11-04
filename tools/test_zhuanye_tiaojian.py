"""「转专业要满足什么条件」这一问的两处毛病：条目文字把问题句粘进答案、答复里明明有「符合」却报「满足这一问，这次没答到」。"""
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

ITEM_ID = "pt-c3e428a3c0"
SRC_TXT = ROOT / "sources" / "wendao-text" / "08e60b19.txt"
flat = lambda s: re.sub(r"\s+", "", s or "")

failed = 0


def check(name: str, ok: bool, got: str = "") -> None:
    global failed
    if not ok:
        failed += 1
    print(("PASS" if ok else "FAIL"), name, "" if ok else f"-> {got[:120]}")


items = {it["id"]: it for it in json.load(io.open(ROOT / "items.json", encoding="utf-8"))["items"]}

it = items[ITEM_ID]
title = it.get("title") or ""
answer = it.get("answer") or ""
quote = (it.get("evidence") or {}).get("answer", {}).get("quote") or ""

# 1 标题：完整的问题句 + 出处，中间不许有省略号，也不许把答案一起粘进来
check("标题不带省略号", "…" not in title, title)
check("标题不粘答案", title.split(" · ")[0].rstrip().endswith("？"), title)
# 2 正文：只有答复，不再重复问句
check("正文以答复开头", answer.startswith("申请报名的同学"), answer)
check("正文不含问句", "？" not in answer, answer)
# 3 引文：仍能在原文里逐字找到（去掉空白后连续出现）
check("引文对得上原文", flat(quote) in flat(SRC_TXT.read_text(encoding="utf-8")), quote)
check("引文不含错序问句", not flat(quote).startswith("名的是什么"), quote)

# 4 反问提示：答案里写了「符合」，就不能再说「满足这一问没答到」
d = app.answer_question("转专业要满足什么条件", {}, False)
note = d.get("note") or ""
check("不再误报没答到", "没答到" not in note, f"note={note!r} unasked={d.get('unasked')}")
# 且这题仍然落在转专业这件事上，没有把路由改坏
check("仍命中转专业", "转专业" in str(d.get("normalized") or ""), str(d.get("normalized")))

# 5 负控：只承认「满足≈符合」这一组同义，别的词照旧要报
hay = flat("申请报名的同学需要符合转专业管理办法中规定的转专业基本条件")
check("同义词算覆盖", app._covered("满足", hay, ""), "满足 应视为已答")
check("无关词仍算漏", not app._covered("宿舍", hay, ""), "宿舍 不应被视为已答")

print("failed", failed)
sys.exit(1 if failed else 0)
