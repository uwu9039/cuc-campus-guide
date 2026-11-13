"""条目 id 体检：sections_check 不查「id 是否存在」，这里补上。

查三件事（只报告不一致，不打印正文）：
1. 文件里出现的每个条目 id 必须在 items.json 里存在（防手误拼写）；
2. 节内 items 的并集必须 ⊆ 文档级 items；
3. 文档级 items 应与 _doclist.json 里该 key 的 ids 集合相等（少/多都报）。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/items_id_check.py           # 全目录
  ./.venv/Scripts/python.exe -X utf8 -u tools/items_id_check.py --quiet    # 只打有问题的
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEC = ROOT / "_review_items" / "sections"


def main() -> None:
    quiet = "--quiet" in sys.argv[1:]
    doclist = json.loads((ROOT / "_review_items" / "toc" / "_doclist.json").read_text(encoding="utf-8"))
    by_key = {d.get("key"): set(d.get("ids") or []) for d in doclist.get("docs") or []}
    items = {it["id"] for it in json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]}

    bad = 0
    files = [p for p in sorted(SEC.glob("*.json")) if not p.name.startswith("_")]
    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        slug = p.stem
        doc_items = list(d.get("items") or [])
        sec_items = [i for s in d.get("sections") or [] for i in (s.get("items") or [])]
        probs: list[str] = []
        unknown = sorted({i for i in doc_items + sec_items if i not in items})
        if unknown:
            probs.append(f"未知 id {len(unknown)}: {unknown[:5]}")
        not_in_doc = sorted(set(sec_items) - set(doc_items))
        if not_in_doc:
            probs.append(f"节内出现但文档级没列 {len(not_in_doc)}: {not_in_doc[:5]}")
        want = by_key.get(slug)
        if want is not None:
            miss = sorted(want - set(doc_items))
            extra = sorted(set(doc_items) - want)
            if miss:
                probs.append(f"比 _doclist 少 {len(miss)}: {miss[:5]}")
            if extra:
                # 多的不算错：`attf-*` 这类「表格/表名」条目常不在 _doclist.ids 里，但确实引用本文件。
                # 只要 id 真实存在（前面已校验）就只提示。
                print(f"[note] {slug}: 比 _doclist 多 {len(extra)} {extra[:5]}")
        if probs:
            bad += 1
            print(f"[BAD] {slug}: " + " | ".join(probs))
        elif not quiet:
            print(f"{slug:42s} ok")
    print(f"\n{len(files)} 份 | 有问题 {bad} 份")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
