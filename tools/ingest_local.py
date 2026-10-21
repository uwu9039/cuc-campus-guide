"""把本地文件夹里的官方文件（PDF / DOCX）批量收进 sources/。

用法：
    python tools/ingest_local.py "D:\\path\\to\\资料"
    python tools/ingest_local.py "D:\\path" --tag 学籍

产物：
    sources/pdf/<slug>.txt        提取出的正文
    sources/<slug>.txt            同一份副本（check_quotes 从这里读）
    sources/index.json            登记：本地路径 / 文件哈希 / 页数 / 字数 / 抓取时间

注意：扫描件（图片型 PDF）提取不到文字，会提示需要 OCR，不会硬塞空文本。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TZ = timezone(timedelta(hours=8))


def slugify(path: Path) -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", path.stem).strip("-")
    return base[:40] or "doc"


def read_pdf(path: Path) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return text, len(reader.pages)


def read_docx(path: Path) -> tuple[str, int]:
    from docx import Document

    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append("\t".join(c.text for c in row.cells))
    return "\n".join(parts), len(doc.paragraphs)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print("不是文件夹:", folder)
        return

    pdf_dir = ROOT / "sources" / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    idx_path = ROOT / "sources" / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}

    files = sorted([*folder.glob("*.pdf"), *folder.glob("*.docx")])
    if not files:
        print("这个文件夹里没有 pdf / docx")
        return

    for f in files:
        slug = slugify(f)
        try:
            if f.suffix.lower() == ".pdf":
                text, pages = read_pdf(f)
            else:
                text, pages = read_docx(f)
        except Exception as e:  # noqa: BLE001
            print(f"[失败] {f.name}: {e}")
            continue

        if len(text.strip()) < 200:
            print(f"[跳过] {f.name}: 只提取到 {len(text)} 字，可能是扫描件，需要 OCR")
            continue

        (pdf_dir / f"{slug}.txt").write_text(text, encoding="utf-8")
        (ROOT / "sources" / f"{slug}.txt").write_text(text, encoding="utf-8")
        index[slug] = {
            "url": f"file:///{f.as_posix()}",
            "title": f.stem,
            "chars": len(text),
            "pages": pages,
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest()[:16],
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "kind": f.suffix.lower().lstrip("."),
            "local_path": str(f),
        }
        print(f"[收] {pages:>3} 页 {len(text):>6} 字  {slug}  ← {f.name}")

    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsources/ 现有 {len(index)} 条来源")


if __name__ == "__main__":
    main()
