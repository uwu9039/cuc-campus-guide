"""为下载的问道原文生成 sources/wendao-index.json，供向量库识别标题与来源。

只登记有正文的（>=300 字），扫描件/空文本跳过。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
WD = SRC / "wendao"


def clean_title(name: str) -> str:
    t = re.sub(r"\.(pdf|docx?|xlsx?)$", "", name, flags=re.I)
    t = re.sub(r"_view$", "", t, flags=re.I)
    t = re.sub(r"^\d+-", "", t)
    t = re.sub(r"[_ ]20\d{2}-\d{2}-\d{2}$", "", t)
    return t.strip()


def main() -> None:
    idx = json.loads((WD / "index.json").read_text(encoding="utf-8"))
    verify = {r["id"]: r for r in json.loads((SRC / "wendao-verify.json").read_text(encoding="utf-8"))}
    old = {}
    for name in ("kb-catalog.json", "kb-catalog-new.json"):
        p = ROOT / name
        if p.exists():
            for d in json.loads(p.read_text(encoding="utf-8")):
                old.setdefault(d["id"], {"title": d.get("title", ""), "queries": d.get("queries", [])})

    out = {}
    skipped = []
    for fid, rec in idx.items():
        v = verify.get(fid)
        title = clean_title(rec.get("name", ""))
        if "模板" in title:
            skipped.append((rec.get("name", fid), v.get("chars", 0) if v else 0))
            continue
        if not v or v.get("chars", 0) < 80:
            skipped.append((rec.get("name", fid), v.get("chars", 0) if v else 0))
            continue
        slug = fid[:8]
        out[slug] = {
            "title": title,
            "url": f"https://aihub.cuc.edu.cn/doc/view/fileview?fileId={fid}",
            "file": rec.get("path", ""),
            "chars": v["chars"],
            "pages": v.get("pages", 0),
            "kind": "问道原文",
            "official": True,
            "fileId": fid,
            "queries": old.get(fid, {}).get("queries", []),
        }

    (SRC / "wendao-index.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"登记 {len(out)} 份，跳过 {len(skipped)} 份")
    for n, c in skipped:
        print("  跳过", n[:50], c)


if __name__ == "__main__":
    main()
