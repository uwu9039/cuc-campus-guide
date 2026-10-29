"""核验下载到的文件：抽正文、看标题是否能对上、识别扫描件/空文本。

输出：
- sources/wendao-text/<id前8位>.txt  正文（PDF 用 pdftotext，DOCX 用 python-docx）
- sources/wendao-verify.json         每份文件的核验记录
- sources/wendao-verify.md           人看的核验表
"""
from __future__ import annotations

import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WD = ROOT / "sources" / "wendao"
TXT = ROOT / "sources" / "wendao-text"
IDX = WD / "index.json"
PUNCT = re.compile(r"[\s\-—_（）()【】\[\]《》〈〉、，。：:；;·.．,_]+")
DOCNO = re.compile(r"[\u4e00-\u9fa5]{1,8}[字〔\[（(]\s*\d{4}\s*[)〕】]\s*\d+\s*号")


def norm(s: str) -> str:
    return PUNCT.sub("", s)


def core_title(name: str) -> str:
    s = re.sub(r"\.(pdf|docx?|xlsx?)$", "", name, flags=re.I)
    s = re.sub(r"^\d+-", "", s)
    m = re.search(r"《([^》]+)》", s)
    if m:
        s = m.group(1)
    elif "号" in s:
        s = s.split("号", 1)[1]
    s = re.sub(r"（审稿稿）|（修订）|\(修订\)|修订版", "", s)
    return norm(s)


def docx_text(p: Path) -> str:
    try:
        import docx  # type: ignore
        return "\n".join(x.text for x in docx.Document(str(p)).paragraphs)
    except Exception:
        try:
            with zipfile.ZipFile(p) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            return re.sub(r"<[^>]+>", "", xml)
        except Exception:
            return ""


def pdf_text(p: Path) -> tuple[str, int]:
    out = TXT / (p.stem.split("_")[0] + ".txt")
    text = ""
    pages = 0
    try:
        from pypdf import PdfReader
        r = PdfReader(str(p))
        pages = len(r.pages)
        chunks = []
        for pg in r.pages[:40]:
            try:
                chunks.append(pg.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(chunks)
    except Exception:
        text = ""
    if len(text.strip()) < 100:
        try:
            subprocess.run(["pdftotext", "-layout", "-l", "40", str(p), str(out)],
                           capture_output=True, timeout=120)
            alt = out.read_text(encoding="utf-8", errors="ignore")
            if len(alt.strip()) > len(text.strip()):
                text = alt
        except Exception:
            pass
    out.write_text(text, encoding="utf-8")
    return text, pages


def main() -> None:
    TXT.mkdir(parents=True, exist_ok=True)
    idx = json.loads(IDX.read_text(encoding="utf-8"))
    rows = []
    for fid, rec in idx.items():
        if not rec.get("path"):
            continue
        p = ROOT / rec["path"]
        if rec["kind"] == "pdf":
            text, pages = pdf_text(p)
        else:
            text, pages = docx_text(p), 0
        text = re.sub(r"[ \t]+", " ", text)
        head = text[:4000]
        nfull = norm(text[:60000])
        fname = rec["name"]
        key = core_title(fname)[:12]
        tkey = core_title(rec.get("title", ""))[:12]
        hit_name = bool(key) and key in nfull
        hit_title = bool(tkey) and tkey in nfull
        docno = DOCNO.search(head)
        flags = []
        if len(text.strip()) < 200:
            flags.append("无文本/扫描件")
        if not (hit_name or hit_title):
            flags.append("标题未对上")
        rows.append({
            "id": fid, "name": fname, "title": rec.get("title", ""), "bytes": rec["bytes"],
            "pages": pages, "chars": len(text.strip()), "hit_name": hit_name,
            "hit_title": hit_title, "docno": docno.group(0) if docno else "",
            "flags": flags, "head": head[:600],
        })

    (ROOT / "sources" / "wendao-verify.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 问道中传引用文件 · 下载核验", "",
             f"- 文件数：**{len(rows)}**",
             f"- 无文本/扫描件：{sum(1 for r in rows if '无文本/扫描件' in r['flags'])}",
             f"- 标题未对上：{sum(1 for r in rows if '标题未对上' in r['flags'])}", "",
             "| # | 文件 | 页 | 字数 | 标题 | 文号 | 标记 |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        mark = "、".join(r["flags"]) or "OK"
        lines.append(f"| {i} | {r['name'][:52]} | {r['pages']} | {r['chars']} | "
                     f"{'✓' if r['hit_name'] or r['hit_title'] else '✗'} | {r['docno']} | {mark} |")
    (ROOT / "sources" / "wendao-verify.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"核验 {len(rows)} 份；无文本 {sum(1 for r in rows if '无文本/扫描件' in r['flags'])}；"
          f"标题未对上 {sum(1 for r in rows if '标题未对上' in r['flags'])}")


if __name__ == "__main__":
    main()
