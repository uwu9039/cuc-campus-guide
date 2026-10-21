"""去重：标题相同就只留一条（人工条目优先于机器条目，其次字段多者优先）。"""
import json
import re
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "items.json"
d = json.loads(p.read_text(encoding="utf-8"))


def norm(t: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", t)


groups: dict[str, list] = {}
for it in d["items"]:
    groups.setdefault(norm(it["title"]), []).append(it)

keep, drop = [], []
for g in groups.values():
    if len(g) == 1:
        keep.extend(g)
        continue
    g.sort(key=lambda x: (x["id"].startswith("doc-"), -len(x.get("evidence", {}))))
    keep.append(g[0])
    drop.extend(g[1:])

if drop:
    for it in drop:
        print("  删:", it["id"], it["title"][:40])
d["items"] = keep
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"删除重复 {len(drop)} 条，剩余 {len(d['items'])} 条")
