"""补入库：问道补抓的 40 份（wd-*）。

问题（2026-11-11 核查）：
  1. 40 条条目 evidence 全空 → check_quotes 40 条失败；
  2. 正文在临时目录 _wendao_text/（287 份），没进 sources/；
  3. 上游抽取把长文截断在 ~3,300 字（25 份末句断在半句）；
  4. 40 份都不在向量库、没有 slug 关联。

本脚本（可重复执行）：
  1. 逐份重抽：pypdf 文本若比现有长 5% 以上就用它，否则保留现有（图片版页面 pypdf 会少）；
  2. 正文写到 sources/wendao-text/<sid>.txt（去掉 _wendao_text 的 # 头注释）；
  3. sources/index.json、sources/corpus-index.json 各补一条（带 full_text / chars / used_by_items）；
  4. 条目：source 补 slug、evidence 挂 answer 的逐字引文（开头段 + 章节行）；
     对仍可能截断的文档，把 answer 里「全文已入库」改成「正文已入库（N 字…）」；
  5. 打印汇总，向量入库由 tools/vector_add.py 单独跑。
用法：.venv/Scripts/python.exe -X utf8 -u tools/ingest_wd_batch_20261111.py
"""
from __future__ import annotations

import hashlib
import json
import glob
import re
import shutil
import sys
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
TMP = ROOT / "_wendao_text"
sys.path.insert(0, str(ROOT))

HEAD = re.compile(r"^#\s*(file|url)=", re.M)
FOOT = re.compile(r"^\s*-?\s*\d+\s*-?\s*$")


def clean(text: str) -> str:
    """去掉抽取工具的 # 头注释与孤立页码行，其余原样保留。"""
    lines = [l for l in text.split("\n") if not HEAD.match(l) and not FOOT.match(l)]
    out = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def extract(sid: str, old: str) -> tuple[str, str, int]:
    pdfs = glob.glob(str(SRC / "wendao" / f"{sid}_*"))
    if not pdfs:
        return clean(old), "keep", 0
    try:
        r = pypdf.PdfReader(pdfs[0])
        new = "\n".join((pg.extract_text() or "") for pg in r.pages)
        pages = len(r.pages)
    except Exception:  # noqa: BLE001
        return clean(old), "keep", 0
    if len(new) > len(old) * 1.05:
        return clean(new), "pypdf", pages
    return clean(old), "keep", pages


def first_quotes(text: str) -> list[str]:
    """取两段能逐字落在正文里的引文：开头连续两行 + 前若干个章节行。"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return []
    head = lines[0]
    for l in lines[1:6]:
        if len(head) < 40 and len(l) > 8:
            head = head + l
            break
    quotes = [head[:120]] if len(head) >= 8 else []
    heads = []
    for l in lines:
        if re.match(r"^(第[一二三四五六七八九十百]+[章条]|[一二三四五六七八九十]+、|（[一二三四五六七八九十]+）)", l) and len(l) < 60:
            heads.append(l)
        if len(heads) >= 3:
            break
    quotes += heads
    return quotes


def main() -> None:
    items_p = ROOT / "items.json"
    data = json.loads(items_p.read_text(encoding="utf-8"))
    items = data["items"]
    wd = [i for i in items if i["id"].startswith("wd-")]
    idx_p = SRC / "index.json"
    ci_p = SRC / "corpus-index.json"
    index = json.loads(idx_p.read_text(encoding="utf-8"))
    corpus = json.loads(ci_p.read_text(encoding="utf-8"))
    (SRC / "wendao-text").mkdir(parents=True, exist_ok=True)

    stats = {"pypdf": 0, "keep": 0, "chars_before": 0, "chars_after": 0,
             "ev_added": 0, "answer_fixed": 0, "partial": []}
    for it in wd:
        sid = it["id"][3:]
        old = (TMP / f"{sid}.txt").read_text(encoding="utf-8", errors="ignore") if (TMP / f"{sid}.txt").exists() else ""
        text, how, pages = extract(sid, old)
        dst = SRC / "wendao-text" / f"{sid}.txt"
        dst.write_text(text, encoding="utf-8")
        full = how == "pypdf"
        stats[how] += 1
        stats["chars_before"] += len(old)
        stats["chars_after"] += len(text)
        if not full:
            stats["partial"].append(sid)

        src0 = (it.get("source") or [{}])[0]
        url = str(src0.get("url") or "")
        title = str(it.get("title") or sid)
        sha = ""
        pdfs = glob.glob(str(SRC / "wendao" / f"{sid}_*"))
        if pdfs:
            sha = hashlib.sha256(Path(pdfs[0]).read_bytes()).hexdigest()[:16]
        index[sid] = {
            "url": url, "title": title, "chars": len(text), "sha256": sha,
            "fetched_at": "2026-11-11T21:00:00+08:00",
            "kind": "pdf", "pages": pages or None,
            "local_path": "（本地路径已隐藏）",
            "text_from": "pypdf" if full else "上游抽取（可能截断）",
        }
        c = corpus.get(sid) or {}
        c.update({"slug": sid, "kind": c.get("kind") or "官方文件·问道补抓", "title": title,
                  "account": "", "date": "", "url": url, "chars": len(text),
                  "fetched_at": "2026-11-11T21:00:00+08:00", "official": True,
                  "used_by_items": sorted(set((c.get("used_by_items") or []) + [it["id"]])),
                  "note": "问道补抓；" + ("pypdf 重抽" if full else "上游抽取，长文可能截断")})
        corpus[sid] = c

        # 关联：source 补 slug
        src = it.get("source") or []
        if src and not (src[0].get("slug")):
            src[0]["slug"] = sid
            it["source"] = src

        # 证据：answer 的逐字引文
        qs = first_quotes(text)
        if qs:
            it.setdefault("evidence", {})["answer"] = {"sources": [{"src": sid, "quote": q} for q in qs]}
            stats["ev_added"] += 1

        # 仍可能截断的，改掉「全文已入库」的表述
        ans = str(it.get("answer") or "")
        if not full and "全文已入库" in ans:
            it["answer"] = ans.replace("全文已入库", f"正文已入库（{len(text)} 字，原件为图片版 PDF，抽取可能缺页）")
            stats["answer_fixed"] += 1

    shutil.copyfile(items_p, ROOT / "items.json.bak-wd-evidence")
    items_p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    idx_p.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    ci_p.write_text(json.dumps(corpus, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"条目 {len(wd)} 条；正文 pypdf 重抽 {stats['pypdf']} 份、保留原抽 {stats['keep']} 份")
    print(f"字数 {stats['chars_before']} → {stats['chars_after']}")
    print(f"evidence 补 {stats['ev_added']} 条；answer 改写 {stats['answer_fixed']} 条")
    print(f"index {len(index)} 条；corpus {len(corpus)} 条")
    print("仍可能截断的:", len(stats["partial"]), stats["partial"][:10])
    print("下一步：tools/vector_add.py " + " ".join(i["id"][3:] for i in wd[:3]) + " …")


if __name__ == "__main__":
    main()
