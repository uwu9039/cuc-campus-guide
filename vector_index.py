"""本地字符 n-gram 向量检索：不依赖模型、不联网，给原文库做辅助检索。

构建见 tools/build_vector.py；查询与构建必须共用本文件的 normalize/weigh/idf。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
VDIR = ROOT / "sources" / "vector"
DIM = 2048
WEIGHTS = {1: 0.45, 2: 1.0, 3: 0.65}
KEEP = re.compile(r"[0-9a-z\u4e00-\u9fff]+")

_CACHE: dict[str, Any] | None = None
_CACHE_MTIME: float = 0.0


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").lower()
    return "".join(KEEP.findall(t))


def bucket(gram: str) -> int:
    h = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "little") & (DIM - 1)


def features(text: str) -> dict[int, float]:
    s = normalize(text)
    out: dict[int, float] = {}
    n_chars = len(s)
    for n, w in WEIGHTS.items():
        if n_chars < n:
            continue
        for i in range(n_chars - n + 1):
            gram = s[i:i + n]
            if n == 1 and not ("\u4e00" <= gram <= "\u9fff" or gram.isalnum()):
                continue
            b = bucket(gram)
            out[b] = out.get(b, 0.0) + w
    return out


def vectorize(text: str, idf: Any) -> Any:
    import numpy as np

    vec = np.zeros(DIM, dtype=np.float32)
    for b, tf in features(text).items():
        vec[b] += tf * float(idf[b])
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec /= norm
    return vec


def _mtime() -> float:
    files = [VDIR / "vectors.npy", VDIR / "chunks.jsonl", VDIR / "idf.npy"]
    return max((p.stat().st_mtime for p in files if p.exists()), default=0.0)


def load() -> dict[str, Any] | None:
    global _CACHE, _CACHE_MTIME
    if not (VDIR / "vectors.npy").exists():
        return None
    m = _mtime()
    if _CACHE is not None and m == _CACHE_MTIME:
        return _CACHE
    try:
        import numpy as np
    except ImportError:
        return None
    vectors = np.load(VDIR / "vectors.npy", mmap_mode="r")
    idf = np.load(VDIR / "idf.npy")
    chunks = [json.loads(line) for line in (VDIR / "chunks.jsonl").open(encoding="utf-8") if line.strip()]
    manifest = json.loads((VDIR / "manifest.json").read_text(encoding="utf-8"))
    _CACHE = {"vectors": vectors, "idf": idf, "chunks": chunks, "manifest": manifest}
    _CACHE_MTIME = m
    return _CACHE


def stats() -> dict[str, Any]:
    idx = load()
    if not idx:
        return {}
    mf = idx["manifest"]
    return {
        "vector_sources": mf.get("sources", 0),
        "vector_chunks": mf.get("chunks", 0),
        "vector_built": mf.get("built", ""),
    }


def _queries(q: str) -> list[str]:
    parts = [p for p in re.split(r"[^\w\u4e00-\u9fff]+", q) if len(p) >= 2]
    out: list[str] = []
    for p in sorted(parts, key=len, reverse=True):
        if p not in out:
            out.append(p)
    for n in (4, 3, 2):
        for i in range(len(normalize(q)) - n + 1):
            g = normalize(q)[i:i + n]
            if g not in out:
                out.append(g)
    return out[:40]


def snippet(text: str, q: str, width: int = 240) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    pos = -1
    hit = ""
    for probe in _queries(q):
        pos = t.find(probe)
        if pos >= 0:
            hit = probe
            break
    if pos < 0:
        return t[:width] + ("…" if len(t) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(t), start + width)
    start = max(0, end - width)
    out = t[start:end]
    if hit and hit not in out:
        out = t[pos:pos + width]
    return ("…" if start else "") + out + ("…" if end < len(t) else "")


def search(q: str, k: int = 8, min_score: float = 0.0, per_doc: int = 2) -> list[dict[str, Any]]:
    idx = load()
    if not idx or not normalize(q):
        return []
    import numpy as np

    qv = vectorize(q, idx["idf"])
    if not float(np.linalg.norm(qv)):
        return []
    scores = np.asarray(idx["vectors"] @ qv)
    if scores.size == 0:
        return []
    top = np.argsort(-scores)[: min(len(scores), max(k * 6, 30))]
    hits: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for i in top:
        score = float(scores[int(i)])
        if score < min_score:
            continue
        c = idx["chunks"][int(i)]
        doc = c.get("doc", "")
        if seen.get(doc, 0) >= per_doc:
            continue
        seen[doc] = seen.get(doc, 0) + 1
        hits.append({
            "doc": doc,
            "title": c.get("title", ""),
            "kind": c.get("kind", ""),
            "url": c.get("url", ""),
            "page": c.get("page"),
            "item_ids": c.get("item_ids", []),
            "score": round(score, 4),
            "snippet": snippet(c.get("text", ""), q),
        })
        if len(hits) >= k:
            break
    return hits
