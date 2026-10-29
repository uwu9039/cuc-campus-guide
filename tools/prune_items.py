"""清理引用已隔离语料的条目：能补证据的保留，补不了的删除。

用法：python tools/prune_items.py [--apply]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
SRC = ROOT / "sources"

INDEXES = ["index.json", "crawl-index.json", "cdp-index.json", "wechat-index.json",
           "chsi-index.json", "moe-index.json", "national-index.json",
           "extra-index.json", "huibian-index.json", "local-index.json"]


def existing_slugs() -> dict[str, str]:
    """slug -> 文本全文（压缩空白）。"""
    texts: dict[str, str] = {}
    for fname in INDEXES:
        f = SRC / fname
        if not f.exists():
            continue
        sub = {
            "crawl-index.json": "crawl", "cdp-index.json": "cdp",
            "wechat-index.json": "wechat", "chsi-index.json": "chsi",
            "moe-index.json": "moe", "national-index.json": "national",
            "extra-index.json": "extra", "huibian-index.json": "huibian",
            "local-index.json": "local",
        }.get(fname, "")
        try:
            idx = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for slug in idx:
            p = SRC / sub / f"{slug}.txt" if sub else SRC / f"{slug}.txt"
            if p.exists():
                texts[slug] = re.sub(r"\s+", "", p.read_text(encoding="utf-8"))
    return texts


def main() -> None:
    apply = "--apply" in sys.argv
    texts = existing_slugs()
    p = ROOT / "items.json"
    data = json.loads(p.read_text(encoding="utf-8"))

    kept, dropped, fixed = [], [], 0
    for it in data["items"]:
        ev = it.get("evidence") or {}
        good, bad = {}, 0
        for k, v in ev.items():
            rows = v.get("sources") if isinstance(v, dict) and "sources" in v else [v]
            ok = all((r.get("src") in texts and re.sub(r"\s+", "", r.get("quote", "")) in texts[r["src"]])
                     for r in rows or [])
            if ok:
                good[k] = v
            else:
                bad += 1
        if not good:
            dropped.append(it["id"])
            continue
        if bad:
            fixed += 1
            it["evidence"] = good
            for field in ("steps", "pitfalls", "materials"):
                if field in it:
                    n = sum(1 for k in good if k.startswith(field + "."))
                    if field == "steps":
                        it[field] = it[field][:max(n, 1)]
        kept.append(it)

    print(f"保留 {len(kept)} 条，删除 {len(dropped)} 条（证据全失效），修剪 {fixed} 条")
    for d in dropped[:10]:
        print("  -", d)
    if apply:
        data["items"] = kept
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("已写入 items.json")


if __name__ == "__main__":
    main()
