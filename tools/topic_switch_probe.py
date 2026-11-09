"""话题切换集：上一件事问完，下一句换成**新话题**，看还会不会被旧上下文带走。

判据两条（任一成立即算过）：
  1. 没有接上一条（context_item 为空），且：新话题有对应条目时答上它 / 没条目时拒答；
  2. 接上了，但答的是新话题的条目（说明上下文没带偏）。
真追问另有一组，必须接住。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/topic_switch_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

# (第一问, 第二句新话题, 新话题应命中的条目集合（空=库里没有，应拒答）, 说明)
SWITCH = [
    ("宿舍购电怎么办理", "饿了", set(), "饿了：库里没有，应拒答"),
    ("宿舍购电怎么办理", "下雨了", set(), "下雨：拒答"),
    ("宿舍购电怎么办理", "困了", set(), "困了：拒答"),
    ("转专业怎么办理", "我想吃火锅", set(), "吃火锅：拒答"),
    ("图书馆开放时间", "学校有校车吗", set(), "校车：拒答"),
    ("宿舍购电怎么办理", "学校医保怎么报", {"xyy-gongfei"}, "医保：答公费医疗"),
    ("图书馆开放时间", "学校食堂在哪里", {"shitang-canting"}, "食堂：答食堂"),
    ("校园卡丢了怎么补办", "ps激活怎么弄", None, "ps：答 Adobe（八条之一）"),
    ("转专业怎么办理", "那宿舍怎么调", {"sushe-huansu"}, "点宿舍：答换宿舍"),
    ("图书馆开放时间", "那成绩单在哪开", {"jwc-chengjidan"}, "点成绩单：答成绩单"),
]
ADOBE = {"pt-f64e32ffb5", "pt-92ee6239ee", "pt-7d77f75e17", "pt-66ba4e0dbb",
         "pt-20fd89cd01", "pt-15a080e181", "pt-c688f71bd2", "pt-059632ba15"}

# (第一问, 第二句真追问, 答案里该有的词)
FOLLOW = [
    ("转专业怎么办理", "那要带什么材料", "转专业"),
    ("转专业怎么办理", "几天能办好", "转专业"),
    ("图书馆开放时间", "周末呢", "图书馆"),
    ("校园卡丢了怎么补办", "要交多少钱", "校园卡"),
]


def ask(q, ctx=None, hist=None):
    return app.answer_question(q, context_item=ctx, history=hist, router_llm=True)


def main() -> int:
    bad = 0
    print("== 新话题（不许被旧上下文带走）")
    for q1, q2, want, why in SWITCH:
        r1 = ask(q1)
        ctx = (r1.get("item") or {}).get("id") or ""
        hist = [{"role": "user", "content": q1},
                {"role": "assistant", "content": str((r1.get("answers") or [{}])[0].get("text") or "")[:200]}]
        r2 = ask(q2, ctx or None, hist)
        got = (r2.get("item") or {}).get("id")
        attached = bool(r2.get("context_item"))
        hit = got in (want or set()) if want is not None else got in ADOBE
        if want == set():
            ok = (not attached and not r2.get("matched")) or (attached and not r2.get("matched"))
        else:
            ok = hit and (not attached or hit)
        if not ok:
            bad += 1
        print(f"{'OK ' if ok else 'BAD'} {why:22} 接上={attached} matched={r2.get('matched')} "
              f"item={got} conf={r2.get('confidence')}")

    print("\n== 真追问（必须接住）")
    for q1, q2, word in FOLLOW:
        r1 = ask(q1)
        ctx = (r1.get("item") or {}).get("id") or ""
        hist = [{"role": "user", "content": q1},
                {"role": "assistant", "content": str((r1.get("answers") or [{}])[0].get("text") or "")[:200]}]
        r2 = ask(q2, ctx or None, hist)
        body = str((r2.get("item") or {}).get("title") or "") + " " + " ".join(
            str(p.get("text") or "") for p in (r2.get("answers") or []))
        ok = bool(r2.get("context_item")) and r2.get("matched") and word in body
        if not ok:
            bad += 1
        print(f"{'OK ' if ok else 'BAD'} {q1}→{q2} 接上={bool(r2.get('context_item'))} "
              f"matched={r2.get('matched')} item={(r2.get('item') or {}).get('id')}")

    print(f"\n共 {len(SWITCH) + len(FOLLOW)} 段，不符期望 {bad} 段")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
