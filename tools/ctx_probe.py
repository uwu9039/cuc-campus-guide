"""多轮四类集：每段对话先问第一句（不带上下文），再拿答上的那一条当 context_item 问第二句。

这就是界面真实走的路：web-next/field.js 每轮都把上一条事项的 id 和最近 12 条消息发上来。
四类各自的期望：
  A 词表内续问（「那要带什么材料」）——接住上一条。
  B 词表外续问（「几天能办好」）——接住上一条；这一类以前靠「答得薄就重试」兜，现在靠判定。
  C 独立新问题（「滑雪」）——不接，答不上就拒答；用户实测的错接就在这类。
  D 句里点了别的事（「那宿舍怎么调」）——不接上一条，答自己那件事。

用法：./.venv/Scripts/python.exe tools/ctx_probe.py
产物：_review_items/ctx_rows.jsonl
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

OUT = ROOT / "_review_items" / "ctx_rows.jsonl"

# (类别, 第一问, 第二问, 期望第二问接不接上一条, 期望答案里该有的词（可空）)
CASES = [
    ("A词表内续问", "转专业怎么办理", "那要带什么材料", True, "转专业"),
    ("B词表外续问", "转专业怎么办理", "几天能办好", True, "转专业"),
    ("A词表内续问", "校园卡丢了怎么补办", "要交多少钱", True, "校园卡"),
    ("C图书馆续问", "图书馆开放时间", "周末呢", True, "图书馆"),
    ("C独立新问题", "学生综合服务大厅在哪", "滑雪", False, ""),
    ("C独立新问题", "宿舍怎么报修", "学校有滑雪课吗", False, ""),
    ("D点了别的事", "转专业怎么办理", "那宿舍怎么调", False, "宿舍"),
    ("D点了别的事", "图书馆开放时间", "那成绩单在哪开", False, "成绩单"),
]


def brief(resp: dict) -> dict:
    mr = resp.get("model_route") or {}
    item = (resp.get("item") or {}).get("title") or ""
    return {
        "matched": bool(resp.get("matched")),
        "conf": round(float(resp.get("confidence") or 0), 2),
        "item": item,
        "ctx": resp.get("context_item") or "",
        "need": mr.get("ctx_need", "词表"),
        "need_why": mr.get("ctx_need_why", ""),
        "search": resp.get("condensed_query") or "",
        "cond": mr.get("condense_error", ""),
        "err": mr.get("error", ""),
    }


def ans_text(resp: dict) -> str:
    for p in (resp.get("answers") or []):
        if p.get("text"):
            return str(p["text"])[:200]
    return str(resp.get("suggestion") or "")[:200]


def main() -> int:
    if not app.api_key():
        print("没有模型 key，判定会全走词表——先配好 .env 再跑")
        return 2
    only = sys.argv[1:]
    rows = []
    for cat, q1, q2, want_ctx, want_word in CASES:
        if only and not any(o in cat or o in q1 or o in q2 for o in only):
            continue
        t0 = time.time()
        r1 = app.answer_question(q1)
        ctx = (r1.get("item") or {}).get("id") or ""
        hist = [{"role": "user", "content": q1},
                {"role": "assistant", "content": ans_text(r1)}]
        r2 = app.answer_question(q2, context_item=ctx or None, history=hist)
        b1, b2 = brief(r1), brief(r2)
        got_ctx = bool(b2["ctx"])
        ok_ctx = got_ctx == want_ctx
        ok_word = (not want_word) or (want_word in (b2["item"] + ans_text(r2)))
        row = {"cat": cat, "q1": q1, "b1": b1, "q2": q2, "b2": b2,
               "want_ctx": want_ctx, "got_ctx": got_ctx, "ok_ctx": ok_ctx,
               "ok_word": ok_word, "ms": round((time.time() - t0) * 1000)}
        rows.append(row)
        flag = "OK " if (ok_ctx and ok_word) else "BAD"
        print(f"{flag} [{cat}] 「{q1}」→「{q2}」 判={b2['need']}({b2['need_why'][:14]}) "
              f"接上一条={'是' if got_ctx else '否'}(要{'接' if want_ctx else '不接'}) "
              f"答={b2['conf']} {b2['item'][:24]} {'|' + b2['search'][:30] if b2['search'] else ''}")
    bad = [r for r in rows if not (r["ok_ctx"] and r["ok_word"])]
    n_need = sum(1 for r in rows if r["b2"]["need"] != "词表")
    print(f"—— {len(rows)} 段，判定生效 {n_need} 段，不符期望 {len(bad)} 段 | "
          f"墙钟 {sum(r['ms'] for r in rows)/1000:.0f}s")
    with io.open(OUT if not only else OUT.with_name("ctx_rows_partial.jsonl"),
                 "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("产物", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
