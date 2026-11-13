"""Find clauses that carry the connector rule, and test candidate rule queries."""
import sys
import re
sys.path.insert(0, ".")
import app  # noqa: E402

def norm(s):
    return "".join(str(s).split()).lower()

PROBES = [
    "补考 重修 成绩 按 60 分 计入 平均分 学分绩点",
    "平均分 学分绩点 计算",
    "补考 成绩 记载 计入 平均分",
    "综合成绩 构成 计算 学业表现",
    "推免 综合成绩 排名 计算",
    "处分 期限 起算 届满 解除",
    "期间 不享受 待遇 中止",
    "适用于 本科生 范围",
]

for t in PROBES:
    print("=== QUERY", t)
    seen = set()
    for it, sc in app.rank(t)[:6]:
        print("  rank %.1f %s :: %s" % (sc, it["id"], str(it.get("title"))[:40]))
    for it, sc in app.bm25_hits(t, k=6):
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        print("  bm25 %s :: %s" % (it["id"], str(it.get("title"))[:40]))
    # does the actual 60-point clause exist in retrieved rows?
    hits = app.bm25_hits(t, k=40) + [x for x in app.rank(t)[:8]]
    found = []
    for it, _s in hits:
        for _k, v in (it.get("evidence") or {}).items():
            for one in app._ev_items(v):
                q = str((one or {}).get("quote") or "")
                nq = norm(q)
                if ("60" in nq and ("平均分" in nq or "绩点" in nq)):
                    found.append((it["id"], q[:100]))
    print("  [60分/平均分] ->", found[:3])
