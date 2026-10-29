"""语料错配审计：标题和正文对不上的，挑出来。

判断依据：把标题切成 2-4 字词，看有多少出现在正文前 3000 字里。
命中率过低 = 标题与内容不符（多为搜索抓错页面）。

用法：
    python tools/audit_sources.py                 # 只报告
    python tools/audit_sources.py --quarantine    # 移到 sources/_quarantine 并从索引移除
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path("D:/DSH/智能体节")
SRC = ROOT / "sources"
Q = SRC / "_quarantine"

INDEXES = {
    "extra": ("extra-index.json", "extra"),
    # local 多为表格/清单，标题词与正文重合度天然低，不参与错配判定
    "cdp": ("cdp-index.json", "cdp"),
    "crawl": ("crawl-index.json", "crawl"),
    "huibian": ("huibian-index.json", "huibian"),
}

STOP = {"中国传媒大学", "管理办法", "管理规定", "实施细则", "办法", "规定", "细则",
        "关于", "工作", "通知", "试行", "修订", "的", "和", "及"}


def terms(title: str) -> list[str]:
    t = re.sub(r"[（(].*?[）)]", "", title)
    t = re.sub(r"[^\u4e00-\u9fff]+", " ", t)
    out = []
    for chunk in t.split():
        for n in (4, 3, 2):
            for i in range(len(chunk) - n + 1):
                w = chunk[i:i + n]
                if w not in STOP and len(w) >= 2:
                    out.append(w)
    # 去重保序
    return list(dict.fromkeys(out))[:12]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarantine", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.34)
    args = ap.parse_args()

    bad: list[tuple[str, str, str, float, str]] = []
    for key, (idx_name, folder) in INDEXES.items():
        idx_file = SRC / idx_name
        if not idx_file.exists():
            continue
        idx = json.loads(idx_file.read_text(encoding="utf-8"))
        for slug, meta in idx.items():
            f = SRC / folder / f"{slug}.txt" if folder else SRC / f"{slug}.txt"
            if not f.exists():
                continue
            body = f.read_text(encoding="utf-8")[:3000]
            ts = terms(meta.get("title", ""))
            if not ts:
                continue
            hit = sum(1 for t in ts if t in body)
            rate = hit / len(ts)
            if rate < args.threshold:
                bad.append((key, slug, meta.get("title", ""), rate, str(f)))

    print(f"疑似错配 {len(bad)} 条\n")
    for key, slug, title, rate, f in sorted(bad, key=lambda x: x[3]):
        print(f"  [{key}] {rate:.0%}  {title[:44]}")

    if not args.quarantine:
        return

    Q.mkdir(parents=True, exist_ok=True)
    moved = 0
    by_index: dict[str, set[str]] = {}
    for key, slug, title, rate, f in bad:
        src = Path(f)
        if src.exists():
            shutil.move(str(src), str(Q / src.name))
            moved += 1
        by_index.setdefault(key, set()).add(slug)

    for key, slugs in by_index.items():
        idx_name, _ = INDEXES[key]
        idx_file = SRC / idx_name
        idx = json.loads(idx_file.read_text(encoding="utf-8"))
        for s in slugs:
            idx.pop(s, None)
        idx_file.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n已隔离 {moved} 个文件到 sources/_quarantine，并从 {len(by_index)} 个索引移除")


if __name__ == "__main__":
    main()
