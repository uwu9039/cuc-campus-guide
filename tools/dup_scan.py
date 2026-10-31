"""全库答案去重体检：按空白归一后分组，列出完全相同的条目。"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
OUT = ROOT / "_review_items" / "dup_groups.txt"


def norm(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", "", t)


def main() -> None:
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    groups: dict[str, list[dict]] = defaultdict(list)
    for it in data["items"]:
        text = it.get("answer") or ""
        if not text or it.get("auto"):
            continue
        groups[norm(text)].append(it)
    for it in data["items"]:
        if not it.get("auto"):
            continue
        text = it.get("answer") or ""
        if text:
            groups[norm(text)].append(it)

    dups = {k: v for k, v in groups.items() if len(v) > 1 and k}
    lines = [f"重复组 {len(dups)} 个，涉及 {sum(len(v) for v in dups.values())} 条"]
    for key, its in dups.items():
        lines.append("")
        lines.append(f"### x{len(its)}  {its[0].get('answer', '')[:80]}")
        for it in its:
            src = (it.get("evidence", {}).get("answer", {}) or {}).get("src", "")
            kind = "auto" if it.get("auto") else "curated"
            lines.append(f"  {it['id']}  {kind}  {src}  |  {it.get('answer', '')[:120]}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(lines[0])
    print(f"写出 {OUT.name}")


if __name__ == "__main__":
    main()
