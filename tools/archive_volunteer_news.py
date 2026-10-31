"""把志愿者联合会管理文件库里的年度总结流水账标为存档，不参与问答路由。

数据不删，只打 archive_only 标记：条目、引文、来源都还在 items.json 里，
但排名、联想、预置问法不再把它们当成可答事项。逐条列出 id 与标题供复核。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
BACKUP = ROOT / "items_before_archive_volunteer.json"
LOG = ROOT / "_review_items" / "applied_archive_volunteer.txt"
SRC_PREFIX = "1de56d3c"


def main() -> None:
    dry = "--dry-run" in sys.argv
    data = json.loads(ITEMS.read_text(encoding="utf-8"))
    items = data["items"]
    picked = []
    for it in items:
        ev = it.get("evidence") or {}
        srcs = {v.get("src", "") for v in ev.values() if isinstance(v, dict)}
        if any(s.startswith(SRC_PREFIX) for s in srcs):
            picked.append(it)

    if len(picked) != 259:
        raise SystemExit(f"预期 259 条，实际 {len(picked)} 条，先查证据来源")

    changed = [it for it in picked if not it.get("archive_only")]
    lines = [f"志愿者联合会管理文件库流水账 {len(picked)} 条 → archive_only（不删数据）", ""]
    for it in picked:
        title = (it.get("title") or "").split(" · ")[0]
        lines.append(f"ARCHIVE {it['id']}  {title[:100]}")
    print("\n".join(lines))
    print(f"\n待改 {len(changed)} 条，已是存档 {len(picked) - len(changed)} 条")
    if dry:
        return

    BACKUP.write_text(ITEMS.read_text(encoding="utf-8"), encoding="utf-8")
    for it in changed:
        it["archive_only"] = True
    tmp = ITEMS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ITEMS)
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    total = sum(1 for it in items if it.get("archive_only"))
    print(f"已写入，items={len(items)}，archive_only 共 {total} 条")


if __name__ == "__main__":
    main()
