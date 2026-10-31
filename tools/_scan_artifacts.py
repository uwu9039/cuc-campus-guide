import json
import re

pats = {
    "merge": re.compile(r"(?:MM)?PAGE\s*\\?\*?\s*MERGE[A-Z]*\s*\d*", re.I),
    "pagenum": re.compile(r"(?m)^\s*[—–]\s*\d{1,3}\s*[—–]\s*$|\s[—–]\s*\d{1,3}\s*[—–]\s"),
}

d = json.load(open("items.json", encoding="utf-8"))


def vals(it):
    for k, v in it.items():
        if isinstance(v, str):
            yield k, v
    for i, s in enumerate(it.get("steps") or []):
        if isinstance(s, dict):
            for k in ("what", "where", "when"):
                if isinstance(s.get(k), str):
                    yield f"steps.{i}.{k}", s[k]
        elif isinstance(s, str):
            yield f"steps.{i}", s
    for i, m in enumerate(it.get("materials") or []):
        if isinstance(m, dict) and isinstance(m.get("name"), str):
            yield f"materials.{i}", m["name"]
    for key in ("pitfalls", "advisory"):
        for i, p in enumerate(it.get(key) or []):
            if isinstance(p, str):
                yield f"{key}.{i}", p


for name, pat in pats.items():
    hits = []
    for it in d["items"]:
        for k, v in vals(it):
            m = pat.search(v)
            if m:
                hits.append((it["id"], k, m.group(0)))
    print(name, len(hits))
    for h in hits[:40]:
        print(" ", h)
