"""给图书馆门户新增的 4 个条目补预置问法，只收录真实命中自己的问法。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app as core  # noqa: E402

CANDIDATES = {
    "lib-benguan-buju": [
        "图书馆各层有什么",
        "图书馆楼层布局",
        "图书馆空间布局",
        "图书馆二层有什么",
    ],
    "lib-quyuguobie": [
        "区域国别学学科馆在哪",
        "区域国别学学科馆是什么",
    ],
    "lib-daping-yuelan": [
        "大屏阅览区在哪",
        "大屏阅览区怎么预约",
        "大屏阅览区使用规则",
    ],
    "lib-guimo": [
        "图书馆有多少座位",
        "图书馆藏书量",
        "图书馆有多少研讨间",
    ],
    "lib-tese-yuelan": [
        "图书馆有哪些特色空间",
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
        got = 0
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
                got += 1
        if got == 0:
            print(f"✗ {item_id} 没有可用问法")

    data["total"] = sum(len(g["items"]) for g in data["groups"])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"新增问法 {len(added)} 条，total={data['total']}")
    for item_id, q in added:
        print(f"  {item_id:<20} {q}")


if __name__ == "__main__":
    main()
