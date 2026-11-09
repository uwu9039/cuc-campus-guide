"""高危要点回归：历史上一再答错、修好过的那几条，发布前必须重跑。

判据不是「id 对上了」，而是两件事同时成立：
  1. 挑中的条目 id 在允许集合里；
  2. 答出来的标题或正文确实讲到这件事（关键字在标题或正文里，人也能读懂）。

抖动的题给多次机会（`考试不及格` 有两条官方原文互相冲突，实测 16/17 命中预期那条）：
reps/min_pass 写在用例里，不靠一次运气。

`known_gap=True` 的是已知未修项：照实打印、不计失败，免得把没修好的说成修好了。
上下文污染不在这里——那条要两轮对话，用 tools/ctx_probe.py（8 段，约 4 分钟）。

用法：./.venv/Scripts/python.exe -X utf8 -u tools/check_canonical.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

ADOBE = {"pt-f64e32ffb5", "pt-92ee6239ee", "pt-7d77f75e17", "pt-66ba4e0dbb",
         "pt-20fd89cd01", "pt-15a080e181", "pt-c688f71bd2", "pt-059632ba15"}

# (问题, 允许的 id 集合 or None=应拒答, 关键字, 说明, 次数, 至少几次算过, 已知未修)
CASES = [
    ("医保和公费医疗是一回事吗？学生医保怎么用？", {"xyy-gongfei"}, "公费医疗", "医保指向公费医疗", 1, 1, False),
    ("学校医保怎么报", {"xyy-gongfei"}, "公费医疗", "同上，口语说法", 1, 1, False),
    ("ps激活怎么弄", ADOBE, "adobe", "ps 激活指向 Adobe 正版", 1, 1, False),
    ("PS 怎么激活", ADOBE, "adobe", "同上，大写写法", 1, 1, False),
    ("Adobe软件怎么激活", ADOBE, "adobe", "同上，全名", 1, 1, False),
    ("学校有校车吗？班车时刻表在哪里？", None, "", "库里没有校车，必须拒答", 1, 1, False),
    ("学校有滑雪课吗", None, "", "库里没有，必须拒答", 1, 1, False),
    ("宿舍能用哪些电器？吹风机、电煮锅能用吗？", {"sushe-dianqi"}, "禁止", "经验帖不许压过官方规定", 1, 1, False),
    ("考试不及格怎么办？补考还是重修？", {"jwc-bukao-chongkao", "qa-18fe5c7d-33"}, "重考",
     "本科生没有补考，走重考", 3, 2, False),
    ("研究生能换导师吗", None, "", "库里没有「换导师」，应拒答", 1, 1, True),
]


def body_of(resp: dict) -> str:
    for p in resp.get("answers") or []:
        if p.get("text"):
            return str(p["text"])
    return ""


def main() -> int:
    failed = known = 0
    for q, allowed, must, note, reps, need, known_gap in CASES:
        wins = 0
        tried = []
        for _ in range(reps):
            d = app.answer_question(q, router_llm=True)
            item = d.get("item") or {}
            got = item.get("id")
            body = body_of(d)
            if allowed is None:
                ok = not d.get("matched")
            else:
                hay = f"{item.get('title') or ''}{body}".lower()
                ok = got in allowed and bool(must) and must.lower() in hay
            tried.append((got, ok, d, body))
            wins += int(bool(ok))
        passed = wins >= need
        mark = ("PASS" if passed else ("KNOWN" if known_gap else "FAIL"))
        if not passed and not known_gap:
            failed += 1
        if not passed and known_gap:
            known += 1
        got, ok, d, body = tried[0]
        item = d.get("item") or {}
        print(f"{mark} {note}｜{q}" + (f"（{wins}/{reps}）" if reps > 1 else ""))
        print(f"     got={got} matched={d.get('matched')} conf={d.get('confidence')} "
              f"gate={((d.get('model_route') or {}).get('gate'))}｜{'这条对' if ok else '这条不对'}")
        print(f"     条目：{item.get('title')}")
        if body:
            print(f"     正文：{body[:110]}")
        gen = (d.get("llm_answer") or {}).get("text", "")
        if gen:
            print(f"     生成：{gen[:90]}")
    print(f"\n共 {len(CASES)} 条用例：失败 {failed}，已知未修 {known}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
