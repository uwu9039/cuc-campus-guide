"""增量把一份新文件加进向量库——**不重建**。

为什么需要：补文件只做条目、不把它塞进向量库，用户在语义检索里就永远问不到它。
但完整重建（tools/build_vector.py）是全量重算 2,112 份 / 12,479 段 / 100MB，很慢。
本脚本只做增量：
  1. 用**现有 idf**（idf.npy）给新文件切块并算向量；
  2. append 到 chunks.jsonl、vstack 到 vectors.npy（原子替换）；
  3. 更新 manifest 的计数与 sha。
idf 会因新增文档轻微漂移，但查询端也用同一份 idf，库内自洽；需要严格一致时再全量重建。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/vector_add.py cz-czjg-platform
  ./.venv/Scripts/python.exe -X utf8 -u tools/vector_add.py --dry-run <slug> [...]
  ./.venv/Scripts/python.exe -X utf8 -u tools/vector_add.py --sections <slug> [...]   # ③ 只补节 chunk

--sections 与默认模式的区别：默认模式加的是整份文件的 doc chunk（已在库的 slug 会跳过）；
--sections 只处理这几份文档的**节 chunk**，先把它们已存在的节 chunk 摘掉再按
`_review_items/sections/<slug>.json` 重建，doc chunk 一行不动。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import vector_index as vi  # noqa: E402

VDIR = ROOT / "sources" / "vector"
TARGET, OVERLAP, MIN_CHUNK_CHARS = 520, 90, 40


def chunk_text(text: str) -> list[dict]:
    """与 tools/build_vector.py 的 chunk_text 保持一致（改那边要同步改这里）。"""
    out: list[dict] = []
    n = len(text)
    start = 0
    while start < n:
        end = min(n, start + TARGET)
        if end < n:
            lo = start + int(TARGET * 0.6)
            window = text[lo:end]
            pos = max((window.rfind(x) for x in "。；！？\n"), default=-1)
            if pos >= 0:
                end = lo + pos + 1
        piece = re.sub(r"\s+", " ", text[start:end]).strip()
        if len(vi.normalize(piece)) >= MIN_CHUNK_CHARS:
            out.append({"text": piece, "start": start, "end": end})
        if end >= n:
            break
        nxt = end - OVERLAP
        if nxt <= start:
            nxt = start + 1
        start = nxt
    return out


def find_text(slug: str) -> Path | None:
    for d in ("", "pdf", "huibian", "wendao-text", "wechat", "crawl", "cdp", "local",
              "attachments/text", "ilib-text", "ilib-list-text", "wendao-extra", "chsi", "moe",
              "national", "extra"):
        p = (ROOT / "sources" / d / f"{slug}.txt") if d else (ROOT / "sources" / f"{slug}.txt")
        if p.exists():
            return p
    return None


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    sections = "--sections" in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)
    if sections:
        main_sections(args, dry)
        return

    index = json.loads((ROOT / "sources" / "index.json").read_text(encoding="utf-8"))
    corpus = json.loads((ROOT / "sources" / "corpus-index.json").read_text(encoding="utf-8"))
    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]

    chunks_path = VDIR / "chunks.jsonl"
    old_chunks = [json.loads(x) for x in chunks_path.open(encoding="utf-8") if x.strip()]
    have = {c.get("doc") for c in old_chunks}

    # 条目关联：evidence.src 或 source[].slug 指向该文件
    link: dict[str, set[str]] = {}
    for it in items:
        refs = set()
        for ev in (it.get("evidence") or {}).values():
            if not isinstance(ev, dict):
                continue
            for s in (ev.get("sources") or [ev]):
                if s.get("src"):
                    refs.add(str(s["src"]))
        for s in it.get("source") or []:
            if isinstance(s, dict) and s.get("slug"):
                refs.add(str(s["slug"]))
        for r in refs:
            link.setdefault(r, set()).add(it["id"])

    idf = np.load(VDIR / "idf.npy")
    vectors = np.load(VDIR / "vectors.npy")

    new_chunks, new_vecs = [], []
    for slug in args:
        if slug in have:
            print(f"· {slug}: 已在库中，跳过")
            continue
        p = find_text(slug)
        if not p:
            print(f"✗ {slug}: 找不到正文 .txt，跳过")
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        meta = index.get(slug) or corpus.get(slug) or {}
        title = str(meta.get("title") or slug)
        kind = str((corpus.get(slug) or {}).get("kind") or ("PDF" if meta.get("kind") == "pdf" else "文件"))
        url = str(meta.get("url") or "")
        pieces = chunk_text(text)
        if not pieces:
            print(f"✗ {slug}: 切不出块（正文 {len(text)} 字）")
            continue
        ids = sorted(link.get(slug, ()))
        for i, piece in enumerate(pieces):
            new_chunks.append({
                "id": f"{slug}#{i}", "doc": slug, "source": slug, "title": title,
                "kind": kind, "url": url, "page": None,
                "item_ids": ids, "text": piece["text"],
            })
            new_vecs.append(vi.vectorize(title + "。" + piece["text"], idf).astype(np.float32))
        print(f"✓ {slug}: {len(pieces)} 块，关联条目 {len(ids)} 条（{', '.join(ids[:3])}{'…' if len(ids) > 3 else ''}）")

    if not new_chunks:
        print("没有可加的块，退出")
        return
    mat = np.vstack([vectors, np.array(new_vecs, dtype=np.float32)])
    if dry:
        print(f"[dry-run] 将新增 {len(new_chunks)} 块，库从 {len(vectors)} → {len(mat)} 行")
        return

    # 原子写：先写临时文件再替换（np.save 给文件句柄，避免它自动补 .npy 后缀）
    tmp_v = VDIR / "vectors.npy.tmp"
    with open(tmp_v, "wb") as fh:
        np.save(fh, mat)
    os.replace(tmp_v, VDIR / "vectors.npy")
    with chunks_path.open("a", encoding="utf-8") as f:
        for c in new_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    mf_p = VDIR / "manifest.json"
    mf = json.loads(mf_p.read_text(encoding="utf-8"))
    added_docs = {c["doc"] for c in new_chunks}
    all_chunks = old_chunks + new_chunks
    indexed_docs = {c.get("doc") for c in all_chunks}
    # manifest.sources 是「入档文档数」，只能 +新增数，不能用 chunks 的 doc 去重重算
    mf.update({
        "built": date.today().isoformat(),
        "sources": int(mf.get("sources") or 0) + len(added_docs),
        "official_sources": int(mf.get("official_sources") or 0) + len(added_docs),
        "chunks": len(all_chunks),
        "avg_chunk_chars": round(sum(len(c["text"]) for c in all_chunks) / len(all_chunks), 1),
        # 原来这里写的是未定义的 docs，增量一跑就 NameError（2026-11-12 修）：
        # 要算的是「已在索引里的文档中，有多少份在语料库里」
        "corpus_indexed": sum(1 for d in indexed_docs if d in corpus),
        "sha256_vectors": hashlib.sha256(mat.tobytes()).hexdigest()[:16],
        "last_incremental": {"added": sorted({c["doc"] for c in new_chunks}), "chunks": len(new_chunks)},
    })
    mf_p.write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写入完成：库 {len(vectors)} → {len(mat)} 行；manifest sources={mf['sources']} chunks={mf['chunks']}")


def main_sections(args: list[str], dry: bool) -> None:
    """③ 只补这几份文档的节 chunk：摘掉旧的节 chunk，按 sections/*.json 重建。"""
    import build_vector as bv

    want = set(args)
    indexes = {d: bv.load_json(f) for d, f in bv.DIR_INDEX.items()}
    indexes[""] = bv.load_json("index.json")
    indexes["pdf"] = {}

    chunks_p = VDIR / "chunks.jsonl"
    old_chunks = [json.loads(x) for x in chunks_p.open(encoding="utf-8") if x.strip()]
    vectors = np.load(VDIR / "vectors.npy")
    idf = np.load(VDIR / "idf.npy")

    keep = [i for i, c in enumerate(old_chunks)
            if not (str(c.get("kind") or "") == bv.SEC_KIND and c.get("doc") in want)]
    kept = [old_chunks[i] for i in keep]
    dropped = len(old_chunks) - len(kept)

    fresh = [c for c in bv.section_records(indexes) if c.get("doc") in want]
    if not fresh:
        print(f"✗ {sorted(want)}：没有可用的节 chunk（sections/*.json 缺失或每节都太短）")
        return
    new_vecs = np.zeros((len(fresh), vi.DIM), dtype=np.float32)
    for i, c in enumerate(fresh):
        new_vecs[i] = vi.vectorize(c["title"] + "。" + c["text"], idf)

    if dry:
        print(f"[dry-run] 摘掉 {dropped} 段旧节 chunk，新增 {len(fresh)} 段，"
              f"库 {len(old_chunks)} → {len(kept) + len(fresh)} 行")
        return

    mat = np.vstack([vectors[keep], new_vecs]) if len(keep) else new_vecs
    all_chunks = kept + fresh
    for p in (VDIR / "vectors.npy", chunks_p):
        bak = p.with_suffix(p.suffix + ".bak")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())

    bv.write_atomic(VDIR / "vectors.npy", bv._np_bytes(mat))
    with chunks_p.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    mf_p = VDIR / "manifest.json"
    mf = json.loads(mf_p.read_text(encoding="utf-8"))
    mf.update({
        "version": "2",
        "built": date.today().isoformat(),
        "chunks": len(all_chunks),
        "section_chunks": sum(1 for c in all_chunks if str(c.get("kind") or "") == bv.SEC_KIND),
        "sections_indexed": len({c["doc"] for c in all_chunks
                                 if str(c.get("kind") or "") == bv.SEC_KIND}),
        "avg_chunk_chars": round(sum(len(c["text"]) for c in all_chunks) / len(all_chunks), 1),
        "sha256_vectors": hashlib.sha256(mat.tobytes()).hexdigest()[:16],
        "last_sections_add": {"docs": sorted(want), "chunks": len(fresh), "dropped": dropped},
    })
    mf_p.write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {sorted(want)}：摘掉 {dropped} 段旧节 chunk，新增 {len(fresh)} 段；"
          f"库 {len(old_chunks)} → {len(mat)} 行")


if __name__ == "__main__":
    main()
