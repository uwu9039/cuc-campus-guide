# -*- coding: utf-8 -*-
"""从探针结果里对比 base / conn56 / res48 的逐点变化（不重建池）。"""
import json

d = json.load(open("_review_items/_plan_connector_probe.json", encoding="utf-8"))
rows = d["rows"]

print("%-34s %-8s %-9s %-9s %-9s" % ("题", "点数", "base", "conn56", "res48"))
tot = {"base": [0, 0], "conn56": [0, 0], "res48": [0, 0], "llm_res": [0, 0]}
for r in rows:
    n = r["n_points"]
    cells = []
    for k in ("base", "conn56", "res48"):
        v = r["variants"].get(k)
        if not v:
            cells.append("—")
            continue
        cells.append("%d/%d" % (v["strict"], n))
        tot[k][0] += v["strict"]
        tot[k][1] += n
    if "llm_res" in r["variants"]:
        tot["llm_res"][0] += r["variants"]["llm_res"]["strict"]
        tot["llm_res"][1] += n
    print("%-34s %-8d %-9s %-9s %-9s" % (r["q"][:32], n, *cells))

print()
for k, (a, b) in tot.items():
    if b:
        print("%-8s strict %d/%d = %.1f%%" % (k, a, b, 100.0 * a / b))

print("\n逐点变化（base -> conn56）")
new = lost = 0
for r in rows:
    bs = r["variants"]["base"]["strict_list"]
    cs = r["variants"]["conn56"]["strict_list"]
    ls = r["variants"]["base"]["loose_list"]
    cl = r["variants"]["conn56"]["loose_list"]
    for i in range(r["n_points"]):
        if cs[i] and not bs[i]:
            new += 1
            print("  + %-20s P%d %s" % (r["q"][:18], i + 1, r["points"][i]["kw"]))
        if bs[i] and not cs[i]:
            lost += 1
            print("  - %-20s P%d %s" % (r["q"][:18], i + 1, r["points"][i]["kw"]))
        if cl[i] and not ls[i]:
            print("  ~ %-20s P%d loose+ %s" % (r["q"][:18], i + 1, r["points"][i]["kw"]))
print("  新增 strict %d 条，丢失 strict %d 条" % (new, lost))

print("\n仍然是 loose-only 的点（kw 在池里但不在同一引文）")
for r in rows:
    b, c = r["variants"]["base"], r["variants"]["conn56"]
    for i in range(r["n_points"]):
        if c["loose_list"][i] and not c["strict_list"][i]:
            print("  ? %-20s P%d %s" % (r["q"][:18], i + 1, r["points"][i]["kw"]))
