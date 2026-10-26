"""发布前给手机号打码：把 11 位手机号替换成前三位+****+后四位，保留学校座机。

会同时检查引文是否含手机号——含的话先报错，避免打码破坏证据链。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOBILE = re.compile(r"(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)")
TEXT_EXT = {".txt", ".json", ".md", ".html", ".py"}
SKIP_DIRS = {".venv", "__pycache__", "dist", ".git", "piptest", "node_modules"}


def mask(t: str) -> str:
    return MOBILE.sub(lambda m: f"{m.group(1)}****{m.group(2)}", t)


def main() -> None:
    dry = "--dry-run" in sys.argv

    # 引文若含手机号，先停：打码会让 quote 匹配不上
    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    offenders = []
    for it in items["items"]:
        for k, ev in (it.get("evidence") or {}).items():
            rows = ev.get("sources") if isinstance(ev, dict) and "sources" in ev else [ev]
            for r in rows or []:
                if isinstance(r, dict) and MOBILE.search(r.get("quote", "") or ""):
                    offenders.append(f"{it['id']}.{k}")
    if offenders:
        # 引文和原文一起打码，两边同步改，证据链仍然成立
        print(f"注意：{len(offenders)} 处引文含手机号，将与原文一起打码：{offenders[:3]}")

    changed = 0
    for p in ROOT.rglob("*"):
        if p.is_dir() or set(p.parts) & SKIP_DIRS:
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
        new = mask(text)
        if new != text:
            if not dry:
                p.write_text(new, encoding="utf-8")
            changed += 1
    print(f"{'将' if dry else '已'}打码 {changed} 个文件")


if __name__ == "__main__":
    main()
