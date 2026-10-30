"""审计 e 收尾：两个新问法仍走反问，补精确别名；presets 补宿舍网络问法并修坏字符。"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALIAS_ADD = {
    "sushe-sheshi": ["宿舍有哪些设施", "宿舍都有什么设施", "宿舍里有什么设施", "宿舍都有啥"],
    "sushe-kongtiao": ["宿舍空调电费怎么算", "空调电费怎么算", "空调电费", "宿舍空调费"],
}
CHIPS = {
    "it-sushe-wangluo": ["宿舍有wifi吗", "宿舍有校园网吗", "宿舍能连校园网吗",
                         "宿舍怎么上网", "宿舍能装路由器吗", "宿舍能装宽带吗"],
}
BAD = {"在读证明\x01": "在读证明怎么开", "捡到卡\x01": "捡到卡怎么办"}

data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
by_id = {i["id"]: i for i in data["items"]}
for iid, extra in ALIAS_ADD.items():
    item = by_id[iid]
    for a in extra:
        if a not in item["aliases"]:
            item["aliases"].append(a)
(ROOT / "items.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import app as core  # noqa: E402
from gen_presets import group_of, stem  # noqa: E402

presets = json.loads((ROOT / "presets.json").read_text(encoding="utf-8"))
groups = {g["name"]: g for g in presets["groups"]}
existing = {p for g in presets["groups"] for p in g["items"]}
cov = presets["coverage"]

for bad, good in BAD.items():
    for g in groups.values():
        g["items"] = [good if p == bad else p for p in g["items"]]
    if bad in existing:
        existing.discard(bad)
        existing.add(good)

added, misses = 0, []
for iid, chips in CHIPS.items():
    item = by_id[iid]
    stems = {stem(q) for q in cov.get(iid, [])}
    for q in chips:
        if q in existing or stem(q) in stems:
            continue
        r = core.answer_question(q, {})
        got = (r.get("item") or {}).get("id")
        if got != iid or r.get("hold"):
            misses.append((iid, q, got or "未命中", bool(r.get("hold"))))
            continue
        cov.setdefault(iid, []).append(q)
        existing.add(q)
        stems.add(stem(q))
        groups.setdefault(group_of(item["title"]), {"name": group_of(item["title"]), "items": []})["items"].append(q)
        added += 1

presets["generated"] = date.today().isoformat()
presets["total"] = sum(len(g["items"]) for g in groups.values())
presets["groups"] = list(groups.values())
(ROOT / "presets.json").write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"新增问法 {added} 条，总计 {presets['total']} 条，坏字符 {len(BAD)} 处；未采用 {len(misses)} 条")
for x in misses:
    print("  ✗", x)

# 补完别名后重新验证两句不再反问
for q in ("宿舍空调电费怎么算", "宿舍有哪些设施"):
    r = core.answer_question(q, {})
    print(q, "->", (r.get("item") or {}).get("id"), "hold=", r.get("hold"))
