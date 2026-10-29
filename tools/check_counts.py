"""核对口径：items.json、API、presets、contacts、语料与向量库存量必须一致。

用法：python tools/check_counts.py    失败时退出码 1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402

OK_STATUS = {"verified", "source-thin"}


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    fails: list[str] = []
    items = load("items.json")["items"]
    ids = [i["id"] for i in items]
    status = {i.get("status") for i in items}

    if len(ids) != len(set(ids)):
        fails.append("items.json 存在重复 id")

    if not status <= OK_STATUS:
        fails.append(f"items.json 出现未知 status: {sorted(status - OK_STATUS)}")

    verified = sum(1 for i in items if i.get("status") == "verified")
    thin = sum(1 for i in items if i.get("status") == "source-thin")
    if verified + thin != len(items):
        fails.append(f"条目状态未覆盖全部：{verified}+{thin} != {len(items)}")

    h = app.health()
    if h["items"] != len(items):
        fails.append(f"/api/health items={h['items']} != items.json {len(items)}")
    if h["verified"] != verified:
        fails.append(f"/api/health verified={h['verified']} != {verified}")
    if h["source_thin"] != thin:
        fails.append(f"/api/health source_thin={h['source_thin']} != {thin}")

    pz = load("presets.json")
    ptotal = sum(len(g.get("items", [])) for g in pz.get("groups", []))
    if pz.get("total") != ptotal:
        fails.append(f"presets.total={pz.get('total')} != 分组求和 {ptotal}")
    coverage = {k: v for k, v in (pz.get("coverage") or {}).items() if k}
    pids = set(coverage)
    unknown = sorted(x for x in pids if x not in set(ids))
    if unknown:
        fails.append(f"presets 引用了不存在的事项: {unknown[:5]}")
    hand_ids = {i["id"] for i in items if not i.get("auto")}
    missing = sorted(hand_ids - pids)
    if missing:
        fails.append(f"预置问法未覆盖人工条目: {missing[:8]}")
    if coverage:
        ncov = sum(len(v) for v in coverage.values())
        if ncov != ptotal:
            fails.append(f"presets.coverage 问法数 {ncov} != total {ptotal}")

    ct = load("contacts.json")
    if ct.get("total") != len(ct.get("items", [])):
        fails.append(f"contacts.total={ct.get('total')} != items {len(ct.get('items', []))}")

    corpus = json.loads((ROOT / "sources" / "corpus-index.json").read_text(encoding="utf-8"))
    if h.get("sources") != len(corpus):
        fails.append(f"/api/health sources={h.get('sources')} != corpus-index {len(corpus)}")

    manifest_path = ROOT / "sources" / "vector" / "manifest.json"
    if not manifest_path.exists():
        fails.append("缺少 sources/vector/manifest.json（先跑 tools/build_vector.py）")
    else:
        mf = json.loads(manifest_path.read_text(encoding="utf-8"))
        chunks_path = ROOT / "sources" / "vector" / "chunks.jsonl"
        vectors_path = ROOT / "sources" / "vector" / "vectors.npy"
        if chunks_path.exists():
            n = sum(1 for line in chunks_path.open(encoding="utf-8") if line.strip())
            if mf.get("chunks") != n:
                fails.append(f"manifest.chunks={mf.get('chunks')} != chunks.jsonl {n}")
            if vectors_path.exists():
                import numpy as np

                rows = np.load(vectors_path, mmap_mode="r").shape[0]
                if rows != n:
                    fails.append(f"vectors.npy 行数 {rows} != chunks.jsonl {n}")
            else:
                fails.append("缺少 sources/vector/vectors.npy")
        else:
            fails.append("缺少 sources/vector/chunks.jsonl")
        if h.get("vector_chunks") != mf.get("chunks"):
            fails.append("health vector_chunks 与 manifest 不一致")

    print("口径核对")
    print(f"  事项        {len(items)}（verified {verified} / source-thin {thin}）")
    print(f"  事实        {h.get('facts')}")
    cov = f"{len(pids)}/{len(hand_ids)} 个人工条目" if pids else "未记录（需重新生成）"
    print(f"  预置问法    {pz.get('total')} 条 / 覆盖 {cov}")
    print(f"  联系方式    {ct.get('total')} 条")
    print(f"  语料        {h.get('sources')} 份（official {h.get('sources_official')}）")
    if manifest_path.exists():
        print(f"  向量库      {h.get('vector_sources')} 份 / {h.get('vector_chunks')} 段")

    if fails:
        print("\n✗ 口径不一致：")
        for f in fails:
            print(f"  - {f}")
        sys.exit(1)
    print("\n✓ 口径一致")


if __name__ == "__main__":
    main()
