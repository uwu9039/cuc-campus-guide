"""给 2026-10-30 新增的图书馆条目补预置问法，只收录真实命中自己的问法。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app as core  # noqa: E402

CANDIDATES = {
    "lib-jicungui": ["图书馆存包柜", "图书馆寄存柜", "图书馆书包放哪", "存包柜超时怎么办"],
    "lib-zizhu-dayin": ["图书馆打印", "图书馆复印", "图书馆扫描"],
    "lib-xiaoyou-rg": ["校友入馆", "校友能进图书馆吗", "毕业生进图书馆"],
    "lib-duzhe-shouze": ["图书馆能喝奶茶吗", "图书馆可以吃东西吗", "图书馆占座"],
    "lib-xuezhe-wenku": ["中传学者文库", "文库怎么预约"],
    "lib-lianxi": ["图书馆联系方式", "馆长信箱"],
    "lib-jiangzuo": ["图书馆讲座", "预约讲座", "信息素养课"],
    "lib-jiangou": ["芸悦读", "图书馆荐购", "推荐图书馆买书"],
}


def main() -> None:
    path = ROOT / "presets.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    existing = {q for g in data["groups"] for q in g["items"]}
    coverage = data.setdefault("coverage", {})
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
                coverage.setdefault(item_id, []).append(q)
                existing.add(q)
                added.append((item_id, q))
            else:
                print(f"  跳过 {q}（命中 {hit}）")

    data["total"] = sum(len(g["items"]) for g in data["groups"])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"新增问法 {len(added)} 条，total={data['total']}")
    for item_id, q in added:
        print(f"  {item_id:<20} {q}")


if __name__ == "__main__":
    main()
