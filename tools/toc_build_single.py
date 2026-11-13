"""单份文档装配器（非汇编）：把「我手写的章节树」+ 原文 + 条目 span 合成 toc JSON。

与 toc_assemble.py 同源，区别是：
  - 直接读 spec 里的 key / text / doc 元数据，不再依赖合订本页码表；
  - 每节用 `lines: [起, 止]`（1-based，闭区间）标定在原文中的行区间，或给 clause_no/anchor 自动定位；
  - 条目按 `evidence.answer.span` 定位，落在哪节区间就挂哪节，其余进 unassigned。

用法：
  python tools/toc_build_single.py _review_items/toc/_spec_2021-07-15-e3ef7aaa.json --write
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "items.json"
DOCLIST = ROOT / "_review_items" / "toc" / "_doclist.json"
PAGE_RE = re.compile(r"^\s*-\s*(\d+)\s*-\s*$")


def norm(s: str) -> str:
    s = s.replace("\x08", "").replace("\x0c", "").replace("\x0b", "").replace("\u3000", " ")
    return re.sub(r"\s+", "", s)


def clean(s: str) -> str:
    return s.replace("\x08", "").replace("\x0c", "").replace("\x0b", "").strip()


class Text:
    def __init__(self, path: Path):
        self.lines = path.read_text(encoding="utf-8").split("\n")
        self.npos, acc = [], 0
        self.norm = []
        for ln in self.lines:
            n = norm(ln)
            self.npos.append(acc)
            self.norm.append(n)
            acc += len(n)
        self.text = "".join(self.norm)

    def pos(self, i: int) -> int:
        return self.npos[i]

    def end(self, i: int) -> int:
        return self.npos[i] + len(self.norm[i])


def locate(t: Text, entries):
    pos, bad = {}, []
    N = t.text
    for e in entries:
        q = e["quote"]
        if not q:
            bad.append(e["id"])
            continue
        s0 = e["span"][0] if e["span"] else 0
        lo, hi = max(0, s0 - 5000), min(len(N), (e["span"][1] if len(e["span"]) > 1 else s0) + 5000)
        cands, p = [], N.find(q, lo, hi)
        while p >= 0 and len(cands) < 64:
            cands.append(p)
            p = N.find(q, p + 1, hi)
        p = min(cands, key=lambda x: abs(x - s0)) if cands else N.find(q)
        if p < 0:
            bad.append(e["id"])
        else:
            pos[e["id"]] = p
    if bad:
        print(f"⚠️  {len(bad)} 个条目无法定位：{bad[:6]}")
    return pos


def split_clauses(text: str):
    t = text.strip()
    if not t:
        return []
    parts = re.split(r"(?=第[一二三四五六七八九十百零〇\d]+条)", t)
    parts = [x.strip() for x in parts if x.strip()]
    if len(parts) >= 2:
        return parts
    parts = re.split(r"(?<=[。；：])(?=[一二三四五六七八九十]{1,3}、)", t)
    parts = [x.strip() for x in parts if x.strip()]
    if len(parts) >= 2:
        return parts
    parts = re.split(r"(?=（[一二三四五六七八九十]{1,3}）)", t)
    parts = [x.strip() for x in parts if x.strip()]
    if len(parts) >= 2:
        return parts
    sents = [x.strip() for x in re.findall(r"[^。！？]*[。！？]|[^。！？]+$", t) if x.strip()]
    out, buf = [], ""
    for x in sents:
        buf += x
        if len(buf) >= 120:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out or [t]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    raw = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    specs = raw["docs"] if isinstance(raw, dict) and "docs" in raw else [raw]
    for spec in specs:
        build_one(spec, a.write)
    return


def build_one(spec, write):
    key = spec["key"]
    docs = {x["key"]: x for x in json.loads(DOCLIST.read_text(encoding="utf-8"))["docs"]}
    want = set(docs[key]["ids"])
    items = json.loads(ITEMS.read_text(encoding="utf-8"))["items"]
    entries = []
    for it in items:
        if it["id"] not in want:
            continue
        ev = (it.get("evidence") or {}).get("answer") or {}
        entries.append({"id": it["id"], "quote": norm(ev.get("quote") or ""), "span": ev.get("span") or [0, 0]})
    t = Text(ROOT / spec["text"])
    pos = locate(t, entries)
    ids_all = {x["id"] for x in entries}

    sections, covered = [], set()
    for idx, sec in enumerate(spec["sections"]):
        if sec.get("lines"):
            s, e = sec["lines"][0] - 1, sec["lines"][1] - 1
        else:
            print(f"❌ 第 {idx+1} 节「{sec.get('heading')}」缺 lines")
            continue
        body = [clean(t.lines[i]) for i in range(s, e + 1)]
        body = [x for x in body if x and not PAGE_RE.match(x)]
        if sec.get("clause_mode") == "record":
            n = int(sec.get("clause_group", 5))
            clauses = ["".join(body[i:i + n]) for i in range(0, len(body), n)]
        elif sec.get("clause_mode") == "until":
            # 表格记录：累积若干行，遇到结束标记行（如「大会报告」）即收一条
            marks = set(sec.get("clause_until") or [])
            clauses, buf = [], ""
            for ln in body:
                buf += ln
                if ln in marks:
                    clauses.append(buf)
                    buf = ""
            if buf:
                clauses.append(buf)
        elif sec.get("clause_mode") == "numbered":
            # 编号清单：遇到「1.」「（一）」这类编号行就起新的一条，续行并回上一条
            clauses, buf = [], ""
            pat = re.compile(r"^(\d+[.．、]|[（(][一二三四五六七八九十]{1,3}[)）]|[一二三四五六七八九十]{1,3}、)")
            for ln in body:
                if pat.match(ln) and buf:
                    clauses.append(buf)
                    buf = ln
                else:
                    buf += ln
            if buf:
                clauses.append(buf)
        elif sec.get("clause_mode") == "line":
            clauses = body
            cno1 = norm(sec.get("clause_no") or "")
            if cno1 and clauses and norm(clauses[0]) == cno1:
                clauses = clauses[1:]  # 去掉「附1」这类附件号行
        else:
            cno0 = norm(sec.get("clause_no") or "")
            if cno0 and body and norm(body[0]).startswith(cno0) and ("。" not in body[0]) and len(body[0]) <= 40:
                body = body[1:]
            clauses = split_clauses("".join(body))
        p0, p1 = t.pos(s), t.end(e)
        forced = {x["entry_id"] for x in spec.get("force_unassigned", [])}
        ids = sorted([eid for eid, p in pos.items()
                      if p0 <= p < p1 and eid in ids_all and eid not in covered and eid not in forced])
        covered |= set(ids)
        sec_out = {
            "section_id": f"{spec['doc_id']}#s{idx+1:02d}",
            "heading": sec["heading"],
            "heading_kind": sec.get("heading_kind", "derived"),
            "clause_no": sec.get("clause_no", ""),
            "level": sec.get("level", 2),
            "parent": sec.get("parent", ""),
            "order": idx + 1,
            "scope": sec.get("scope", ""),
            "facets": sec.get("facets", []),
            "entry_ids": ids,
            "clauses": [{"i": j + 1, "text": x} for j, x in enumerate(clauses)],
            "confidence": sec.get("confidence", "high"),
            "note": sec.get("note", ""),
        }
        if sec.get("merged_chapters"):
            sec_out["merged_chapters"] = sec["merged_chapters"]
        if sec.get("placeholder"):
            sec_out["placeholder"] = True
        if spec.get("auto_placeholder") and not ids and not sec.get("placeholder"):
            sec_out["placeholder"] = True
            sec_out["note"] = (sec_out["note"] + "；" if sec_out["note"] else "") + "原文有本节、库中 0 个碎片条目，保留结构不挂条目"
        sections.append(sec_out)

    # 同一 key 拆成多份文件时，每份只认「自己行区间内」的条目，避免把别的分片条目算成未归属
    if spec.get("range"):
        lo, hi = spec["range"][0] - 1, spec["range"][1] - 1
    else:
        spans = [(sec["lines"][0] - 1, sec["lines"][1] - 1) for sec in spec["sections"] if sec.get("lines")]
        lo = min(a for a, b in spans)
        hi = max(b for a, b in spans)
    here = {e for e, p in pos.items() if t.pos(lo) <= p < t.end(hi)}
    # 无法按位置定位的条目（如 rule-* 全篇摘要）：spec 指定挂到某节
    for fa in spec.get("force_assign", []):
        idx = int(fa["to"].split("#s")[-1]) - 1
        eid = fa["entry_id"]
        if eid in ids_all and eid not in covered and 0 <= idx < len(sections):
            sections[idx]["entry_ids"].append(eid)
            sections[idx]["note"] = (sections[idx]["note"] + "；" if sections[idx]["note"] else "") + fa.get("why", "")
            covered.add(eid)
    forced_ids = {x["entry_id"] for x in spec.get("force_unassigned", [])}
    un = [{"entry_id": e, "why": spec.get("unassigned_why", "位于页面间隙/页眉标题行，无对应正文条款"), "suggest": ""}
          for e in sorted(here - covered - forced_ids)]
    for x in spec.get("force_unassigned", []):
        if x["entry_id"] not in covered:
            un.append({"entry_id": x["entry_id"], "why": x["why"], "suggest": ""})
    un.sort(key=lambda u: u["entry_id"])
    doc = {"doc_id": spec["doc_id"], "key": key, "title": spec["title"], "number": spec.get("number", ""),
           "issuer": spec.get("issuer", ""), "date": spec.get("date", ""),
           "audience": spec.get("audience", ["本科生", "研究生"]), "text_path": spec["text"],
           "title_kind": spec.get("title_kind", "author"), "parent_hb": "",
           "partial": bool(spec.get("partial", False))}
    assigned = sum(len(s["entry_ids"]) for s in sections)
    out = {"doc": doc, "sections": sections, "unassigned": un,
           "stats": {"entries_total": assigned + len(un), "entries_assigned": assigned,
                     "entries_unassigned": len(un), "sections": len(sections),
                     "by_kind": {"author": sum(1 for s in sections if s["heading_kind"] == "author"),
                                 "derived": sum(1 for s in sections if s["heading_kind"] == "derived")}}}
    print(f"{spec['file']:<34} sections={len(sections):>2} assigned={assigned:>4} unassigned={len(un):>2} / total={assigned+len(un):>4}")
    empty = [f"{s['section_id']}/{s['heading']}" for s in sections if not s["entry_ids"] and not s.get("placeholder")]
    if empty:
        print("  ❗空节", len(empty), empty[:3])
    if write:
        (ROOT / "_review_items" / "toc" / spec["file"]).write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
