"""把随包的 sources-archive.tar.gz 解到 sources/（云端部署第一步，幂等）。

用法：
    python tools/extract_sources.py                # 只补缺，已存在的同名同大小文件跳过
    python tools/extract_sources.py --rebuild      # 全部重抽，并删掉归档里没有的正文残留
    python tools/extract_sources.py --verify       # 只核对不抽

安全：不解 zip/rar，逐成员校验归一化路径（挡路径穿越与绝对路径），单个坏成员跳过不中断。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
ARCH = SRC / "sources-archive.tar.gz"
ROOT_ARCH = ROOT / "sources-archive.tar.gz"
BIN_ARCH = ROOT / "sources-binaries.tar.gz"
STAMP = SRC / ".extract-stamp"
DANGER_SUFFIX = {".zip", ".rar", ".7z"}


def _archive() -> Path | None:
    for p in (ARCH, ROOT_ARCH):
        if p.exists():
            return p
    return None


def _safe_member(name: str) -> str | None:
    """归档内路径统一成 sources/ 下的相对路径，越界的返回 None。"""
    parts = [seg for seg in name.replace("\\", "/").split("/") if seg not in ("", ".")]
    if not parts or ".." in parts or name.startswith(("/", "\\")) or ":" in parts[0]:
        return None
    if parts[0] == "sources":
        parts = parts[1:]
    if not parts:
        return None
    return "/".join(parts)


def _skip_existing(tf: tarfile.TarFile) -> int:
    skipped = 0
    for m in tf.getmembers():
        if not m.isfile():
            continue
        rel = _safe_member(m.name)
        if rel is None:
            print(f"跳过越界成员：{m.name}")
            continue
        if m.name.lower().endswith(tuple(DANGER_SUFFIX)):
            print(f"跳过不解压：{m.name}（归档已排除压缩包）")
            continue
        dst = SRC / rel
        if dst.exists() and dst.stat().st_size == m.size:
            skipped += 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        src = tf.extractfile(m)
        if src is None:
            continue
        dst.write_bytes(src.read())
    return skipped


def _drop_stale(tf: tarfile.TarFile) -> int:
    """--rebuild 时清掉不在归档里的旧正文，免得改完包没换干净。"""
    want = set()
    for m in tf.getmembers():
        if m.isfile():
            rel = _safe_member(m.name)
            if rel:
                want.add(rel.lower())
    removed = 0
    for p in list(SRC.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(SRC).as_posix().lower()
        if rel in ("sources-archive.tar.gz", "sources-binaries.tar.gz", ".extract-stamp"):
            continue
        if "attachments/files/" in rel or "local/_files/" in rel or rel.startswith("vector/"):
            continue
        if rel not in want:
            p.unlink()
            removed += 1
    return removed


def extract(rebuild: bool = False) -> int:
    arch = _archive()
    if arch is None:
        print("没找到 sources-archive.tar.gz，跳过解压")
        return 0
    stamp = hashlib.sha256(arch.read_bytes()).hexdigest()[:16]
    if STAMP.exists() and STAMP.read_text(encoding="utf-8").strip() == stamp and not rebuild:
        print(f"已解过同一个包（{stamp}），跳过；要重抽用 --rebuild")
        return 0
    with tarfile.open(arch, "r:*") as tf:
        skipped = _skip_existing(tf)
        stale = _drop_stale(tf) if rebuild else 0
    STAMP.write_text(stamp, encoding="utf-8")
    print(f"解压完成：{arch.name}，跳过已存在 {skipped} 份" + (f"，清掉残留 {stale} 份" if rebuild else ""))
    return 0


def verify() -> int:
    arch = _archive()
    if arch is None:
        print("缺 sources-archive.tar.gz")
        return 1
    with tarfile.open(arch, "r:*") as tf:
        members = [(m.name, m.size) for m in tf.getmembers() if m.isfile()]
    bad = [name for name, _ in members if _safe_member(name) is None]
    missing = [(SRC / _safe_member(name)).relative_to(SRC).as_posix()
               for name, size in members
               if _safe_member(name) and not (SRC / _safe_member(name)).exists()]
    mismatch = [(SRC / _safe_member(name)).relative_to(SRC).as_posix()
                for name, size in members
                if _safe_member(name) and (SRC / _safe_member(name)).exists()
                and (SRC / _safe_member(name)).stat().st_size != size]
    print(f"归档 {len(members)} 份成员，sources/ 现有 {sum(1 for p in SRC.rglob('*') if p.is_file())} 份文件")
    if bad:
        print(f"✗ 越界成员 {len(bad)}：{bad[:3]}")
    if missing:
        print(f"✗ 缺 {len(missing)} 份，例如 {missing[:3]}")
    if mismatch:
        print(f"✗ 大小不符 {len(mismatch)} 份，例如 {mismatch[:3]}")
    if not (bad or missing or mismatch):
        print("✅ 归档与磁盘逐份对上")
        return 0
    return 1


def stats() -> int:
    """把 sources/ 现状落成一份 JSON 统计，供部署核对与后续任务规划。"""
    files = [p for p in SRC.rglob("*") if p.is_file() and "_quarantine" not in p.parts]
    by_bucket: dict[str, dict[str, float]] = {}
    for p in files:
        rel = p.relative_to(SRC)
        bucket = rel.parts[0] if len(rel.parts) > 1 else "(根)"
        d = by_bucket.setdefault(bucket, {"files": 0, "bytes": 0})
        d["files"] += 1
        d["bytes"] += p.stat().st_size
    out = {
        "files": len(files),
        "bytes": sum(d["bytes"] for d in by_bucket.values()),
        "archive": (_archive().name if _archive() else None),
        "stamp": STAMP.read_text(encoding="utf-8").strip() if STAMP.exists() else None,
        "by_bucket": dict(sorted(by_bucket.items(), key=lambda kv: -kv[1]["bytes"])),
    }
    path = ROOT / "sources_stats.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path.name}：{out['files']} 份 {out['bytes'] / 1048576:.1f} MB，"
          f"目录 {len(by_bucket)} 个 → {path}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="全部重抽并清掉归档外的残留")
    ap.add_argument("--verify", action="store_true", help="只核对不抽")
    ap.add_argument("--stats", action="store_true", help="把 sources/ 统计写成 sources_stats.json")
    a = ap.parse_args()
    if a.stats:
        sys.exit(stats())
    if a.verify:
        sys.exit(verify())
    sys.exit(extract(a.rebuild))
