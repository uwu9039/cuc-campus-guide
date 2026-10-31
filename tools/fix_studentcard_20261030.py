import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"
data = json.loads(P.read_text(encoding="utf-8"))
by = {i["id"]: i for i in data["items"]}

it = by["qa-18fe5c7d-43"]
add_alias = [
    "学生证丢了",
    "学生证丢了怎么办",
    "学生证掉了",
    "学生证找不到",
    "学生证找不到了",
    "学生证遗失",
    "学生证遗失怎么办",
    "学生证补办",
    "补办学生证",
    "学生证怎么补办",
]
add_kw = ["补办", "遗失", "丢失"]
for a in add_alias:
    if a not in it["aliases"]:
        it["aliases"].append(a)
for k in add_kw:
    if k not in it["keywords"]:
        it["keywords"].append(k)

P.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("aliases", len(it["aliases"]), "keywords", it["keywords"])
