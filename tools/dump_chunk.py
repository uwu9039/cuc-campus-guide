"""把指定分块的条目按来源分组导出，供人工逐条复核。

用法：
    python tools/dump_chunk.py 18                # 全部 600 条
    python tools/dump_chunk.py 18 86b40f9f       # 只看某个来源
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNKS = ROOT / "_review_items" / "chunks"


def main() -> None:
    n = sys.argv[1]
    only = sys.argv[2] if len(sys.argv) > 2 else None
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in data["items"]}
    groups: dict[str, list[str]] = defaultdict(list)
    titles: dict[str, str] = {}
    urls: dict[str, str] = {}
    for line in (CHUNKS / f"auto_{n}.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        pid = line.split()[0]
        item = items[pid]
        src = (item.get("evidence", {}).get("answer", {}) or {}).get("src", "")
        if only and not src.startswith(only):
            continue
        key = src[:8]
        if key not in titles:
            srcinfo = (item.get("source") or [{}])[0]
            titles[key] = str(srcinfo.get("title") or "")
            urls[key] = str(srcinfo.get("url") or "")
        text = str(item.get("answer") or "").replace("\n", " ")
        groups[key].append(f"{pid} [{key}] | {text}")
    total = 0
    for src in sorted(groups):
        print(f"\n### {src} ({len(groups[src])}) {titles.get(src, '')}")
        if urls.get(src):
            print(f"URL {urls[src]}")
        for row in groups[src]:
            print(row)
        total += len(groups[src])
    print(f"\nTOTAL {total}", file=sys.stderr)


if __name__ == "__main__":
    main()
