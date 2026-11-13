"""行为门覆盖率审计：把每个「词表门」当成被测对象，用同义改写集量它漏多少。

只测门函数本身，不发模型调用。加新门或改词表后跑一遍，看覆盖率有没有掉。
用法：./.venv/Scripts/python.exe -X utf8 -u tools/gate_audit.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

REL = ["转专业后综测分还算数吗", "辅修成绩转专业后还能用吗", "班长加分转专业后承认吗",
       "体育免修和保研冲突吗", "重修和保研能同时吗", "奖学金转专业后带走吗",
       "综测分转专业后重新评吗", "免修成绩计入保研吗"]
CONTACT = ["打哪个电话", "找哪位老师", "问哪个科室", "联系方式在哪", "咨询谁", "该找谁办"]
ELLIPSIS = ["还有呢", "具体点呢", "要多久", "能带啥", "那要准备什么", "周末开门吗", "哪个更快"]
PLACE = ["在几楼", "从南门怎么走", "位置在哪"]  # 「怎么找」太泛（怎么找工作），故意不收
STRATEGY = ["值得去吗", "好不好进", "难不难", "划算吗"]
NOT_REL = ["图书馆开放时间", "校园卡丢了怎么办", "补考怎么报名", "宿舍怎么报修"]

rows = [
    ("关系门（综合层触发）", REL, app._looks_relational),
    ("联系门（联系人追问）", CONTACT, lambda q: bool(app.CONTACT_ASK.search(q))),
    ("追问门（纯省略）", ELLIPSIS, app._pure_ellipsis),
    ("地点门", PLACE, lambda q: bool(app.PLACE_ASK.search(q))),
    ("策略门", STRATEGY, lambda q: bool(app.STRATEGY.search(q))),
]
bad = 0
for name, cases, fn in rows:
    hit = sum(1 for q in cases if fn(q))
    miss = [q for q in cases if not fn(q)]
    print(f"{name}: {hit}/{len(cases)}" + (f" | 漏：{'、'.join(miss)}" if miss else ""))
    bad += len(miss)

fp = [q for q in NOT_REL if app._looks_relational(q)]
print(f"关系门误报（普通题被当关系题）: {len(fp)}/{len(NOT_REL)}" + (f" | {'、'.join(fp)}" if fp else ""))
bad += len(fp)
print(f"\n合计不符期望 {bad} 处")
raise SystemExit(1 if bad else 0)
