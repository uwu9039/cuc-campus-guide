import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "items.json"

data = json.loads(P.read_text(encoding="utf-8"))
by = {i["id"]: i for i in data["items"]}
it = by["it-sushe-wangluo"]
add = ["宿舍网络报修", "宿舍网报修", "宿舍网络维修", "宿舍网维修", "宿舍网络怎么报修", "宿舍网怎么报修"]
for a in add:
    if a not in it["aliases"]:
        it["aliases"].append(a)

P.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("aliases now", len(it["aliases"]))
