"""查证：资格条款为什么进不了候选池 —— 直接用 app 的检索函数点名看排名。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app  # noqa: E402

TARGETS = ["tuimian-tiaojian"]
QUERIES = [
    "推免 基本条件 外语",
    "推免 基本条件 挂科",
    "推免 基本条件 违纪 处分",
    "推免 资格条件",
    "推免 基本条件",
]

for q in QUERIES:
    print("=" * 70)
    print("query:", q)
    ranked = app.rank(q)
    pos = {it["id"]: i + 1 for i, (it, _s) in enumerate(ranked)}
    for t in TARGETS:
        print(f"  rank()     {t}: pos={pos.get(t)} score={[s for i, s in ranked if i['id'] == t]}")
    for name, fn in (("bm25", app.bm25_hits), ("meta", app.meta_hits)):
        try:
            rows = fn(q, k=60) if name == "bm25" else fn(q, k=40)
        except TypeError:
            rows = fn(q)
        ids = [it["id"] for it, _ in rows]
        print(f"  {name:<10} {t}: pos={ids.index(t) + 1 if t in ids else None} / {len(ids)}")
    # 单看目标条目的词面
