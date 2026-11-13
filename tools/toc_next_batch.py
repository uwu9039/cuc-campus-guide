"""下一批待标注清单：给「夜间批量标注」编排 agent 用。

只读、不写。每次调用打印下一批候选（默认 6 份 / 合计 ≤25,000 字符），
已完成的（_review_items/sections/<slug>.json 存在）和已排除的自动跳过。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/toc_next_batch.py
  ./.venv/Scripts/python.exe -X utf8 -u tools/toc_next_batch.py --n 4 --chars 15000
  ./.venv/Scripts/python.exe -X utf8 -u tools/toc_next_batch.py --json    # 机器可读
  ./.venv/Scripts/python.exe -X utf8 -u tools/toc_next_batch.py --status  # 只看进度

排除表：_review_items/sections/_exclude.json
  {"exclude": [{"key": "...", "why": "..."}]}
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCLIST = ROOT / "_review_items" / "toc" / "_doclist.json"
SECDIR = ROOT / "_review_items" / "sections"
EXCLUDE = SECDIR / "_exclude.json"


def load_texts() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in (ROOT / "sources").rglob("*.txt"):
        out.setdefault(p.stem, p)
    return out


def main() -> None:
    args = sys.argv[1:]
    as_json = "--json" in args
    status_only = "--status" in args
    n = 6
    budget = 25000
    for i, a in enumerate(args):
        if a == "--n" and i + 1 < len(args):
            n = int(args[i + 1])
        if a == "--chars" and i + 1 < len(args):
            budget = int(args[i + 1])

    docs = json.loads(DOCLIST.read_text(encoding="utf-8"))["docs"]
    done = {p.stem for p in SECDIR.glob("*.json") if not p.name.startswith("_")}
    # 已用 toc 分片登记过的 key（如 huibian-2025 / 大汇编）不再按单文档重复标注
    registered = set()
    for p in (ROOT / "_review_items" / "toc").glob("*.json"):
        if p.name.startswith("_"):
            continue
        try:
            registered.add(str((json.loads(p.read_text(encoding="utf-8")).get("doc") or {}).get("key") or ""))
        except Exception:  # noqa: BLE001
            continue
    excl: dict[str, str] = {}
    if EXCLUDE.exists():
        for x in json.loads(EXCLUDE.read_text(encoding="utf-8")).get("exclude") or []:
            excl[str(x.get("key"))] = str(x.get("why") or "")
    texts = load_texts()

    rows = []
    for d in docs:
        key = d.get("key") or ""
        if d.get("worth") != "优先" or key in done or key in excl or key in registered:
            continue
        p = texts.get(key)
        if not p:
            continue
        try:
            chars = len(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:  # noqa: BLE001
            continue
        rows.append({"key": key, "chars": chars, "path": str(p.relative_to(ROOT))})

    rows.sort(key=lambda r: r["chars"])
    total_left = len(rows)
    total_chars = sum(r["chars"] for r in rows)

    if status_only:
        print(f"待做 {total_left} 份 | 合计 {total_chars:,} 字符 | 已完成 {len(done)} 份 | 排除 {len(excl)} 份")
        return

    batch: list[dict] = []
    used = 0
    for r in rows:
        if len(batch) >= n:
            break
        if batch and used + r["chars"] > budget:
            break
        batch.append(r)
        used += r["chars"]

    if as_json:
        print(json.dumps({"left": total_left, "left_chars": total_chars,
                          "batch": batch, "batch_chars": used}, ensure_ascii=False, indent=1))
        return

    print(f"待做 {total_left} 份 / {total_chars:,} 字符 | 本批 {len(batch)} 份 / {used:,} 字符")
    for r in batch:
        print(f"  {r['key']}  {r['chars']:>6,} 字符  {r['path']}")


if __name__ == "__main__":
    main()
