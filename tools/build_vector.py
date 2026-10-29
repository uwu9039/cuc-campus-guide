"""建立全量官方原文向量库（本地字符 n-gram TF-IDF，不调用外部模型）。

用法：python tools/build_vector.py

覆盖口径
  - sources/ 下所有官方 txt（HTML 采集、公众号官方文、制度汇编、本地 PDF/DOCX/XLSX 抽取文本）
  - 跳过 sources/_quarantine/
  - 跳过整本 huibian-2025.txt（与 huibian/*.txt 分篇重复）
  - 非官方来源（招生软文等）不进库，只在报告里列出
产物
  sources/vector/vectors.npy    float32, L2 归一化
  sources/vector/idf.npy
  sources/vector/chunks.jsonl
  sources/vector/manifest.json
  sources/vector/vector-report.md
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
VDIR = SRC / "vector"
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import vector_index as vi  # noqa: E402

TARGET = 520
OVERLAP = 90
MIN_DOC_CHARS = 80
MIN_CHUNK_CHARS = 40

DIR_INDEX = {
    "local": "local-index.json",
    "huibian": "huibian-index.json",
    "wechat": "wechat-index.json",
    "cdp": "cdp-index.json",
    "crawl": "crawl-index.json",
    "extra": "extra-index.json",
    "chsi": "chsi-index.json",
    "moe": "moe-index.json",
    "national": "national-index.json",
    "wendao-text": "wendao-index.json",
    "wendao-extra": "wendao-extra-index.json",
}

KIND = {
    "": "官网·页面",
    "local": "本地文件",
    "huibian": "制度汇编",
    "wechat": "公众号",
    "cdp": "官网·渲染",
    "crawl": "官网·采集",
    "extra": "官网·精读",
    "chsi": "学信网",
    "moe": "教育部",
    "national": "全国资助",
    "pdf": "PDF",
    "wendao-text": "问道原文",
    "wendao-extra": "官方通知",
}

BLACK_TITLE = re.compile(r"提示信息|404|页面不存在|访问出错|出错了")
HEAD_KW = re.compile(r"(办法|规定|通知|细则|意见|指南|标准|条例|方案|须知|规则|制度|决定|纲要)(（[^）]{0,12}）)?$")


def load_json(name: str) -> dict:
    p = SRC / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def clean_text(text: str) -> str:
    t = (text or "").replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw in t.splitlines():
        s = raw.strip()
        if not s:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if re.fullmatch(r"[-—–\s]*\d{1,4}[-—–\s]*", s):
            continue
        if s in {"首页", "上一篇", "下一篇", "返回", "关闭"}:
            continue
        lines.append(s)
    t = "\n".join(lines)
    t = re.sub(r"[ \t\u3000]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def first_title(text: str) -> str:
    for line in text.splitlines():
        s = line.strip(" #*-—")
        if 4 <= len(s) <= 60:
            return s
    return ""


def _heading_positions(text: str) -> list[tuple[int, str]]:
    """制度汇编一个 txt 常含多份文件；找出「标题 + 文号/第一章」的位置。"""
    lines = text.splitlines()
    offsets = []
    pos = 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1
    out: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not (6 <= len(s) <= 60):
            continue
        if s.startswith(("第", "（", "(", "-", "—", "附件", "附表", "究生")):
            continue
        if any(c in s for c in "。；，,：:、《》"):
            continue
        if not HEAD_KW.search(s):
            continue
        ctx = " ".join(x.strip() for x in lines[i + 1:i + 6] if x.strip())[:160]
        if ("〔" in ctx and "〕" in ctx) or re.search(r"第[一二三四五六七八九十百]+章", ctx) or "第一条" in ctx:
            title = s
            prev = next((x.strip() for x in reversed(lines[max(0, i - 4):i]) if x.strip()), "")
            if 6 <= len(prev) <= 40 and not any(c in prev for c in "。；，,：:（(") and \
                    prev.endswith(("关于", "的", "研究生", "本科生", "本科", "学生", "学院", "工作", "管理")):
                title = prev + title
            out.append((offsets[i], title[:80]))
    return out


def split_sections(text: str, fallback: str) -> list[tuple[str, str]]:
    heads = _heading_positions(text)
    if not heads:
        return [(fallback, text)]
    parts: list[tuple[str, str]] = []
    first_pos = heads[0][0]
    if first_pos > 120:
        parts.append((fallback, text[:first_pos]))
    for j, (pos, title) in enumerate(heads):
        end = heads[j + 1][0] if j + 1 < len(heads) else len(text)
        body = text[pos:end].strip()
        if len(body) < 300 and parts:
            prev_title, prev_body = parts[-1]
            parts[-1] = (prev_title, prev_body + "\n" + body)
        else:
            parts.append((title, body))
    return parts


def chunk_text(text: str) -> list[dict]:
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


def gather_meta(slug: str, directory: str, corpus: dict, indexes: dict) -> dict:
    meta: dict = {}
    specific = indexes.get(directory) or {}
    if slug in specific:
        meta.update(specific[slug])
    if directory == "local" and slug in indexes.get("local", {}):
        meta["file"] = indexes["local"][slug].get("file", "")
    if slug in corpus:
        meta.update(corpus[slug])
        meta["in_corpus"] = True
    meta.setdefault("kind", KIND.get(directory, directory))
    meta.setdefault("official", directory != "wechat")
    meta.setdefault("title", "")
    meta.setdefault("url", "")
    return meta


def doc_priority(path: Path, meta: dict) -> tuple[int, int]:
    score = 0
    if meta.get("in_corpus"):
        score += 8
    if meta.get("used_by_items"):
        score += 4
    d = path.parent.name if path.parent != SRC else ""
    if d in {"pdf", "local", "huibian"}:
        score += 2
    elif d in DIR_INDEX:
        score += 1
    if d == "":
        score -= 3
    return score, -len(str(path))


def main() -> None:
    corpus = load_json("corpus-index.json")
    indexes = {d: load_json(f) for d, f in DIR_INDEX.items()}
    indexes[""] = load_json("index.json")
    indexes["pdf"] = {}

    docs: list[dict] = []
    dropped: list[tuple[str, str]] = []
    excluded: list[tuple[str, str]] = []
    skipped_short: list[str] = []
    skipped_junk: list[str] = []
    seen: dict[str, dict] = {}

    for p in sorted(SRC.rglob("*.txt")):
        if "_quarantine" in p.parts:
            continue
        if p.parent == SRC and p.name == "huibian-2025.txt":
            continue
        d = p.parent.name if p.parent != SRC else ""
        slug = p.stem
        meta = gather_meta(slug, d, corpus, indexes)
        if not meta.get("official"):
            excluded.append((slug, meta.get("title", "")))
            continue
        title = (meta.get("title") or "").strip()
        if BLACK_TITLE.search(title):
            skipped_junk.append(slug)
            continue
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            skipped_short.append(slug)
            continue
        text = clean_text(raw)
        if len(vi.normalize(text)) < MIN_DOC_CHARS:
            skipped_short.append(slug)
            continue
        if not title:
            title = first_title(text) or slug
        doc = {
            "doc": slug,
            "title": title,
            "kind": meta.get("kind") or KIND.get(d, d),
            "url": meta.get("url", ""),
            "official": True,
            "page": meta.get("page_label") or meta.get("page_start"),
            "page_end": meta.get("page_end"),
            "item_ids": meta.get("used_by_items") or [],
            "file": meta.get("file", ""),
            "path": str(p.relative_to(ROOT)).replace("\\", "/"),
            "text": text,
            "_prio": doc_priority(p, meta),
        }
        h = hashlib.sha256(vi.normalize(text).encode()).hexdigest()[:20]
        if h in seen:
            keep, drop = (doc, seen[h]) if doc["_prio"] > seen[h]["_prio"] else (seen[h], doc)
            seen[h] = keep
            dropped.append((drop["path"], keep["path"]))
        else:
            seen[h] = doc

    docs = sorted(seen.values(), key=lambda x: x["doc"])

    sections: list[dict] = []
    for doc in docs:
        parts = split_sections(doc["text"], doc["title"]) if doc["kind"] == "制度汇编" else [(doc["title"], doc["text"])]
        for i, (title, body) in enumerate(parts):
            sections.append({
                **doc,
                "doc": doc["doc"] if len(parts) == 1 else f"{doc['doc']}~{i + 1:02d}",
                "source": doc["doc"],
                "title": title,
                "text": body,
            })

    chunks: list[dict] = []
    for doc in sections:
        pieces = chunk_text(doc["text"])
        if not pieces:
            continue
        for i, piece in enumerate(pieces):
            page = doc.get("page")
            if doc.get("page_end") and page:
                page = f"{page}-{doc['page_end']}" if doc["page_end"] != page else str(page)
            chunks.append({
                "id": f"{doc['doc']}#{i}",
                "doc": doc["doc"],
                "source": doc["source"],
                "title": doc["title"],
                "kind": doc["kind"],
                "url": doc["url"],
                "page": page,
                "item_ids": doc["item_ids"],
                "text": piece["text"],
            })

    if not chunks:
        raise SystemExit("✗ 没有可入库的文本")

    df = np.zeros(vi.DIM, dtype=np.int32)
    for c in chunks:
        for b in vi.features(c["title"] + "。" + c["text"]):
            df[b] += 1
    n = len(chunks)
    idf = (np.log((n + 1) / (df + 1)) + 1).astype(np.float32)

    vecs = np.zeros((n, vi.DIM), dtype=np.float32)
    for i, c in enumerate(chunks):
        vecs[i] = vi.vectorize(c["title"] + "。" + c["text"], idf)
    norms = np.linalg.norm(vecs, axis=1)
    if not np.isfinite(vecs).all() or float(norms.min()) < 0.5:
        raise SystemExit(f"✗ 向量异常：min norm={float(norms.min()):.3f}")

    VDIR.mkdir(parents=True, exist_ok=True)
    np.save(VDIR / "idf.npy", idf)
    np.save(VDIR / "vectors.npy", vecs)
    with (VDIR / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    raw = audit_raw()
    if raw["covered"] < raw["total"]:
        missing = [it["file"] for it in raw["items"] if not it["ok"]]
        raise SystemExit(f"✗ 有原始文件没有对上抽取文本：{missing}")
    kinds = Counter(c["kind"] for c in chunks)
    docs_by_kind = Counter(d["kind"] for d in docs)
    sha = hashlib.sha256(vecs.tobytes()).hexdigest()[:16]
    manifest = {
        "version": "1",
        "built": date.today().isoformat(),
        "dim": vi.DIM,
        "ngrams": "char 1-3",
        "sources": len(docs),
        "sections": len(sections),
        "official_sources": len(docs),
        "corpus_total": len(corpus),
        "corpus_indexed": sum(1 for d in docs if d["doc"] in corpus),
        "chunks": len(chunks),
        "avg_chunk_chars": round(sum(len(c["text"]) for c in chunks) / len(chunks), 1),
        "raw_docs": raw["total"],
        "raw_covered": raw["covered"],
        "skipped": {
            "non_official": len(excluded),
            "too_short": len(skipped_short),
            "junk_title": len(skipped_junk),
            "duplicate_text": len(dropped),
            "missing_text_in_corpus": 9,
        },
        "sha256_vectors": sha,
        "idf": "idf.npy",
        "vectors": "vectors.npy",
        "chunks_file": "chunks.jsonl",
    }
    (VDIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    write_report(manifest, docs, chunks, dropped, excluded, skipped_short, skipped_junk, raw, kinds, docs_by_kind)
    print(f"✓ 文档 {len(docs)} 份 / 分节 {len(sections)} 节，切块 {len(chunks)} 段，维度 {vi.DIM}，向量 {vecs.nbytes/1048576:.1f} MB")
    print(f"  原始文件覆盖 {raw['covered']}/{raw['total']}，非官方跳过 {len(excluded)}，重复丢弃 {len(dropped)}")
    print(f"  产物 {VDIR.relative_to(ROOT)}")


def audit_raw() -> dict:
    """每个本地 PDF/Word/Excel 必须能对上一份抽取文本。"""
    local_index = load_json("local-index.json")
    by_file: dict[str, list[str]] = defaultdict(list)
    for slug, m in local_index.items():
        by_file[m.get("file", "")].append(slug)

    items = []
    covered = 0
    for p in sorted((SRC / "local" / "_files").iterdir()):
        if not p.is_file():
            continue
        slugs = by_file.get(p.name, [])
        txts = [s for s in slugs if (SRC / "local" / f"{s}.txt").exists()]
        ok = bool(txts)
        covered += 1 if ok else 0
        items.append({"file": p.name, "suffix": p.suffix.lower(), "txt": [f"local/{s}.txt" for s in txts], "ok": ok})

    pdf_map = {
        "huibian-2025.pdf": [str(x.relative_to(ROOT)).replace("\\", "/") for x in sorted((SRC / "huibian").glob("*.txt"))],
        "tiyu-2025.pdf": ["sources/pdf/tiyu-2025.txt"],
        "tizhi-2024.pdf": ["sources/pdf/tizhi-2024.txt"],
        "xuanke-2025.pdf": ["sources/pdf/xuanke-2025.txt"],
        "xueji-official.pdf": ["sources/pdf/xueji-2025.txt"],
    }
    for p in sorted((SRC / "pdf").glob("*.pdf")):
        txts = [t for t in pdf_map.get(p.name, []) if (ROOT / t).exists()]
        ok = bool(txts)
        covered += 1 if ok else 0
        items.append({"file": p.name, "suffix": ".pdf", "txt": txts, "ok": ok})

    return {"total": len(items), "covered": covered, "items": items}


def write_report(manifest, docs, chunks, dropped, excluded, short, junk, raw, kinds, docs_by_kind) -> None:
    lines = [
        "# 原文向量库报告", "",
        f"- 建成：{manifest['built']}",
        f"- 文档：**{manifest['sources']}** 份（官方），按制度汇编分节 {manifest.get('sections', manifest['sources'])} 节",
        f"- 切块：**{manifest['chunks']}** 段，平均 {manifest['avg_chunk_chars']} 字",
        f"- 维度：{manifest['dim']}（字符 1–3 gram TF-IDF，L2 归一化）",
        f"- 原始文件：**{raw['covered']}/{raw['total']}** 已对上抽取文本",
        f"- 语料库：{manifest['corpus_indexed']}/{manifest['corpus_total']} 条进入索引",
        f"- 跳过：非官方 {len(excluded)}、重复正文 {len(dropped)}、过短 {len(short)}、导航页 {len(junk)}",
        "", "## 原始文件覆盖", "",
        "| 文件 | 类型 | 抽取文本 | 状态 |", "|---|---|---|---|",
    ]
    for it in raw["items"]:
        txt = "<br>".join(it["txt"][:3]) + ("<br>…" if len(it["txt"]) > 3 else "")
        lines.append(f"| {it['file'][:46]} | {it['suffix']} | {txt or '—'} | {'✓' if it['ok'] else '✗'} |")

    lines += ["", "## 各类型文档 / 切块", "", "| 类型 | 文档 | 切块 |", "|---|---|---|"]
    for k, v in docs_by_kind.most_common():
        lines.append(f"| {k} | {v} | {kinds.get(k, 0)} |")

    if excluded:
        lines += ["", "## 未入库：非官方来源", ""]
        for slug, title in excluded:
            lines.append(f"- {title or slug}（{slug}）")
    if dropped:
        lines += ["", "## 去重：保留 / 丢弃", ""]
        for drop, keep in dropped:
            lines.append(f"- 丢弃 `{drop}` → 保留 `{keep}`")
    if short or junk:
        lines += ["", "## 未入库：过短 / 导航页", ""]
        for s in short + junk:
            lines.append(f"- {s}")

    lines += ["", "## 抽样检索", ""]
    for q in ("校园卡丢了怎么办", "奖学金怎么申请", "宿舍报修找谁", "成绩复核", "补办学生证"):
        hits = vi.search(q, k=3)
        lines.append(f"**{q}**")
        if not hits:
            lines.append("- （无结果）")
        for h in hits:
            lines.append(f"- {h['score']:.3f} · {h['title']} · {h['snippet'][:70]}")
        lines.append("")
    (VDIR / "vector-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
