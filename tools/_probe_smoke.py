"""Smoke: import app, one _synth_plan call, show the raw short sentences."""
import json
import sys
import time

sys.path.insert(0, ".")
t0 = time.time()
import app  # noqa: E402

print("import %.1fs items=%d" % (time.time() - t0, len(app.ITEMS)))
print("SECTIONS_REWRITE", app.SECTIONS_REWRITE,
      "ADDITIVE", app.SECTIONS_ADDITIVE,
      "PER_PREMISE", app.SECTIONS_PER_PREMISE)

q = "挂科了还能保研吗？补考通过算吗？"
st = {}
t1 = time.time()
prem, qs = app._synth_plan(q, st)
print("plan %.1fs status=%r" % (time.time() - t1, st))
print(json.dumps({"premises": prem, "queries": qs}, ensure_ascii=False, indent=1))

cands = app._synth_candidates(qs or prem, prem, question=q)
print("pool", len(cands))
raw = " ".join(c["quote"] for c in cands)
for w in ["平均分", "绩点", "GPA", "60", "综合成绩", "排名"]:
    print("  ", w, w in raw)
for c in cands[:6]:
    print(" -", c["doc"], "|", c["quote"][:60])
