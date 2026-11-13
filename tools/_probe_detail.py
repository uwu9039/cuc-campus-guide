# -*- coding: utf-8 -*-
"""看池内细节：点在不在、引文是不是金标准 src 的、是哪条短句捞的。"""
import json
import sys

sys.path.insert(0, ".")
import app  # noqa: E402

probe = json.load(open("_review_items/_plan_connector_probe.json", encoding="utf-8"))
rows = {r["q"]: r for r in probe["rows"]}

import re


def norm(s):
    return "".join(str(s or "").split()).lower()


def show(q, tokens):
    r = rows[q]
    print("=" * 80)
    print(q)
    print("base queries:", r["base_queries"])
    print("det rules:", [(d["genre"], d["query"]) for d in r["det_rules"]])
    for p in r["points"]:
        print("  P%d base=%s conn=%s src=%s kw=%s"
              % (p["i"], p["base"], p["conn"], p["base_src"], p["kw"]))
    cands = app._synth_candidates(r["base_queries"], r["premises"], question=q)
    print("  base pool", len(cands), "items", len({c.get("item_id") for c in cands}))
    for t in tokens:
        got = [c for c in cands if norm(t) in norm(c["quote"])]
        print("  [%s] base pool -> %d" % (t, len(got)))
        for c in got[:4]:
            print("     ", str(c.get("item_id")), c["doc"][:28], "|",
                  str(c["quote"])[:110])
    for d in r["det_rules"]:
        cands2 = app._synth_candidates([d["query"]], r["premises"], question=q)
        for t in tokens:
            got = [c for c in cands2 if norm(t) in norm(c["quote"])]
            if got:
                print("  rule[%s] -> [%s] %d" % (d["name"], t, len(got)))
                for c in got[:2]:
                    print("     ", str(c.get("item_id")), c["doc"][:28], "|",
                          str(c["quote"])[:110])


show("挂科了还能保研吗？补考通过算吗？", ["平均分", "60分", "五项", "5项", "综合成绩"])
show("国家奖学金一年发多少钱", ["8000", "10000", "硕士", "为准"])
show("国家奖学金和国家励志奖学金能同时拿吗", ["8000", "不能同时"])
show("校园卡丢了怎么补办？多久能拿到", ["当场", "工本费"])
