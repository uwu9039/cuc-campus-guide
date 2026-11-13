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

节级 chunk（③，2026-11-12 接入）
  - 每份 `_review_items/sections/<slug>.json` 的每一节另做一段 `kind="section"`，
    与 doc chunk 并存；doc chunk 的字段与切法一个字不动。
  - 全量重建太贵，日常用增量：
        python tools/build_vector.py --sections-only   # 只重算节 chunk，doc 行原样搬运
        python tools/build_vector.py --no-sections     # 退回纯 doc 库
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


# ---------------------------------------------------------------- ③ 节级 chunk
#
# 与 doc chunk 并存的第二路：每份 _review_items/sections/<slug>.json 的每一节
# 单独成 chunk，kind="section"。doc chunk 的字段与切法一个字不动。
#
# 口径：text = heading + "\n" + 原文 lines[a..b]（与 sections 文件同一把尺子），截到 TARGET。
#
# 跳过规则（2026-11-12 实测修正）：任务书原写「节文本 < 80 字符 → 跳过」，用来剔除标题页/空节。
# 但按字数卡会把**单句条款**一起丢掉——「每名学生每期只能申请修读一个微专业」是 21 个字，
# 却正好是用户要的那句答案；20 条章级问句里有 13 条的期望节因此连 chunk 都不存在，
# 节级检索永远不可能命中它们。改成看「正文里除了标题还剩多少内容」：
# 剩不到 SEC_MIN_EXTRA 个字，才算标题页/空节。

SEC_DIR = ROOT / "_review_items" / "sections"
SEC_MIN_CHARS = 12      # 绝对下限：连一句话都不到的不值得单独成段
SEC_MIN_EXTRA = 16      # 去掉标题后至少还剩这么多字，才算「这一节有正文」
SEC_KIND = "section"

# sources/ 下正文可能落的目录（与 tools/vector_add.py find_text 同序）
TEXT_DIRS = ("", "pdf", "huibian", "wendao-text", "wechat", "crawl", "cdp", "local",
             "attachments/text", "ilib-text", "ilib-list-text", "wendao-extra",
             "chsi", "moe", "national", "extra")


def find_text(slug: str) -> Path | None:
    for d in TEXT_DIRS:
        p = (SRC / d / f"{slug}.txt") if d else (SRC / f"{slug}.txt")
        if p.exists():
            return p
    return None


def doc_url(slug: str, indexes: dict) -> str:
    for d in ("", *TEXT_DIRS):
        meta = indexes.get(d) or {}
        one = meta.get(slug)
        if isinstance(one, dict) and one.get("url"):
            return str(one["url"])
    return ""


def section_records(indexes: dict) -> list[dict]:
    """把 _review_items/sections/*.json 摊成 kind="section" 的 chunk（不含向量）。"""
    out: list[dict] = []
    if not SEC_DIR.is_dir():
        return out
    for p in sorted(SEC_DIR.glob("*.json")):
        if p.name.startswith("_"):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        slug = str(d.get("key") or p.stem)
        tp = find_text(slug)
        if tp is None:
            continue
        try:
            lines = tp.read_text(encoding="utf-8", errors="ignore").split("\n")
        except OSError:
            continue
        doc_title = str(d.get("title") or slug)
        url = doc_url(slug, indexes)
        doc_items = [str(x) for x in (d.get("items") or [])]
        used: set[str] = set()
        for sec in d.get("sections") or []:
            if not isinstance(sec, dict):
                continue
            lr = sec.get("lines") or [0, 0]
            try:
                a, b = int(lr[0]), int(lr[1])
            except (TypeError, ValueError, IndexError):
                continue
            if not (1 <= a <= b <= len(lines)):
                continue
            heading = str(sec.get("heading") or "").strip()
            body = "\n".join(lines[a - 1:b])
            body_core = vi.normalize(body)
            if len(body_core) < SEC_MIN_CHARS:
                continue
            # 正文里除了标题还剩多少：只剩标题的节（标题页/空节）不成段，单句条款要留下
            head_core = vi.normalize(heading)
            extra = body_core.replace(head_core, "", 1) if head_core and head_core in body_core else body_core
            if len(extra) < SEC_MIN_EXTRA:
                continue
            text = (heading + "\n" + body).strip()[:TARGET]
            no = str(sec.get("no") or "")
            cid = f"{slug}#s{no}"
            k = 2
            while cid in used:
                cid = f"{slug}#s{no}-{k}"
                k += 1
            used.add(cid)
            items = [str(x) for x in (sec.get("items") or [])] or doc_items[:3]
            out.append({
                "id": cid,
                "doc": slug,
                "source": slug,
                "title": f"{doc_title} · {heading}",
                "kind": SEC_KIND,
                "url": url,
                "page": None,
                "lines": [a, b],
                "section": {"no": no, "heading": heading},
                "item_ids": items,
                "text": text,
            })
    return out


def write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def main_sections_only() -> None:
    """只重算节 chunk，doc chunk 原样搬运（③ 的分批补法）。

    doc chunk 的行序与向量逐字节保留，所以 /api/search 与向量腿在 doc 侧的口径不变；
    新增的只有 kind="section" 的行。首次运行前把老头两份产物备份成 .bak。
    """
    chunks_p = VDIR / "chunks.jsonl"
    vec_p = VDIR / "vectors.npy"
    idf_p = VDIR / "idf.npy"
    if not (chunks_p.exists() and vec_p.exists() and idf_p.exists()):
        raise SystemExit("✗ 向量库还不存在，先跑一次全量 build_vector.py")

    indexes = {d: load_json(f) for d, f in DIR_INDEX.items()}
    indexes[""] = load_json("index.json")
    indexes["pdf"] = {}

    old = [json.loads(x) for x in chunks_p.open(encoding="utf-8") if x.strip()]
    vectors = np.load(vec_p)
    if len(old) != len(vectors):
        raise SystemExit(f"✗ chunks({len(old)}) 与 vectors({len(vectors)}) 行数对不上，先全量重建")
    idf = np.load(idf_p)

    keep = [i for i, c in enumerate(old) if str(c.get("kind") or "") != SEC_KIND]
    kept = [old[i] for i in keep]
    kept_vecs = vectors[keep] if len(keep) else vectors[:0]

    sec = section_records(indexes)
    new_vecs = np.zeros((len(sec), vi.DIM), dtype=np.float32)
    for i, c in enumerate(sec):
        new_vecs[i] = vi.vectorize(c["title"] + "。" + c["text"], idf)
    if len(sec):
        norms = np.linalg.norm(new_vecs, axis=1)
        if not np.isfinite(new_vecs).all() or float(norms.min()) < 0.5:
            raise SystemExit(f"✗ 节向量异常：min norm={float(norms.min()):.3f}")

    mat = np.vstack([kept_vecs, new_vecs]) if len(sec) else kept_vecs
    all_chunks = kept + sec

    # 回滚备份：只做一次，别把上一版的 .bak 覆盖掉
    for p in (vec_p, chunks_p):
        bak = p.with_suffix(p.suffix + ".bak")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())

    write_atomic(vec_p, _np_bytes(mat))
    with chunks_p.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    mf_p = VDIR / "manifest.json"
    mf = json.loads(mf_p.read_text(encoding="utf-8"))
    mf.update({
        "version": "2",
        "built": date.today().isoformat(),
        "chunks": len(all_chunks),
        "section_chunks": len(sec),
        "sections_indexed": len({c["doc"] for c in sec}),
        "avg_chunk_chars": round(sum(len(c["text"]) for c in all_chunks) / max(1, len(all_chunks)), 1),
        "sha256_vectors": hashlib.sha256(mat.tobytes()).hexdigest()[:16],
        "last_sections_only": {"doc_chunks": len(kept), "section_chunks": len(sec),
                               "docs": len({c["doc"] for c in sec})},
    })
    mf_p.write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 节 chunk {len(sec)} 段 / {mf['sections_indexed']} 份文档；doc chunk {len(kept)} 段原样保留")
    print(f"  库 {len(vectors)} → {len(mat)} 行；chunks.jsonl "
          f"{chunks_p.stat().st_size / 1048576:.1f} MB；vectors.npy {mat.nbytes / 1048576:.1f} MB")


def _np_bytes(arr) -> bytes:
    import io

    buf = io.BytesIO()
    np.save(buf, arr)
    return buf.getvalue()


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

    # ③ 节级 chunk：与 doc chunk 并存，kind 区分。`--no-sections` 可退回纯 doc 库。
    sec_chunks: list[dict] = [] if "--no-sections" in sys.argv else section_records(indexes)
    chunks.extend(sec_chunks)

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
        "version": "2",
        "built": date.today().isoformat(),
        "dim": vi.DIM,
        "ngrams": "char 1-3",
        "sources": len(docs),
        "sections": len(sections),
        "official_sources": len(docs),
        "corpus_total": len(corpus),
        "corpus_indexed": sum(1 for d in docs if d["doc"] in corpus),
        "chunks": len(chunks),
        "section_chunks": len(sec_chunks),
        "sections_indexed": len({c["doc"] for c in sec_chunks}),
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
    for p in sorted((SRC / "pdf").glob("wzy-2026-*.pdf")):
        pdf_map[p.name] = [f"sources/pdf/{p.stem}.txt"]
    # 信通学院 2027 推免材料（实施细则 + 附件1-5 原件与抽取文本同名配对）
    for p in sorted((SRC / "pdf").glob("xt-tuimian-2027-*.pdf")):
        pdf_map[p.name] = [f"sources/pdf/{p.stem}.txt"]
    # 学生创作成果管理与服务平台操作手册（图片版 PDF，正文为 sources/ 根目录的逐页转录）
    pdf_map["cz-czjg-platform.pdf"] = ["sources/cz-czjg-platform.txt"]
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
    if "--sections-only" in sys.argv:
        main_sections_only()
    else:
        main()
