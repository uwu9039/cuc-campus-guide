import json
import sys

sys.path.insert(0, ".")
import app

qs = ["就业协议怎么签", "保研条件", "快递地址怎么写", "体测什么时候", "军训要准备什么",
      "报警电话", "自习室要预约吗", "宿舍桌子规格", "游泳馆怎么收费"]
for q in qs:
    r = app.clean_response(app.answer_question(q, {}, router_llm=False))
    it = r.get("item") or {}
    print("=" * 60)
    print(q, "->", r.get("matched"), it.get("id"), it.get("title"))
    for p in r.get("answers") or []:
        if p.get("text"):
            print("  文字:", p["text"][:200])
        for s in p.get("steps") or []:
            if isinstance(s, dict):
                print("  步:", s.get("when") or "", "|", (s.get("what") or "")[:160])
            else:
                print("  步:", str(s)[:160])
        for ln in p.get("lines") or []:
            print("  行:", str(ln)[:200])
    if r.get("note"):
        print("  note:", r["note"][:200])
    if r.get("clarify"):
        print("  clarify:", r["clarify"][:120])
    for f in r.get("followups") or []:
        print("  追问:", f)
