"""金标准要点的「证据可得性」诊断：每条要点，候选池里到底有没有对应条款。

用来区分两种缺口：
  · 证据在场、答案没写 → 合成/结构问题（改提示词、改结构）
  · 证据根本不在池里   → 取证问题（改检索）
用法：./.venv/Scripts/python.exe -X utf8 -u tools/_probe_golden_evidence.py
只读。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app  # noqa: E402

GOLDEN = ROOT / "_review_items" / "golden_20261111.json"


def kw_variants(kw: list[str]) -> list[str]:
    out = []
    for k in kw:
        k = k.replace(" ", "")
        out.append(k)
    return out


def main() -> None:
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
    tot = hit = 0
    for case in cases:
        q = case["q"]
        status: dict = {}
        premises, queries = app._synth_plan(q, status)
        cands = app._synth_candidates(queries or premises, premises, question=q) if premises else []
        # 候选池全文（引文 + 标题），用来判断「池里有没有这条」
        hay = " ".join((c.get("quote") or "") + (c.get("doc") or "") for c in cands)
        hay = hay.replace(" ", "")
        print("=" * 76)
        print(f"{q}  候选 {len(cands)} 条")
        for pt in case["points"]:
            kws = kw_variants(pt.get("kw") or [])
            ok = all(k in hay for k in kws) if kws else False
            # 单关键词时放宽：要求关键词出现且上下文 40 字内提到事名
            tot += 1
            hit += ok
            print(f"  {'池里有' if ok else '池里无'} | {pt['p'][:40]:42} kw={kws}")
    print(f"\n要点证据可得率 {hit}/{tot} = {round(100 * hit / tot)}%（这是上限：答案再好也不会超过它）")


if __name__ == "__main__":
    main()
