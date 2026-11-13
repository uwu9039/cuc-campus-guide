"""章节索引体检：给「夜间批量标注」的编排 agent 每批跑一次。

只读、不改文件。输出尽量短（每份一行 + 失败明细），避免撑爆编排 agent 的上下文。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/sections_check.py            # 全目录
  ./.venv/Scripts/python.exe -X utf8 -u tools/sections_check.py --quiet    # 只打失败
  ./.venv/Scripts/python.exe -X utf8 -u tools/sections_check.py --slug 1de56d3c
  ./.venv/Scripts/python.exe -X utf8 -u tools/sections_check.py --json

查什么（与验收口径一致）：
  1. schema：顶层恰 6 项（key/title/truncated/sections/items/notes），key == 文件名
  2. 行号：1<=a<=b<=len(lines)，父/子区间只能是真嵌套，不许部分交叠
  3. author：heading 必须能在本节行区间里逐字找到（忽略空白）
  4. 落点：条目的引文要能在其所在节的行区间里命中；命中却没列 = 漏列
  5. 覆盖：非空行若整份没被任何节覆盖，计数报出（不一定是错，空行/标题行常见）
  6. truncated：与 sources/*index*.json 的 text_from 比对（仅对 index 里有的 slug）

退出码：0 全过；1 有失败。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SECDIR = ROOT / "_review_items" / "sections"
LEGACY = SECDIR / "_legacy_ok.json"
KEYS = {"key", "title", "truncated", "sections", "items", "notes"}


def load_index_meta() -> dict[str, dict]:
    meta: dict[str, dict] = {}
    for p in (ROOT / "sources").glob("*index*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, dict):
                    meta.setdefault(k, v)
    return meta


def load_texts() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in (ROOT / "sources").rglob("*.txt"):
        out.setdefault(p.stem, p)
    return out


def quotes(item: dict[str, Any]) -> list[str]:
    ev = (item.get("evidence") or {}).get("answer") or {}
    out: list[str] = []
    if isinstance(ev, dict):
        if ev.get("quote"):
            out.append(str(ev["quote"]))
        srcs = ev.get("sources") or []
        if isinstance(srcs, dict):
            srcs = [srcs]
        for s in srcs:
            if isinstance(s, dict) and s.get("quote"):
                out.append(str(s["quote"]))
    return out


def check_one(path: Path, items: dict[str, dict], texts: dict[str, Path], meta: dict[str, dict],
              legacy: set[str]) -> dict:
    slug = path.stem
    problems: list[str] = []
    d = json.loads(path.read_text(encoding="utf-8"))
    if set(d.keys()) != KEYS:
        problems.append(f"schema 键不对：{sorted(set(d.keys()) ^ KEYS)}")
    if d.get("key") != slug:
        problems.append(f"key({d.get('key')!r}) ≠ 文件名")
    secs = d.get("sections") or []
    if not secs:
        problems.append("sections 为空")
    tp = texts.get(slug)
    lines = tp.read_text(encoding="utf-8", errors="ignore").split("\n") if tp else []
    n = len(lines)
    auth = 0
    for s in secs:
        a, b = (s.get("lines") or [0, 0])[:2]
        if not (1 <= a <= b <= n):
            problems.append(f"{s.get('no')} 行号越界 {a}-{b}/{n}")
            continue
        if s.get("heading_kind") == "author":
            auth += 1
            hay = re.sub(r"\s+", "", "\n".join(lines[a - 1:b]))
            if re.sub(r"\s+", "", str(s.get("heading") or "")) not in hay:
                problems.append(f"{s.get('no')} 标 author 但标题不在本节原文")
        if not str(s.get("heading") or "").strip():
            problems.append(f"{s.get('no')} 缺 heading")
    # 真嵌套校验
    for i, s in enumerate(secs):
        a, b = (s.get("lines") or [0, 0])[:2]
        for t in secs[i + 1:]:
            c, e = (t.get("lines") or [0, 0])[:2]
            if e < a or c > b:
                continue
            if (a <= c and e <= b) or (c <= a and b <= e):
                continue
            problems.append(f"{s.get('no')}{s.get('lines')} 与 {t.get('no')}{t.get('lines')} 部分交叠")
    # 落点：引文在本文里找不到 = 跨文件引用（不算错）；在本文里但不在所标节 = 错
    land = 0
    wholetxt = re.sub(r"\s+", "", "\n".join(lines)) if lines else ""
    crossfile: list[str] = []
    for s in secs:
        a, b = (s.get("lines") or [0, 0])[:2]
        blob = re.sub(r"\s+", "", "\n".join(lines[a - 1:b])) if lines else ""
        if s.get("items"):
            land += 1
        for iid in s.get("items") or []:
            qs = [re.sub(r"\s+", "", q)[:26] for q in quotes(items.get(iid) or {})]
            if not qs:
                continue
            if not any(q in wholetxt for q in qs):
                crossfile.append(iid)
                continue
            if not any(q in blob for q in qs):
                problems.append(f"{iid} 的引文在本文里但不在 {s.get('no')}{s.get('lines')}")
    union = {i for s in secs for i in (s.get("items") or [])}
    doc_items = set(d.get("items") or [])
    missing_in_secs = doc_items - union
    # 文档级有、节内没列的：只有当它的引文确实落在本文某节时才算漏列
    for iid in sorted(missing_in_secs):
        qs = [re.sub(r"\s+", "", q)[:26] for q in quotes(items.get(iid) or {})]
        if qs and any(q in wholetxt for q in qs):
            problems.append(f"{iid} 在文档级 items 里但没有落进任何节")
        else:
            crossfile.append(iid)
    # 覆盖（非空行）
    covered = set()
    for s in secs:
        a, b = (s.get("lines") or [0, 0])[:2]
        covered.update(range(a, b + 1))
    gap = [i for i in range(1, n + 1) if i not in covered and lines[i - 1].strip()]
    # truncated 与 index 对照
    warns: list[str] = []
    if slug in legacy:
        keep = []
        for p in problems:
            (warns if "的引文在本文里但不在" in p else keep).append(p)
        problems = keep
    m = meta.get(slug) or {}
    tf = str(m.get("text_from") or "")
    if tf and tf != "pypdf" and not d.get("truncated"):
        problems.append(f"index 记 text_from={tf}，但 truncated=false")
    return {"slug": slug, "secs": len(secs), "author": auth,
            "landing": land, "gap": len(gap), "problems": problems[:6],
            "warns": warns[:4], "nprob": len(problems)}


def main() -> None:
    args = sys.argv[1:]
    quiet = "--quiet" in args
    as_json = "--json" in args
    only: list[str] = []
    for i, a in enumerate(args):
        if a == "--slug" and i + 1 < len(args):
            only.append(args[i + 1])

    items = {it["id"]: it for it in json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]}
    texts = load_texts()
    meta = load_index_meta()

    paths = sorted(p for p in SECDIR.glob("*.json") if not p.name.startswith("_"))
    if only:
        paths = [p for p in paths if p.stem in only]
    legacy: set[str] = set()
    if LEGACY.exists():
        legacy = {str(x) for x in (json.loads(LEGACY.read_text(encoding="utf-8")).get("slugs") or [])}
    results = [check_one(p, items, texts, meta, legacy) for p in paths]

    failed = [r for r in results if r["nprob"]]
    if as_json:
        print(json.dumps({"total": len(results), "failed": len(failed), "rows": results}, ensure_ascii=False, indent=1))
    else:
        if not quiet:
            for r in results:
                flag = "FAIL" if r["nprob"] else "ok"
                print(f"{r['slug']:28s} 节{r['secs']:>3} 作者{r['author']:>3} 落点{r['landing']:>3} "
                      f"空隙{r['gap']:>2} {flag}")
        for r in failed:
            print(f"[FAIL] {r['slug']}: {r['problems']}")
        for r in results:
            if r.get("warns"):
                print(f"[warn] {r['slug']}: {r['warns']}")
        total_secs = sum(r["secs"] for r in results)
        print(f"\n{len(results)} 份 / {total_secs} 节 | 失败 {len(failed)} 份")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
