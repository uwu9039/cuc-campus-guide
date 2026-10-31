"""把 14 条人工条目的 source 字符串编号恢复为来源数组。

这些条目的 evidence 已经登记了来源编号，但 source 仍是裸编号，
前端按数组渲染时会在 (item.source || []).map 处报错。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS = ROOT / "items.json"
BACKUP = ROOT / "_review_items" / "items_before_source_fix_20261031.json"
LOG = ROOT / "_review_items" / "patch_source_20261031.txt"

INDEX_FILES = [
    "sources/corpus-index.json",
    "sources/wendao-index.json",
    "sources/local-index.json",
    "sources/huibian-index.json",
    "sources/index.json",
]
CHECKED = "2026-10-31"

# hb921 是整段学生工作规章制度汇编，索引标题只取了区间首页的规章名。
# 这两条的引文分别来自汇编内的两份办法，按原文标题登记。
HB921_TITLES = {
    "linshi-kunnan-buzhu": "中国传媒大学困难补助管理办法（修订）· 学生工作规章制度汇编 2025",
    "xuefei-jianmian": "中国传媒大学本专科生减免学费管理办法（修订）· 学生工作规章制度汇编 2025",
}


def load_index() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for rel in INDEX_FILES:
        path = ROOT / rel
        if not path.exists():
            continue
        obj = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            continue
        for key, meta in obj.items():
            if not isinstance(meta, dict):
                continue
            cur = found.setdefault(key, {})
            for field in ("title", "url", "file"):
                if meta.get(field) and not cur.get(field):
                    cur[field] = meta[field]
    return found


def main() -> None:
    raw = ITEMS.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not BACKUP.exists():
        BACKUP.write_text(raw, encoding="utf-8")

    index = load_index()
    changed = []
    missing = []
    for item in data["items"]:
        source = item.get("source")
        if not isinstance(source, str):
            continue
        ids = [source]
        for ev in (item.get("evidence") or {}).values():
            if isinstance(ev, dict) and ev.get("src") and ev["src"] not in ids:
                ids.append(ev["src"])

        sources = []
        for sid in ids:
            meta = index.get(sid)
            if not meta:
                missing.append((item["id"], sid))
                continue
            title = HB921_TITLES.get(item["id"], meta.get("title", "")) if sid == "hb921f79f1f2" else meta.get("title", "")
            entry = {"title": title}
            if meta.get("url"):
                entry["url"] = meta["url"]
            if meta.get("file"):
                entry["file"] = meta["file"]
            entry["checked"] = CHECKED
            sources.append(entry)

        if missing:
            continue
        changed.append((item["id"], item["title"], source, sources))
        item["source"] = sources

    if missing:
        print("缺少来源元数据，未写回：")
        for iid, sid in missing:
            print(" ", iid, sid)
        raise SystemExit(1)

    ITEMS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    lines = [f"来源结构修复 {len(changed)} 条", ""]
    for iid, title, before, after in changed:
        lines.append(f"{iid} | {title}")
        lines.append(f"  改前: {before}")
        for s in after:
            lines.append(f"  改后: {json.dumps(s, ensure_ascii=False)}")
        lines.append("")
    LOG.write_text("\n".join(lines), encoding="utf-8")
    print(f"已修复 {len(changed)} 条，日志 {LOG}")


if __name__ == "__main__":
    main()
