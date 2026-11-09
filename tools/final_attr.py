"""最终世界四件候选的边际算分：全离线，只读 _review_items/balance_rows.jsonl。

用法：./.venv/Scripts/python.exe tools/final_attr.py
报三块：
  1. 尺子的分辨率——F0a 与 F0b 同码两跑，逐题比 对/错/拒 与条目，效用差就是噪声带。
  2. 每件候选在最终世界里的边际（对/错答/拒答/效用/每题中位时长），对照 F0a 与 F0b 两个数。
  3. 复核跳过的估算跳过率（判分 ≥ 阈值的那部分题），和 50~54 那档有没有被带下水。
"""
from __future__ import annotations

import io
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = ROOT / "_review_items" / "balance_rows.jsonl"
BASE = ("F0a", "F0b")
CANDS = [("F1", "同分定序 TIE_BREAK"), ("F2", "复核跳过 85"),
         ("F3", "复核跳过 95"), ("F4", "候选行补元信息 POOL_META")]


def load() -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for line in io.open(ROWS, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        out.setdefault(r["cfg"], {})[r["q"]] = r
    return out


def tally(rows: dict[str, dict]) -> dict:
    hits = sum(1 for r in rows.values() if r.get("hit"))
    wrong = sum(1 for r in rows.values() if r.get("matched") and not r.get("hit"))
    ref = len(rows) - hits - wrong
    ms = [r["ms"] for r in rows.values() if r.get("ms")]
    return {"n": len(rows), "hits": hits, "wrong": wrong, "ref": ref,
            "util": hits - 3 * wrong, "med_s": round(statistics.median(ms) / 1000, 1) if ms else 0}


def main() -> int:
    data = load()
    missing = [c for c in (*BASE, *(c for c, _ in CANDS)) if c not in data]
    if missing:
        print("还没跑到的档：", missing)
    for cfg in BASE:
        if cfg in data:
            print(f"[{cfg}] {tally(data[cfg])}")
    if BASE[0] in data and BASE[1] in data:
        a, b = data[BASE[0]], data[BASE[1]]
        common = sorted(set(a) & set(b))
        flip = [q for q in common
                if (a[q].get("hit"), a[q].get("matched")) != (b[q].get("hit"), b[q].get("matched"))]
        item_diff = [q for q in common if a[q].get("got") != b[q].get("got") and a[q].get("matched")
                     and b[q].get("matched")]
        ta, tb = tally(a), tally(b)
        print(f"分辨率：同码两跑 档位翻转 {len(flip)}/{len(common)} 题，"
              f"条目不同 {len(item_diff)} 题，效用差 {abs(ta['util'] - tb['util'])}")
        band = abs(ta["util"] - tb["util"])
        print("翻转题：", [(q[:14], (a[q].get("hit"), a[q].get("matched")),
                          (b[q].get("hit"), b[q].get("matched"))) for q in flip][:8])
    else:
        band = 0

    for cfg, label in CANDS:
        if cfg not in data:
            continue
        rows = data[cfg]
        t = tally(rows)
        common = set(rows) & set(data[BASE[0]])
        marg = [t["util"] - tally({q: data[b][q] for q in common}).__getitem__("util")
                for b in BASE if all(q in data[b] for q in common)]
        jump = sum(1 for r in rows.values()
                   if max(r.get("rule_score") or 0, r.get("model_score") or 0) >= 85)
        near = [q for q, r in rows.items()
                if 50 <= (r.get("rule_score") or 0) < 55 and r.get("matched")]
        print(f"[{cfg} {label}] 对 {t['hits']} 错 {t['wrong']} 拒 {t['ref']} "
              f"效用 {t['util']}（对 − 3×错） 每题中位 {t['med_s']}s | "
              f"边际 vs F0a/F0b = {marg} | 判分≥85 占比 {jump}/{t['n']}"
              f" | 50~54 档答上了 {len(near)} 题")
    print(f"判据：边际要大于噪声带 {band} 才算数；复核跳过还要 中位时长降≥2s 且错答不增超过1。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
