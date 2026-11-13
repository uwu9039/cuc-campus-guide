"""Locate golden points' source clauses in the KB (item id + quote)."""
import json
import sys

sys.path.insert(0, ".")
import app  # noqa: E402

golden = json.load(open("_review_items/golden_20261111.json", encoding="utf-8"))

def norm(s):
    return "".join(str(s).split()).lower()

for ci, case in enumerate(golden["cases"], 1):
    print("=== [%d] %s" % (ci, case["q"]))
    for pi, p in enumerate(case["points"], 1):
        kws = p.get("kw") or []
        hits = []
        for it in app.ITEMS:
            for _k, v in (it.get("evidence") or {}).items():
                for one in app._ev_items(v):
                    q = str((one or {}).get("quote") or "")
                    if not q:
                        continue
                    nq = norm(q)
                    ok = True
                    for k in kws:
                        alts = [norm(x) for x in str(k).split("|")]
                        if not any(a and a in nq for a in alts):
                            ok = False
                            break
                    if ok:
                        hits.append((it["id"], it.get("title", ""), q))
        print("  P%d kw=%s -> %d clause(s)" % (pi, kws, len(hits)))
        for hid, title, q in hits[:3]:
            print("      [%s] %s :: %s" % (hid, title[:40], q[:90]))
