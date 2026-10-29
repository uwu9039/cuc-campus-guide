"""限定语审计：条目文本不能把原文的「原则上 / 一般 / 暂定 / 建议」改写成硬性规定。

用法：python tools/audit_qualifiers.py [--json out.json]
退出码不代表失败，只输出清单，供人工核对后修条目。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

HEDGE = re.compile(r"原则上|暂定|建议|通常|一般情况下|一般应|一般不得|一般不|一般可|一般由|一般在|如有必要|视情况")
STRONG = re.compile(r"禁止|严禁|不得|必须|一律|不允许|取消资格|不予")
# 这些「不得」是原文自带的硬规定，不算改写；只用来判断条目是否凭空加硬
FIELD_LABEL = {
    "fee": "fee", "location": "location", "hours": "hours", "duration": "duration",
    "window": "window", "answer": "answer",
}


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def ev_list(ev: Any) -> list[dict]:
    if not isinstance(ev, dict):
        return []
    if "sources" in ev:
        return [x for x in ev["sources"] if isinstance(x, dict)]
    return [ev]


def field_text(item: dict, key: str) -> str:
    if key in FIELD_LABEL:
        return str(item.get(FIELD_LABEL[key]) or "")
    head, _, idx = key.partition(".")
    if not idx.isdigit():
        return ""
    n = int(idx)
    seq = item.get({"steps": "steps", "materials": "materials", "pitfalls": "pitfalls"}.get(head, ""), [])
    if n >= len(seq):
        return ""
    one = seq[n]
    if isinstance(one, dict):
        return str(one.get("what") or one.get("name") or "")
    return str(one)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
    hardened: list[dict] = []   # 原文有保留，条目写成硬性
    dropped: list[dict] = []    # 原文有保留，条目没保留
    added: list[dict] = []      # 条目加了原文没有的硬性词

    for item in items:
        for key, ev in (item.get("evidence") or {}).items():
            text = squash(field_text(item, key))
            if not text:
                continue
            quotes = [squash(x.get("quote", "")) for x in ev_list(ev)]
            if not quotes:
                continue
            q_hedge = any(HEDGE.search(q) for q in quotes)
            q_strong = any(STRONG.search(q) for q in quotes)
            t_hedge = bool(HEDGE.search(text))
            t_strong = bool(STRONG.search(text))
            row = {
                "id": item["id"], "title": item.get("title", ""), "field": key,
                "text": text[:160], "quote": quotes[0][:160],
            }
            if q_hedge and t_strong and not t_hedge:
                hardened.append(row)
            elif q_hedge and not t_hedge:
                dropped.append(row)
            elif t_strong and not q_strong:
                added.append(row)

    print(f"条目 {len(items)}")
    print(f"A 原文有保留语、条目写成硬性：{len(hardened)}")
    for r in hardened[:25]:
        print(f"  ✗ {r['id']:<22} {r['field']:<10} {r['text'][:60]}")
        print(f"      原文：{r['quote'][:90]}")
    print(f"B 原文有保留语、条目丢掉了：{len(dropped)}")
    for r in dropped[:10]:
        print(f"  ? {r['id']:<22} {r['field']:<10} {r['text'][:60]}")
        print(f"      原文：{r['quote'][:90]}")
    print(f"C 条目有硬性词、原文没有：{len(added)}")
    for r in added[:10]:
        print(f"  ? {r['id']:<22} {r['field']:<10} {r['text'][:60]}")
        print(f"      原文：{r['quote'][:90]}")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"hardened": hardened, "dropped": dropped, "added": added},
                       ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        print(f"清单写入 {args.json}")


if __name__ == "__main__":
    main()
