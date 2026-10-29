"""证据校验：items.json 里每条事实，都必须能在 sources/ 的官方正文里找到原句。

规则
  1. 需要证据的字段：fee / location / hours / duration / window（非空时）、
     materials[i].name、steps[i].what、pitfalls[i]
  2. 每个字段在 evidence 里必须有 quote，且 quote 是 sources/<src>.txt 的子串
  3. source-thin 的条目允许 steps/materials 为空，但写了就必须有证据

用法：python tools/check_quotes.py    失败时退出码 1
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"


def squash(s: str) -> str:
    """去掉所有空白，避免换行/缩进导致误判。"""
    return re.sub(r"\s+", "", s or "")


def ev_list(ev: dict) -> list[dict]:
    """一条事实可以挂多个官方来源（多种说法）。"""
    if not ev:
        return []
    if "sources" in ev:
        return ev["sources"]
    return [ev]


def needed_fields(item: dict) -> list[str]:
    keys = [k for k in ("fee", "location", "hours", "duration", "window") if item.get(k)]
    if item.get("answer"):
        keys.append("answer")
    keys += [f"materials.{i}" for i in range(len(item.get("materials") or []))]
    keys += [f"steps.{i}" for i in range(len(item.get("steps") or []))]
    keys += [f"pitfalls.{i}" for i in range(len(item.get("pitfalls") or []))]
    return keys


def main() -> None:
    data = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    index = json.loads((SRC / "index.json").read_text(encoding="utf-8"))
    texts = {slug: squash((SRC / f"{slug}.txt").read_text(encoding="utf-8")) for slug in index}
    for sub in ("wechat", "crawl", "cdp", "pdf", "chsi", "moe", "national", "extra", "huibian", "local", "wendao-extra", "wendao-text"):
        for f in (SRC / sub).glob("*.txt"):
            texts[f.stem] = squash(f.read_text(encoding="utf-8"))

    fails: list[str] = []
    total = ok = 0

    for item in data["items"]:
        evidence = item.get("evidence") or {}
        for field in needed_fields(item):
            total += 1
            ev = evidence.get(field)
            if not ev:
                fails.append(f"{item['id']:<16} {field:<12} 缺证据")
                continue
            srcs = ev_list(ev)
            if not srcs:
                fails.append(f"{item['id']:<16} {field:<12} 缺证据")
                continue
            bad = False
            for one in srcs:
                src = one.get("src", "")
                quote = squash(one.get("quote", ""))
                if src not in texts:
                    fails.append(f"{item['id']:<16} {field:<12} 来源不存在: {src}")
                    bad = True
                    continue
                if not quote:
                    fails.append(f"{item['id']:<16} {field:<12} quote 为空")
                    bad = True
                    continue
                if quote not in texts[src]:
                    fails.append(f"{item['id']:<16} {field:<12} 原文找不到：{one['quote'][:40]}")
                    bad = True
            if not bad:
                ok += 1

    print(f"事实字段 {total} 个，可追溯到原文 {ok} 个，失败 {len(fails)} 个")
    if fails:
        print("\n失败清单：")
        for f in fails:
            print("  ✗", f)
        sys.exit(1)

    kinds = {}
    for item in data["items"]:
        kinds[item.get("status", "?")] = kinds.get(item.get("status", "?"), 0) + 1
    print("条目状态分布：", "，".join(f"{k} {v} 条" for k, v in sorted(kinds.items())))
    print("✅ 全部事实均可追溯到 sources/ 中的官方正文")


if __name__ == "__main__":
    main()
