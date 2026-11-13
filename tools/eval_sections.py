"""20 条「章/节级」问句的 top1 / top3 命中率——② 与 ③ 唯一能证明「接进去有用」的那张表。

用法：

    SECTIONS_BOOST=0 ./.venv/Scripts/python.exe -X utf8 tools/eval_sections.py
    SECTIONS_BOOST=1 ./.venv/Scripts/python.exe -X utf8 tools/eval_sections.py

        → 规则腿（rank）里，第一个「落在期望节」的条目排在第几

    ./.venv/Scripts/python.exe -X utf8 tools/eval_sections.py --vector
    ./.venv/Scripts/python.exe -X utf8 tools/eval_sections.py --vector --sections-only

        → ③ 的冒烟：vector_index.search(kind="section") 能不能把正确文档的正确节召回来

    ./.venv/Scripts/python.exe -X utf8 tools/eval_sections.py --json _review_items/_eval_sections_out.json

命中口径（写死在 `_hit_pos` 里，改之前先想清楚）：

  问句 → rank() 前 N 名里，**第一个**「所在节属于 expect_doc、且行号在 expect_sections 里」
  的条目排第几（1 起）。命中 `第X章` 与命中 `第X条` 都算对：章级条目本身就是「这一章有讲」。

它只量「节是否被顶到前面」，不量答案对不对——那是 eval.py 的事。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

CASES = ROOT / "_review_items" / "eval_sections_20.json"

_TITLES: dict[str, str] | None = None


def _titles() -> dict[str, str]:
    """sections/*.json 的 slug → 归一后的文档标题。

    同一份文件在 sources/ 里常有多份副本（选课管理办法的 xuanke-2025 /
    att-3cfd2f5a31 / hbd33955782f 就是一份东西的三次抽取），标题归一后相同。
    判定「命中的是不是期望那份文档」必须认副本，否则检索对、评分错。
    """
    global _TITLES
    if _TITLES is None:
        _TITLES = {}
        for p in (ROOT / "_review_items" / "sections").glob("*.json"):
            if p.name.startswith("_"):
                continue
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            slug = str(d.get("key") or p.stem)
            _TITLES[slug] = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "",
                                   str(d.get("title") or slug).lower())
    return _TITLES


def same_doc(a: str, b: str) -> bool:
    if a == b:
        return True
    ta, tb = _titles().get(a), _titles().get(b)
    return bool(ta and tb and ta == tb)


def load_cases() -> list[dict]:
    data = json.loads(CASES.read_text(encoding="utf-8"))
    return list(data.get("cases") or [])


def _hit_pos(ranked: list, case: dict, sections_index, top: int) -> tuple[int, int]:
    """返回 (节命中位置, 文档命中位置)，都是 1 起，0 = 前 top 名里没有。"""
    want = set(case.get("expect_sections") or [])
    doc = case["expect_doc"]
    sec_pos = 0
    doc_pos = 0
    for i, (it, _sc) in enumerate(ranked[:top], 1):
        secs = sections_index.section_of(it["id"], it)
        if doc_pos == 0 and any(same_doc(s["slug"], doc) for s in secs):
            doc_pos = i
        if sec_pos == 0 and any(same_doc(s["slug"], doc) and s["no"] in want for s in secs):
            sec_pos = i
    return sec_pos, doc_pos


def run_rank(cases: list[dict], top: int) -> dict:
    import app
    import sections_index as si

    rows = []
    for c in cases:
        ranked = app.rank(c["q"])
        sec_pos, doc_pos = _hit_pos(ranked, c, si, max(top, 10))
        top1 = next((it for it, _ in ranked[:1]), None)
        rows.append({
            "q": c["q"],
            "expect_doc": c["expect_doc"],
            "expect_sections": c["expect_sections"],
            "sec_pos": sec_pos,
            "doc_pos": doc_pos,
            "top1": (top1 or {}).get("id", ""),
            "top1_title": ((top1 or {}).get("title") or "")[:40],
        })
    return {"mode": "rank", "top": top, "rows": rows, "idx": si.stats()}


def run_vector(cases: list[dict], only_sections: bool) -> dict:
    import vector_index as vi

    rows = []
    for c in cases:
        kwargs = {"k": 12, "kind": "section"} if only_sections else {"k": 12}
        hits = vi.search(c["q"], **kwargs)
        want = set(c.get("expect_sections") or [])
        doc = c["expect_doc"]
        pos = 0
        for i, h in enumerate(hits, 1):
            if h.get("kind") != "section":
                continue
            sec = h.get("section") or {}
            if same_doc(str(h.get("doc")), doc) and str(sec.get("no")) in want:
                pos = i
                break
        rows.append({
            "q": c["q"], "expect_doc": doc, "expect_sections": c["expect_sections"],
            "sec_pos": pos, "top": [f"{h.get('doc')}#{(h.get('section') or {}).get('no')}" for h in hits[:3]],
        })
    return {"mode": "vector", "rows": rows, "idx": vi.stats()}


def summarize(res: dict, top: int) -> None:
    rows = res["rows"]
    n = len(rows)
    t1 = sum(1 for r in rows if r["sec_pos"] == 1)
    t3 = sum(1 for r in rows if 0 < r["sec_pos"] <= 3)
    tN = sum(1 for r in rows if 0 < r["sec_pos"] <= top)
    d1 = sum(1 for r in rows if r.get("doc_pos") == 1)
    d3 = sum(1 for r in rows if 0 < r.get("doc_pos", 0) <= 3)
    tag = "SECTIONS_BOOST=" + str(os.environ.get("SECTIONS_BOOST", "1"))
    print(f"\n{'问句':<40}{'期望节':<16}{'节位':>4}{'文档位':>6}")
    print("-" * 78)
    for r in rows:
        exp = ",".join(r["expect_sections"])[:14]
        print(f"{r['q'][:38]:<40}{exp:<16}{r['sec_pos'] or '-':>4}{r.get('doc_pos') or '-':>6}")
    print("-" * 78)
    top_tag = f"top{top} {tN / n:.2f}" if top not in (1, 3) else ""
    print(f"{tag}  top1 {t1 / n:.2f}  top3 {t3 / n:.2f}  {top_tag}   "
          f"（文档级 top1 {d1 / n:.2f} / top3 {d3 / n:.2f}）".replace("  ", " "))
    if res.get("idx"):
        idx = res["idx"] or {}
        # rank 模式来自 sections_index.stats()（docs/sections/items_mapped）；
        # vector 模式来自 vector_index.stats()（vector_sources/vector_chunks/vector_sections），键名不同，这里统一取。
        if res.get("mode") == "vector":
            docs = idx.get("vector_sources") or 0
            secs = idx.get("vector_sections") or 0
            chunks = idx.get("vector_chunks") or 0
            print(f"索引：{docs} 份文档 / 节 chunk {secs} 段（向量库共 {chunks} 段）")
        else:
            docs = idx.get("docs") or 0
            secs = idx.get("sections") or 0
            mapped = idx.get("items_mapped")
            mapped_s = f"{mapped} 条条目落在节上" if mapped is not None else "条目映射未统计"
            print(f"索引：{docs} 份 / {secs} 节 / {mapped_s}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=3, help="统计到第几名（默认 3）")
    ap.add_argument("--vector", action="store_true", help="改测向量腿（③ 冒烟）")
    ap.add_argument("--sections-only", action="store_true", help="向量腿只看 kind=section 的命中")
    ap.add_argument("--json", default="", help="把逐条结果写成 JSON（做 before/after 对照用）")
    args = ap.parse_args()

    cases = load_cases()
    if not cases:
        raise SystemExit(f"✗ 没有用例：{CASES}")
    res = run_vector(cases, args.sections_only) if args.vector else run_rank(cases, args.top)
    res["boost"] = os.environ.get("SECTIONS_BOOST", "1")
    summarize(res, args.top)
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"→ {out}")


if __name__ == "__main__":
    main()
