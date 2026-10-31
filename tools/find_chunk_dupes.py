"""在 items.json 内查找指定分块条目的规范化完全重复项。

用于复核重复条目：只有规范化后（去空白、去标点、全半角归一）文本完全一致，
才视为内容已完整保留在别处；近似文本不计入。
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
CHUNK_DIR = ROOT / "_review_items" / "chunks"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", text)


def main() -> None:
    n = sys.argv[1]
    chunk = CHUNK_DIR / f"auto_{n}.txt"
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = {it["id"]: it for it in data["items"]}
    chunk_ids = [
        line.split()[0]
        for line in chunk.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    by_norm: dict[str, list[str]] = defaultdict(list)
    for it in data["items"]:
        by_norm[norm(it.get("answer") or "")].append(it["id"])

    dup = 0
    uniq = 0
    for pid in chunk_ids:
        it = items[pid]
        src = (it.get("evidence", {}).get("answer", {}) or {}).get("src", "")
        matches = [m for m in by_norm[norm(it.get("answer") or "")] if m != pid]
        if matches:
            dup += 1
            print(f"DUP {pid} [{src[:8]}] -> {','.join(matches)} | {str(it.get('answer'))[:60]}")
        else:
            uniq += 1
    print(f"TOTAL {len(chunk_ids)}  DUP {dup}  UNIQUE {uniq}")


if __name__ == "__main__":
    main()
