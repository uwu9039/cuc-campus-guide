"""按目录切《学生工作规章制度汇编》：目录里每行「标题 …… 页码」，据此切 PDF。

用法：python tools/split_huibian.py --pdf sources/pdf/huibian-2025.pdf
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path("D:/DSH/智能体节")
TZ = timezone(timedelta(hours=8))

TOC = re.compile(r"^(中国传媒大学.{2,44}?(?:办法|规定|细则|准则|制度|方案|规程|规范|标准))[.…\s]{2,}(\d{1,3})\s*$")
NUM = re.compile(r"中传[^\s〔，。]{0,4}字〔?20\d\d〕?\s*\d+\s*号")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default="sources/pdf/huibian-2025.pdf")
    ap.add_argument("--year", default="2025")
    ap.add_argument("--toc-pages", type=int, default=8)
    args = ap.parse_args()

    reader = PdfReader(args.pdf)
    pages = [(p.extract_text() or "") for p in reader.pages]
    total = len(pages)
    print(f"页数 {total}")

    # 1) 解析目录
    entries: list[tuple[str, int]] = []
    for i in range(min(args.toc_pages, total)):
        for line in pages[i].splitlines():
            s = line.strip().replace(" ", "")
            m = TOC.match(s)
            if m:
                title = re.sub(r"[.…]+$", "", m.group(1)).strip()
                entries.append((title, int(m.group(2))))
    # 去重保序
    seen, toc = set(), []
    for t, p in entries:
        if t in seen:
            continue
        seen.add(t)
        toc.append((t, p))
    print(f"目录条目 {len(toc)} 条")

    # 2) 校正偏移：用标题在正文里定位真实起始页（TOC 页码与实际 PDF 页有偏差）
    body_norm = [re.sub(r"\s+", "", (pages[i] or ""))[:2000] for i in range(total)]
    fixed_toc = []
    cursor = 0
    for title, toc_page in toc:
        key = re.sub(r"\s+", "", title)[:14]
        found = None
        for i in range(max(cursor, args.toc_pages), total):
            if key and key in body_norm[i]:
                found = i + 1
                break
        if found is None:
            found = toc_page
        fixed_toc.append((title, found))
        cursor = max(cursor, found - 1)
    toc = fixed_toc
    print(f"校正后首份起始页：p{toc[0][1] if toc else '?'}")

    # 3) 按页码切
    OUT = ROOT / "sources" / "huibian"
    OUT.mkdir(parents=True, exist_ok=True)
    idx_p = ROOT / "sources" / "huibian-index.json"
    index = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}

    added = 0
    for k, (title, start) in enumerate(toc):
        end = toc[k + 1][1] - 1 if k + 1 < len(toc) else total
        start = max(1, min(start, total))
        end = max(start, min(end, total))
        body = "\n".join(pages[start - 1:end])
        if len(body) < 700:
            continue
        num = NUM.search(body)
        num_s = num.group(0) if num else ""
        slug = "hb" + hashlib.md5(title.encode()).hexdigest()[:10]
        if slug in index:
            continue
        (OUT / f"{slug}.txt").write_text(body, encoding="utf-8")
        printed = re.search(r"[-—]\s*(\d{1,3})\s*[-—]", pages[start - 1] or "")
        index[slug] = {
            "url": "https://xsc.cuc.edu.cn/2023/0904/c2753a259796/page.htm",
            "page_label": int(printed.group(1)) if printed else start,
            "title": f"{title}（{num_s}）" if num_s else title,
            "chars": len(body),
            "page_start": start, "page_end": end,
            "compilation": f"学生工作规章制度汇编{args.year}",
            "sha256": hashlib.sha256(body.encode()).hexdigest()[:16],
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "kind": "huibian",
        }
        added += 1
        print(f"  [切] p{start:>3}-{end:<3} {len(body):>6} 字  {title[:36]}")

    idx_p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n新增 {added} 份，索引 {len(index)} 条")


if __name__ == "__main__":
    main()
