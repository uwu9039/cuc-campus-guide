"""给「章节索引」子代理看：某份文档（slug / doc key）对应哪些条目、引文是什么。

只读。输出很短（每条目一行），避免子代理为了找条目去读 69MB 的 items.json。

用法：
  ./.venv/Scripts/python.exe -X utf8 -u tools/doc_items.py --slug aa31caae
  ./.venv/Scripts/python.exe -X utf8 -u tools/doc_items.py --slug aa31caae --full
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCLIST = ROOT / "_review_items" / "toc" / "_doclist.json"


def load_doc(slug: str) -> dict | None:
    d = json.loads(DOCLIST.read_text(encoding="utf-8"))
    for doc in d.get("docs") or []:
        if doc.get("key") == slug:
            return doc
    return None


def load_items(ids: list[str]) -> dict[str, dict]:
    d = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    want = set(ids)
    return {it["id"]: it for it in d.get("items") or [] if it.get("id") in want}


def quotes_of(it: dict) -> list[str]:
    ev = (it.get("evidence") or {}).get("answer") or {}
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


def main() -> None:
    args = sys.argv[1:]
    full = "--full" in args
    slug = ""
    for i, a in enumerate(args):
        if a == "--slug" and i + 1 < len(args):
            slug = args[i + 1]
        elif a.startswith("--slug="):
            slug = a.split("=", 1)[1]
    if not slug:
        print("用法: --slug <key>", file=sys.stderr)
        raise SystemExit(2)

    doc = load_doc(slug)
    if not doc:
        print(f"{slug}: _doclist.json 里没有这个 key")
        raise SystemExit(1)

    txt = ROOT / str(doc.get("text") or "")
    nchar = len(txt.read_text(encoding="utf-8", errors="ignore")) if txt.is_file() else 0
    ids = doc.get("ids") or []
    print(f"slug={slug}  字符={nchar}  path={doc.get('text')}  条目={len(ids)}")
    print(f"category={doc.get('category')}  depts={doc.get('depts')}  audience={doc.get('audience')}")

    items = load_items(ids)
    for iid in ids:
        it = items.get(iid) or {}
        title = str(it.get("title") or "")
        print(f"- {iid} | {title}")
        for q in quotes_of(it)[: (99 if full else 3)]:
            q1 = q if full else (q if len(q) <= 80 else q[:80] + "…")
            print(f"    quote: {q1}")
        if not quotes_of(it):
            print("    quote: （无引文，只能看标题/正文判断落点）")


if __name__ == "__main__":
    main()
