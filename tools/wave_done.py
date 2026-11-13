"""收尾一波：更新 _progress.json 并打印一行进度（给夜间编排 agent 用）。"""
from __future__ import annotations

import json
import pathlib

p = pathlib.Path("_review_items/sections/_progress.json")
d = json.loads(p.read_text(encoding="utf-8"))
sec = p.parent
base = int(d.get("baseline") or 51)
now = len([q for q in sec.glob("*.json") if not q.name.startswith("_")])
d["waves"] = int(d.get("waves") or 0) + 1
d["done_new"] = now - base
d["last"] = "wave %d" % d["waves"]
p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
print("waves %d | 新增 %d | 全目录 %d" % (d["waves"], d["done_new"], now))
