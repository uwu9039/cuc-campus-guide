import json
import re

P = "items.json"
d = json.load(open(P, encoding="utf-8"))
pat = re.compile(r"(?:MM)?PAGE\s*\\?\*+[A-Z]*", re.I)
n = 0
for it in d["items"]:
    for k, v in list(it.items()):
        if isinstance(v, str) and pat.search(v):
            it[k] = pat.sub("", v)
            n += 1
            print(it["id"], k, repr(it[k][:60]))
open(P, "w", encoding="utf-8").write(
    json.dumps(d, ensure_ascii=False, indent=1))
print("fixed", n)
