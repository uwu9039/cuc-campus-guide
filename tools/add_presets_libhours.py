"""给「图书馆开放时间」条目补预置问法，只收录真实命中自己的问法。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app as core  # noqa: E402

CANDIDATES = {
    "lib-kaifang-shijian": [
        "图书馆开放时间",
        "图书馆几点开门",
        "图书馆开馆时间",
        "图书馆闭馆时间",
        "图书馆几点关门",
        "图书馆自习到几点",
    ],
}


def main() -> None:
    path = ROOT / "presets.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    existing = {q for g in data["groups"] for q in g["items"]}
    group = next((g for g in data["groups"] if g["name"] == "图书馆 / 空间"), None)
    if group is None:
        group = {"name": "图书馆 / 空间", "items": []}
        data["groups"].append(group)

    added = []
    for item_id, queries in CANDIDATES.items():
        for q in queries:
            if q in existing:
                continue
            d = core.answer_question(q)
            hit = (d.get("item") or {}).get("id")
            if d.get("matched") and hit == item_id and not d.get("disambiguate"):
                group["items"].append(q)
                data["coverage"].setdefault(item_id, []).append(q)
                existing.add(q)
                added.append((item_id, q))

    data["total"] = sum(len(g["items"]) for g in data["groups"])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"新增问法 {len(added)} 条，total={data['total']}")
    for item_id, q in added:
        print(f"  {item_id:<20} {q}")


if __name__ == "__main__":
    main()
