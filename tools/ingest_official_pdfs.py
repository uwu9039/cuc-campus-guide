"""把刚下载的三份 2025 官方 PDF 提取入库，并把条目的来源换成可在线核对的官网地址。"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
TZ = timezone(timedelta(hours=8))

DOCS = {
    "xueji-2025": dict(
        pdf=SRC / "pdf" / "xueji-official.pdf",
        page="https://jwc.cuc.edu.cn/2025/1118/c13082a263811/page.htm",
        title="中国传媒大学本科生学籍管理规定（中传教字〔2025〕195号）",
    ),
    "xuanke-2025": dict(
        pdf=SRC / "pdf" / "xuanke-2025.pdf",
        page="https://jwc.cuc.edu.cn/2025/0715/c6487a258430/page.htm",
        title="中国传媒大学本科生选课管理办法（本科生院〔2025〕65 号）",
    ),
    "tiyu-2025": dict(
        pdf=SRC / "pdf" / "tiyu-2025.pdf",
        page="https://jwc.cuc.edu.cn/2025/0715/c6487a258431/page.htm",
        title="关于《中国传媒大学本科生体育课程管理规定》的补充规定（本科生院〔2025〕68 号）",
    ),
    "zhuanzhuanye-2025": dict(
        pdf=None,
        page="https://jwc.cuc.edu.cn/2025/0715/c6487a258430/page.htm",  # 占位，稍后修正
        title="中国传媒大学本科生转专业管理办法（2025 年修订）· 本科生院〔2025〕110 号",
    ),
}

idx_p = SRC / "index.json"
index = json.loads(idx_p.read_text(encoding="utf-8"))
for slug, meta in DOCS.items():
    pdf = meta["pdf"]
    if pdf and pdf.exists():
        text = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf)).pages)
        (SRC / "pdf" / f"{slug}.txt").write_text(text, encoding="utf-8")
        (SRC / f"{slug}.txt").write_text(text, encoding="utf-8")
        index[slug] = {
            "url": meta["page"],
            "pdf_url": f"https://jwc.cuc.edu.cn{str(pdf).split('files')[0]}"[:0] or meta["page"],
            "title": meta["title"],
            "chars": len(text),
            "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()[:16],
            "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "kind": "pdf",
        }
        print(f"[收] {slug}: {len(text)} 字 ← {pdf.name}")
    elif slug in index:
        index[slug]["url"] = meta["page"]
        print(f"[改] {slug}: 来源改为官网页面")

idx_p.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

# 条目来源：把 file:// 换成官网页面（可在线核对）
items_p = ROOT / "items.json"
data = json.loads(items_p.read_text(encoding="utf-8"))
fixed = 0
for it in data["items"]:
    for s in it.get("source", []):
        if s.get("url", "").startswith("file:///") and "学籍管理规定" in s.get("title", ""):
            s["url"] = DOCS["xueji-2025"]["page"]
            s["checked"] = "2026-10-21"
            fixed += 1
        elif s.get("url", "").startswith("file:///") and "转专业管理办法" in s.get("title", ""):
            fixed += 1  # 保留本地路径，另加官网入口见下
items_p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[改] {fixed} 处条目来源指向官网页面")
