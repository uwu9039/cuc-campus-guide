# -*- coding: utf-8 -*-
"""核对「方案救不回来」的几条：库里到底有没有那句话。"""
import sys

sys.path.insert(0, ".")
import app  # noqa: E402


def norm(s):
    return "".join(str(s or "").split()).lower()


def dump(item_id, tokens):
    it = app.ITEM_BY_ID.get(item_id)
    print("=" * 70)
    print(item_id, "->", (it or {}).get("title"))
    if not it:
        return
    quotes = []
    for _k, v in (it.get("evidence") or {}).items():
        for one in app._ev_items(v):
            quotes.append(str((one or {}).get("quote") or ""))
    for q in quotes:
        print("   ", q[:150])
    for t in tokens:
        print("   has %-8s : %s" % (t, any(norm(t) in norm(q) for q in quotes)))


dump("tuimian-tiaojian", ["五项", "5项", "未列", "一、", "（一）"])
dump("xyk-buka", ["当场", "自助补卡机", "20元"])
dump("xueji-kaoshi", ["60分", "平均分", "绩点"])

# 全库：推免 + 五项/5项 同句
g = []
for it in app.ITEMS:
    for _k, v in (it.get("evidence") or {}).items():
        for one in app._ev_items(v):
            q = str((one or {}).get("quote") or "")
            nq = norm(q)
            if "推免" in nq and ("五项" in nq or "5项" in nq or "五条" in nq):
                g.append((it["id"], q[:120]))
print("\n[全库] 推免+五项/5项/五条 :", len(g))
for x in g[:5]:
    print("   ", x)

# 全库：当场 + 补卡
g2 = []
for it in app.ITEMS:
    for _k, v in (it.get("evidence") or {}).items():
        for one in app._ev_items(v):
            q = str((one or {}).get("quote") or "")
            nq = norm(q)
            if "当场" in nq and ("补卡" in nq or "补办" in nq):
                g2.append((it["id"], q[:120]))
print("\n[全库] 当场+补卡/补办 :", len(g2))
for x in g2[:5]:
    print("   ", x)
