"""把 sources/wendao 下（新）文件抽成可读文本，供人工判读后做条目。

python tools/wendao_extract_text.py [fileId前8 ...]     # 不给参数=全部
输出：_wendao_text/<前8>.txt（首行元信息 + 正文前 N 字）
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_wendao_text"
IDX = ROOT / "sources" / "wendao" / "index.json"
LIMIT = 3000


def docx_text(p: Path) -> str:
    try:
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paras = []
        for para in root.iter(ns + "p"):
            s = "".join(t.text or "" for t in para.iter(ns + "t"))
            if s.strip():
                paras.append(s.strip())
        return "\n".join(paras)
    except Exception as e:  # noqa: BLE001
        return f"[docx 解析失败 {e}]"


def pdf_text(p: Path) -> str:
    try:
        import pypdf
        r = pypdf.PdfReader(str(p))
        return "\n".join((pg.extract_text() or "") for pg in r.pages[:20])
    except Exception as e:  # noqa: BLE001
        return f"[pdf 解析失败 {e}]"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    idx = json.loads(IDX.read_text(encoding="utf-8"))
    want = set(sys.argv[1:])
    n = 0
    for fid, rec in idx.items():
        if not rec.get("path"):
            continue
        if want and fid[:8] not in want:
            continue
        p = ROOT / rec["path"]
        if not p.exists():
            continue
        name = rec.get("name", "")
        if p.suffix.lower() == ".pdf":
            txt = pdf_text(p)
        elif p.suffix.lower() == ".docx":
            txt = docx_text(p)
        else:
            txt = "[非 pdf/docx，需另处理]"
        body = f"# {rec.get('title','')}\n# file={name}\n# url={rec.get('url','')}\n\n{txt.strip()[:LIMIT]}\n"
        (OUT / f"{fid[:8]}.txt").write_text(body, encoding="utf-8")
        n += 1
    print("导出", n, "份 →", OUT)


if __name__ == "__main__":
    main()
