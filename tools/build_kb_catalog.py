"""把 aia-raw-*.md 里收集到的 fileId 汇总成文件目录。

输出 kb-catalog.md / kb-catalog.json：按首次出现的提问分组，记录文件名、fileId、
以及它被哪些问题引用过。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
LINK = re.compile(r"\[([^\]]+)\]\((https://aihub\.cuc\.edu\.cn/doc/view/fileview\?fileId=([a-f0-9]{32})[^)]*)\)")
BLOCK = re.compile(r"^=====\s*(.+)$", re.M)


def main() -> None:
    docs: dict[str, dict] = {}
    for f in sorted(ROOT.glob("aia-raw-*.md")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        marks = [(m.start(), m.group(1).strip()) for m in BLOCK.finditer(text)]
        for i, (pos, q) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            for m in LINK.finditer(text[pos:end]):
                title, url, fid = m.group(1).strip(), m.group(2), m.group(3)
                name = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", title).strip()
                rec = docs.setdefault(fid, {"id": fid, "title": name, "queries": set(), "url": url})
                rec["queries"].add(q)

    rows = sorted(docs.values(), key=lambda r: r["title"])
    (ROOT / "kb-catalog.json").write_text(
        json.dumps([{**r, "queries": sorted(r["queries"])} for r in rows],
                   ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 问道中传 · 引用文件目录（自动收集）", "",
             f"- 收集时间：2026-10-27", f"- 去重文件：**{len(rows)}** 份",
             "- 来源：直接调用 `/console/chat/sse`，解析回答末尾的参考链接",
             "- ⚠️ 只证明「它的检索会引用这份文件」，不代表文件内容为真；下载后仍需逐份核对", "",
             "| # | 文件名 | fileId | 被问到 |", "|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        q = "、".join(r["queries"])[:40]
        lines.append(f"| {i} | {r['title'][:56]} | `{r['id']}` | {q} |")
    (ROOT / "kb-catalog.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"汇总 {len(rows)} 份文件 → kb-catalog.md / kb-catalog.json")
    for r in rows[:8]:
        print("  ", r["title"][:50])


if __name__ == "__main__":
    main()
