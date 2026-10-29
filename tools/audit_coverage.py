"""审计：每份已入库文档是否被至少一个条目引用为证据。

输出 sources/doc-coverage.json + 控制台摘要。
"""
import json
import os
import re
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sources")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def index_files():
    """收集所有索引，返回 {src_key: {title, collection, url}}。"""
    out = {}
    for p in glob.glob(os.path.join(SRC, "*-index.json")) + [os.path.join(SRC, "index.json")]:
        col = os.path.basename(p).replace("-index.json", "").replace(".json", "")
        if col == "index":
            col = "corpus"
        try:
            d = load(p)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            out.setdefault(str(k), {
                "title": v.get("title") or "",
                "collection": col,
                "url": v.get("url") or "",
                "file": v.get("file") or "",
                "chars": v.get("chars") or 0,
            })
    # wendao 下载台账（含索引未收录的）
    wp = os.path.join(SRC, "wendao", "index.json")
    if os.path.exists(wp):
        d = load(wp)
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, dict) and str(k) not in out:
                    out[str(k)] = {
                        "title": v.get("title") or "",
                        "collection": "wendao-file",
                        "url": v.get("url") or "",
                        "file": v.get("path") or v.get("file") or "",
                        "chars": v.get("chars") or 0,
                    }
    return out


def item_srcs(items):
    used = {}
    def walk(ev, iid):
        if isinstance(ev, dict):
            s = ev.get("src")
            if s:
                used.setdefault(str(s), set()).add(iid)
            for v in ev.values():
                walk(v, iid)
        elif isinstance(ev, list):
            for v in ev:
                walk(v, iid)
    for it in items:
        walk(it.get("evidence"), it.get("id"))
        for s in it.get("sources") or []:
            if isinstance(s, str):
                used.setdefault(s, set()).add(it.get("id"))
    return used


def main():
    items = load(os.path.join(ROOT, "items.json"))["items"]
    idx = index_files()
    used = item_srcs(items)

    # src 可能只写前缀（如 41123054），补全为索引键
    resolved = {}
    for s in used:
        hit = s if s in idx else None
        if not hit:
            cands = [k for k in idx if k.startswith(s) or s.startswith(k)]
            if cands:
                hit = sorted(cands, key=len, reverse=True)[0]
        resolved[s] = hit or s

    by_col = {}
    missing = []
    for k, meta in idx.items():
        ref = used.get(k)
        if not ref:
            # 前缀反查
            for s, h in resolved.items():
                if h == k:
                    ref = used.get(s)
                    break
        col = meta["collection"]
        rec = by_col.setdefault(col, {"total": 0, "used": 0, "unused": 0})
        rec["total"] += 1
        if ref:
            rec["used"] += 1
        else:
            rec["unused"] += 1
            missing.append({"key": k, **meta})

    report = {
        "items": len(items),
        "index_total": len(idx),
        "used_src_keys": len([s for s, h in resolved.items() if h in idx]),
        "by_collection": by_col,
        "unused": sorted(missing, key=lambda x: (x["collection"], -x["chars"])),
    }
    with open(os.path.join(SRC, "doc-coverage.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    print("items", len(items), "index", len(idx))
    for col, r in sorted(by_col.items(), key=lambda x: -x[1]["unused"]):
        print(f"{col:16s} total={r['total']:4d} used={r['used']:4d} unused={r['unused']:4d}")
    print("unused total", len(missing))
    for m in report["unused"][:25]:
        print(" -", m["collection"], m["key"], m["chars"], (m["title"] or "")[:60])


if __name__ == "__main__":
    main()
