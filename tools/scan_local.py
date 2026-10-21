"""全盘扫描：找出机器上已经下载好、但没进库的官方材料（PDF/WORD/TXT/MD）。

用法：
    python tools/scan_local.py                       # 只看报告，不入库
    python tools/scan_local.py --ingest              # 把命中的官方材料收进 sources/
    python tools/scan_local.py --roots "D:\\a" "（本地路径已隐藏）"

判定规则（宁缺勿滥）：
  文件名命中校园/学籍/教务类关键词，或正文前 2000 字出现「中国传媒大学」「本科生院」「教务处」等。
  命中但看着不像官方文件的，只列出来，不入库。
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

DEFAULT_ROOTS = [
    r"（本地路径已隐藏）",
    r"（本地路径已隐藏）",
    r"（本地路径已隐藏）",
    r"D:\DSH",
]

NAME_HINTS = re.compile(
    r"学籍|教务|本科生院|培养方案|选课|成绩|考试|转专业|休学|复学|退学|毕业|学位|"
    r"学工|学生手册|奖助|助学|宿舍|校园卡|一卡通|体测|体质|军训|入学|新生|"
    r"办理|流程|规定|办法|通知|证明|中传|传媒大学", re.I)

BODY_HINTS = ("中国传媒大学", "本科生院", "教务处", "学生工作部", "信息化处", "体育部")

SKIP_DIR = {".git", "node_modules", ".venv", "__pycache__", "AppData", "Windows", "Program Files",
            "Program Files (x86)", ".cache", "Local Settings", "Application Data"}

EXTS = {".pdf", ".docx", ".doc", ".txt", ".md"}


def sniff(path: Path) -> str:
    """尽量取正文前一段用于判定（PDF 用 pypdf，docx 用 python-docx，其余直接读）。"""
    suf = path.suffix.lower()
    try:
        if suf == ".pdf":
            from pypdf import PdfReader
            r = PdfReader(str(path))
            return "\n".join((p.extract_text() or "") for p in r.pages[:3])[:3000]
        if suf == ".docx":
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs[:60])[:3000]
        if suf in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")[:3000]
    except Exception:  # noqa: BLE001
        return ""
    return ""


def walk(roots: list[str], max_files: int = 4000):
    seen = 0
    for r in roots:
        base = Path(r)
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_dir() or p.suffix.lower() not in EXTS:
                continue
            if any(part in SKIP_DIR for part in p.parts):
                continue
            seen += 1
            if seen > max_files:
                return
            yield p


def main() -> None:
    ingest = "--ingest" in sys.argv
    roots = DEFAULT_ROOTS
    if "--roots" in sys.argv:
        i = sys.argv.index("--roots")
        roots = [a for a in sys.argv[i + 1:] if not a.startswith("--")]

    idx_path = ROOT / "sources" / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    known_hashes = {v.get("sha256") for v in index.values()}
    (ROOT / "sources" / "pdf").mkdir(parents=True, exist_ok=True)

    scanned = hits = 0
    report = []
    for p in walk(roots):
        scanned += 1
        name_hit = bool(NAME_HINTS.search(p.name))
        text = sniff(p) if name_hit or p.stat().st_size < 3_000_000 else ""
        body_hit = any(k in text for k in BODY_HINTS)
        if not (name_hit or body_hit):
            continue
        hits += 1
        sha = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        official = body_hit or "中国传媒大学" in p.name
        report.append({"path": str(p), "name": p.name, "kb": round(p.stat().st_size / 1024),
                       "name_hit": name_hit, "body_hit": body_hit, "official": official,
                       "sha": sha, "dup": sha in known_hashes})

    report.sort(key=lambda r: (not r["official"], -r["kb"]))
    print(f"扫了 {scanned} 个文件，命中 {hits} 个\n")
    print(f"{'入库':<4}{'官方':<4}{'重复':<4}{'KB':>6}  文件")
    print("-" * 92)
    for r in report[:60]:
        tag = "✓" if (r["official"] and not r["dup"]) else ""
        print(f"{tag:<4}{'是' if r['official'] else '?':<4}{'是' if r['dup'] else '':<4}{r['kb']:>6}  {r['path'][:74]}")

    if not ingest:
        print("\n（只报告，未入库。加 --ingest 生效）")
        return

    added = 0
    for r in report:
        if not r["official"] or r["dup"]:
            continue
        p = Path(r["path"])
        text = sniff(p)
        if len(text) < 200:
            print(f"[跳过] {p.name}: 提取不到文字（可能是扫描件）")
            continue
        slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", p.stem)[:40]
        (ROOT / "sources" / "pdf" / f"{slug}.txt").write_text(text, encoding="utf-8")
        (ROOT / "sources" / f"{slug}.txt").write_text(text, encoding="utf-8")
        index[slug] = {"url": f"file:///{p.as_posix()}", "title": p.stem, "chars": len(text),
                       "sha256": r["sha"], "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
                       "kind": p.suffix.lstrip(".").lower(), "local_path": str(p)}
        added += 1
        print(f"[收] {slug} ← {p.name}")

    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n新入库 {added} 份，sources/ 现有 {len(index)} 条")


if __name__ == "__main__":
    main()
