"""把三个来源目录合并成一份内部语料台账 sources/corpus-index.json。

以后加条目时先看这份台账：哪些页面已入库、哪些还没被任何条目引用。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"

def load(name):
    f = SRC / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

corpus = {}
def add(slug, meta, kind):
    corpus[slug] = {
        "slug": slug,
        "kind": kind,
        "title": meta.get("title", ""),
        "account": meta.get("account", ""),
        "date": meta.get("date", ""),
        "url": meta.get("url", ""),
        "chars": meta.get("chars", 0),
        "fetched_at": meta.get("fetched_at", ""),
        "official": meta.get("official", True),
    }

for s, m in load("index.json").items():
    add(s, m, "官网·精读")
for s, m in load("crawl-index.json").items():
    add(s, m, "官网·采集")
for s, m in load("wechat-index.json").items():
    add(s, m, "公众号")

items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))["items"]
used = set()
for it in items:
    for ev in (it.get("evidence") or {}).values():
        rows = ev.get("sources") if isinstance(ev, dict) and "sources" in ev else [ev]
        for r in rows or []:
            if isinstance(r, dict) and r.get("src"):
                used.add(r["src"])

for slug, row in corpus.items():
    row["used_by_items"] = sorted(i["id"] for i in items
                                  if slug in {r.get("src") for ev in (i.get("evidence") or {}).values()
                                              for r in ((ev.get("sources") if isinstance(ev, dict) and "sources" in ev else [ev]) or [])})

(SRC / "corpus-index.json").write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")

by_kind = {}
for row in corpus.values():
    by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
print(f"语料 {len(corpus)} 条：" + "，".join(f"{k} {v}" for k, v in by_kind.items()))
print(f"已被条目引用 {len(used)} 条，未引用 {len(corpus) - len(used)} 条")
unused = [r for r in corpus.values() if not r["used_by_items"] and r["chars"] > 900]
unused.sort(key=lambda r: -r["chars"])
print("\n高价值但还没做成条目的页面（前 12）：")
for r in unused[:12]:
    print(f"  {r['chars']:>5} 字  [{r['kind']}] {r['title'][:38]}  {r['slug']}")
