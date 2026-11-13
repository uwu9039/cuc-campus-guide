"""节首/节尾对齐：把「页码行、书眉行」从节区间里剔除。

审计第 2 轮发现：PDF 转换产物会把「页眉（书眉）」与页码并进节区间——
首行起于页眉、尾行吞掉页码，后果是引文左/右边缘混进书眉与页码。

本脚本只动 `sections[].lines`，不动 heading/items/notes。每一步剔除都复验
「本节所有条目的引文仍在本区间内」，验证不过就退回，不冒险。

判定「可剔除的噪声行」：
  1. 纯页码：`- 244 -` / `244` / 单字符数字（≤3 位）；
  2. 书眉：同一行文本在全文出现 ≥3 次、且长度 ≤40 字的短行（running header）。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/fix_section_start.py --dry
  ./.venv/Scripts/python.exe -X utf8 -u tools/fix_section_start.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEC = ROOT / "_review_items" / "sections"

DASHED = re.compile(r"^[-\u2013\u2014]\s*\d{1,4}\s*[-\u2013\u2014]$")
BARE = re.compile(r"^\d{1,3}$")


def is_page_mark(s: str) -> bool:
    t = s.strip()
    return bool(DASHED.fullmatch(t) or BARE.fullmatch(t))


def quotes(iid: str, item: dict) -> list[str]:
    it = item.get(iid) or {}
    ev = (it.get("evidence") or {}).get("answer") or {}
    out: list[str] = []
    if isinstance(ev, dict):
        if ev.get("quote"):
            out.append(str(ev["quote"]))
        srcs = ev.get("sources") or []
        if isinstance(srcs, dict):
            srcs = [srcs]
        for s in srcs:
            if isinstance(s, dict) and s.get("quote"):
                out.append(str(s["quote"]))
    return [re.sub(r"\s+", "", q)[:26] for q in out]


def main() -> None:
    dry = "--dry" in sys.argv[1:]
    cutoff = 1762944000  # 只动本次夜班新产出的文件
    # 默认只修审计点名的那几份；--all 才全量跑
    named = {"c5181fe8", "00f4cdcc", "5b13d3aa", "61f74587", "01fee161", "9b673804", "hbf8ecd720c7"}
    all_mode = "--all" in sys.argv[1:]
    items = {it["id"]: it for it in json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]}
    texts = {p.stem: p for p in (ROOT / "sources").rglob("*.txt")}

    head_fix = tail_fix = touched_files = 0
    for path in sorted(SEC.glob("*.json")):
        if path.name.startswith("_") or path.stat().st_mtime < cutoff:
            continue
        slug = path.stem
        if not all_mode and slug not in named:
            continue
        tp = texts.get(slug)
        if not tp:
            continue
        lines = tp.read_text(encoding="utf-8", errors="ignore").split("\n")
        # 书眉：全文出现 ≥3 次的短行
        freq = Counter(re.sub(r"\s+", "", ln) for ln in lines if ln.strip() and len(ln.strip()) <= 40)
        header = {t for t, c in freq.items() if c >= 3 and len(t) >= 4}

        def noise(i: int) -> bool:
            t = lines[i].strip()
            if not t:
                return False
            return is_page_mark(t) or re.sub(r"\s+", "", t) in header

        d = json.loads(path.read_text(encoding="utf-8"))
        changed = 0
        for s in d.get("sections") or []:
            a, b = (s.get("lines") or [0, 0])[:2]
            if not (1 <= a < b <= len(lines)):
                continue
            iids = s.get("items") or []
            orig = (a, b)

            def fits(na: int, nb: int) -> bool:
                blob = re.sub(r"\s+", "", "\n".join(lines[na - 1:nb]))
                for iid in iids:
                    qs = quotes(iid, items)
                    if qs and not any(q in blob for q in qs):
                        return False
                # 别把本节自己的 author 标题剔出区间（2026-11-12 踩过：书眉判定误伤「第一章 总则」）
                if s.get("heading_kind") == "author":
                    h = re.sub(r"\s+", "", str(s.get("heading") or ""))
                    if h and h not in blob:
                        return False
                return True

            while a < b and noise(a - 1) and fits(a + 1, b):
                a += 1
                head_fix += 1
            # 尾部只剔「纯页码」：重复短行在尾部可能是正文内容，不碰
            while b > a and is_page_mark(lines[b - 1].strip()) and fits(a, b - 1):
                b -= 1
                tail_fix += 1
            if (a, b) != orig:
                s["lines"] = [a, b]
                changed += 1
        if changed:
            touched_files += 1
            if not dry:
                path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'[dry] ' if dry else ''}首行剔除 {head_fix} 行 / 尾行剔除 {tail_fix} 行 / 涉及 {touched_files} 份文件")


if __name__ == "__main__":
    main()
