"""装配器（记账用）：把「我手写的章节树」+ 原文 + 条目 span 合成 toc JSON。

它**不做任何语义判断**：
  - section 的 heading/level/parent/facets/confidence 全部来自手写 spec；
  - 脚本只做三件机械事：
      1) 按页码把合订本切成内嵌文件（页码来自 _toc_<key>.json，是我读目录后手抄的）；
      2) 按 spec 给的 clause_no / anchor 定位每节在原文里的行区间，把该区间原文照抄进 clauses；
      3) 按条目 evidence.answer.span 定位，把落在该节区间的条目填进 entry_ids。

用法：
  python tools/toc_assemble.py --map  _review_items/toc/_toc_att-c86ee325fa.json
  python tools/toc_assemble.py --spec _review_items/toc/_spec_p1.json
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "items.json"
DOCLIST = ROOT / "_review_items" / "toc" / "_doclist.json"
OUTDIR = ROOT / "_review_items" / "toc"

PAGE_RE = re.compile(r"^\s*-\s*(\d+)\s*-\s*$")


def norm(s: str) -> str:
    s = s.replace("\x08", "").replace("\x0c", "").replace("\x0b", "").replace("\u3000", " ")
    return re.sub(r"\s+", "", s)


def clean(s: str) -> str:
    s = s.replace("\x08", "").replace("\x0c", "").replace("\x0b", "")
    return s.strip()


class Book:
    def __init__(self, path: Path):
        self.raw = path.read_text(encoding="utf-8")
        self.lines = self.raw.split("\n")
        # 每行在归一化文本中的起始偏移
        self.norm_pos = []
        self.norm_lines = []
        acc = 0
        for ln in self.lines:
            n = norm(ln)
            self.norm_pos.append(acc)
            self.norm_lines.append(n)
            acc += len(n)
        self.norm_text = "".join(self.norm_lines)
        self.marks = [(i, int(m.group(1))) for i, l in enumerate(self.lines) for m in [PAGE_RE.match(l)] if m]
        # 合订本前 7 页是总目录，页码从 1 重新起算；正文页码 3 起。正文页码只看第 230 行之后。
        self.body_marks = [m for m in self.marks if m[0] > 229]

    def page_start_line(self, page: int) -> int:
        """目录标注第 page 页 → 该页第一行（0-based）。"""
        prev = [i for i, p in self.body_marks if p == page - 1]
        if prev:
            return prev[0] + 1
        first = [i for i, p in self.body_marks if p >= page]
        return first[0] if first else 0

    def page_end_line(self, page: int) -> int:
        cur = [i for i, p in self.body_marks if p == page]
        return cur[0] if cur else len(self.lines) - 1

    def pos_of_line(self, i: int) -> int:
        return self.norm_pos[i]

    def end_pos_of_line(self, i: int) -> int:
        return self.norm_pos[i] + len(self.norm_lines[i])


def load_entries(key: str) -> list[dict]:
    ids = {x["key"]: x for x in json.loads(DOCLIST.read_text(encoding="utf-8"))["docs"]}[key]["ids"]
    want = set(ids)
    items = json.loads(ITEMS.read_text(encoding="utf-8"))["items"]
    out = []
    for it in items:
        if it["id"] not in want:
            continue
        ev = (it.get("evidence") or {}).get("answer") or {}
        out.append({"id": it["id"], "quote": norm(ev.get("quote") or ""), "span": ev.get("span") or [0, 0],
                    "raw_quote": ev.get("quote") or ""})
    return out


def locate(book: Book, entries: list[dict]) -> dict[str, int]:
    """把每个条目定位到归一化文本中的字符位置（以 span 为中心窗口搜索，失败再全局）。"""
    N = book.norm_text
    pos: dict[str, int] = {}
    bad = []
    for e in entries:
        q = e["quote"]
        if not q:
            bad.append(e["id"])
            continue
        s0 = e["span"][0] if isinstance(e["span"], list) and e["span"] else 0
        lo = max(0, s0 - 5000)
        hi = min(len(N), (e["span"][1] if len(e["span"]) > 1 else s0) + 5000)
        cands = []
        p = N.find(q, lo, hi)
        while p >= 0 and len(cands) < 64:
            cands.append(p)
            p = N.find(q, p + 1, hi)
        if not cands:
            p = N.find(q)
        else:
            p = min(cands, key=lambda x: abs(x - s0))
        if p < 0:
            bad.append(e["id"])
        else:
            pos[e["id"]] = p
    if bad:
        print(f"⚠️  {len(bad)} 个条目无法在原文定位：{bad[:8]}")
    return pos


def doc_slices(book: Book, toc: dict) -> list[dict]:
    docs = sorted(toc["docs"], key=lambda d: (d["page"], d["seq"]))
    out = []
    for i, d in enumerate(docs):
        start = book.page_start_line(d["page"])
        end = (book.page_start_line(docs[i + 1]["page"]) - 1) if i + 1 < len(docs) else len(book.lines) - 1
        # 内嵌文件结尾常带页脚页码行，交给 clean 丢掉
        out.append({**d, "start_line": start, "end_line": end})
    return out


def section_range(book: Book, spec_sections: list[dict], s: int, e: int, key: str) -> list[int]:
    """按 clause_no / anchor 在 [s,e] 行内顺序定位每节起始行。"""
    cursor = s
    starts = []
    for sec in spec_sections:
        cno = norm(sec.get("clause_no") or "")
        anchor = norm(sec.get("anchor") or "")
        pat = cno or anchor
        found = None
        if pat:
            for i in range(cursor, e + 1):
                n = book.norm_lines[i]
                if not n:
                    continue
                if cno and n.startswith(cno):
                    found = i
                    break
                if anchor and not cno and pat in n:
                    found = i
                    break
        if found is None:
            print(f"❌ {key} 「{sec.get('heading')}」定位失败（clause_no={sec.get('clause_no')!r} anchor={sec.get('anchor')!r}）")
            starts.append(None)
            continue
        starts.append(found)
        cursor = found + 1
    return starts


TITLEISH = re.compile(r"^(附件\s*\d*[:：]?|第[一二三四五六七八九十]+部分|\S*〔\d{4}〕\d*号?|（\d{4}年.*）|\(\d{4}年.*\))$")


def is_front_matter(line: str, title_n: str) -> bool:
    t = clean(line)
    if not t:
        return True
    n = norm(t)
    if PAGE_RE.match(t):
        return True
    if TITLEISH.match(n):
        return True
    if title_n and (n in title_n or title_n in n) and len(n) <= len(title_n) + 10:
        return True
    if len(n) <= 12 and not re.search(r"[，。；：、]", n):
        return True  # 部分名、栏目名这类短行
    return False


def is_back_matter(line: str) -> bool:
    t = clean(line)
    if not t:
        return True
    n = norm(t)
    if PAGE_RE.match(t):
        return True
    if re.match(r"^[（(]\d{4}年.*[）)]$", n):
        return True
    return False


def split_clauses(text: str) -> list[str]:
    """把一段原文拆成 clause：优先按「第X条」切，其次按句号每 2~3 句一段。"""
    t = text.strip()
    if not t:
        return []
    parts = re.split(r"(?=第[一二三四五六七八九十百零〇\d]+条)", t)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        merged = []
        for part in parts:
            if merged and re.fullmatch(r"第[一二三四五六七八九十百零〇\d]+条[、，]?", merged[-1]):
                merged[-1] = merged[-1] + part
            else:
                merged.append(part)
        return merged
    # 「一、二、」式列举：在句末标点后切
    parts = re.split(r"(?<=[。；：])(?=[一二三四五六七八九十]{1,3}、)", t)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        return parts
    # 「（一）（二）」式列举
    parts = re.split(r"(?=（[一二三四五六七八九十]{1,3}）)", t)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        return parts
    # 无条号：按句号聚合，避免一条 clause 过长
    sents = re.findall(r"[^。！？]*[。！？]|[^。！？]+$", t)
    sents = [x.strip() for x in sents if x.strip()]
    out, buf = [], ""
    for x in sents:
        buf += x
        if len(buf) >= 120:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out or [t]


def build_doc_sections(book: Book, spec: dict, sl: dict, pos: dict[str, int], entries_ids: set[str]) -> tuple[list[dict], list[dict]]:
    s, e = sl["start_line"], sl["end_line"]
    key = sl["seq"]
    secs = spec["sections"]
    starts = section_range(book, secs, s, e, f"seq{key}")
    file_doc_id = spec["doc_id"]
    out = []
    for idx, sec in enumerate(secs):
        st = starts[idx]
        if st is None:
            continue
        if sec.get("from_doc_start"):
            st = s
        nxt = next((x for x in starts[idx + 1:] if x is not None), e + 1)
        if sec.get("to_doc_end"):
            nxt = e + 1
        body_lines = [book.lines[i] for i in range(st, nxt)]
        keep_from = st
        if sec.get("from_doc_start") and not sec.get("keep_front_matter"):
            title_n = norm(spec.get("title") or "")
            while body_lines and is_front_matter(body_lines[0], title_n):
                body_lines.pop(0)
                keep_from += 1
        if sec.get("to_doc_end"):
            while body_lines and is_back_matter(body_lines[-1]):
                body_lines.pop()
        # 先丢掉「第六章　撤销学位」「一、社团评价」这类纯标题行：它会把后面的
        # 「第X条」「（一）」切分打断，导致整节只剩 1 段 clause
        cno0 = norm(sec.get("clause_no") or "")
        if cno0:
            for i, ln in enumerate(body_lines):
                c0 = clean(ln)
                if not c0:
                    continue
                if norm(c0).startswith(cno0) and len(c0) <= 20:
                    body_lines.pop(i)
                break
        raw = "\n".join(body_lines)
        # 丢掉页码行
        raw = "\n".join(x for x in raw.split("\n") if not PAGE_RE.match(x))
        joined = ""
        for ln in raw.split("\n"):
            c = clean(ln)
            if not c:
                continue
            joined += c
        clauses = split_clauses(joined)
        if sec.get("clause_mode") == "line":
            # 表格型小节：表头（含「序号」的行）之前是散文，合成 1 条；
            # 自表头起每行各成 1 条（原文照抄，不做语义合并）
            prose, rows, in_table = [], [], False
            for ln in raw.split("\n"):
                c = clean(ln)
                if not c:
                    continue
                if not in_table and "序号" in c:
                    in_table = True
                (rows if in_table else prose).append(c)
            clauses = [("".join(prose) if prose else "")] + rows
            clauses = [c for c in clauses if c]
        cno = norm(sec.get("clause_no") or "")
        if clauses and len(clauses[0]) <= 12 and "。" not in clauses[0] and                 re.match(r"^(第[一二三四五六七八九十]+[章节]|[一二三四五六七八九十]{1,3}、)", clauses[0]):
            clauses = clauses[1:]  # 丢掉「第一章　总则」「六、附则」这类纯标记行（无正文）
        p0 = book.pos_of_line(keep_from)
        p1 = book.pos_of_line(nxt) if nxt <= e else book.end_pos_of_line(e)
        ids = sorted([eid for eid, p in pos.items() if p0 <= p < p1 and eid in entries_ids])
        out.append({
            "section_id": f"{file_doc_id}#s{idx+1:02d}",
            "heading": sec["heading"],
            "heading_kind": sec.get("heading_kind", "derived"),
            "clause_no": sec.get("clause_no", ""),
            "level": sec.get("level", 2),
            "parent": sec.get("parent", ""),
            "order": len(out) + 1,
            "scope": sec.get("scope", ""),
            "facets": sec.get("facets", []),
            "entry_ids": ids,
            "clauses": [{"i": j + 1, "text": t} for j, t in enumerate(clauses)],
            "confidence": sec.get("confidence", "high"),
            "note": sec.get("note", ""),
        })
        if sec.get("merged_chapters"):
            out[-1]["merged_chapters"] = sec["merged_chapters"]
    covered = {x for sec in out for x in sec["entry_ids"]}
    first_start = book.pos_of_line(s)
    last_end = book.end_pos_of_line(e)
    leftovers = sorted([eid for eid, p in pos.items() if first_start <= p < last_end and eid in entries_ids and eid not in covered])
    return out, leftovers


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", dest="mapfile")
    ap.add_argument("--spec", dest="specfile")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    if a.mapfile:
        toc = json.loads(Path(a.mapfile).read_text(encoding="utf-8"))
        book = Book(ROOT / toc["outer"]["text"])
        entries = load_entries(toc["outer"]["key"])
        pos = locate(book, entries)
        slices = doc_slices(book, toc)
        print(f"{'seq':>3} {'page':>4} {'lines':>12} {'chars':>7} {'entries':>7}  title")
        total = 0
        for sl in slices:
            s, e = sl["start_line"], sl["end_line"]
            chars = sum(len(norm(x)) for x in book.lines[s:e + 1])
            n = sum(1 for p in pos.values() if book.pos_of_line(s) <= p <= book.end_pos_of_line(e))
            total += n
            head = next((clean(x) for x in book.lines[s:s + 4] if clean(x)), "")
            print(f"{sl['seq']:>3} {sl['page']:>4} {s+1:>5}-{e+1:<6} {chars:>7} {n:>7}  {head[:40]}")
        print("entries in slices:", total, "/", len(entries))
        # 目录页碎片
        toc_entries = [e for e in entries if e["id"] in pos and pos[e["id"]] < book.pos_of_line(slices[0]["start_line"])]
        print("目录/前置页碎片：", len(toc_entries))
        return

    toc = json.loads((OUTDIR / "_toc_att-c86ee325fa.json").read_text(encoding="utf-8"))
    book = Book(ROOT / toc["outer"]["text"])
    entries = load_entries(toc["outer"]["key"])
    pos = locate(book, entries)
    all_ids = {x["id"] for x in entries}
    slices = {x["seq"]: x for x in doc_slices(book, toc)}
    toc_by_seq = {x["seq"]: x for x in toc["docs"]}
    spec = json.loads(Path(a.specfile).read_text(encoding="utf-8"))
    for d in spec["docs"]:
        sl = dict(slices.get(d["seq"], {"seq": d["seq"], "start_line": 0, "end_line": len(book.lines)-1}))
        if d.get("lines"):  # 手读后标定的行区间优先（1-based，闭区间）
            sl["start_line"], sl["end_line"] = d["lines"][0] - 1, d["lines"][1] - 1
        sections, leftovers = build_doc_sections(book, d, sl, pos, all_ids)
        total = sum(1 for p in pos.values() if book.pos_of_line(sl["start_line"]) <= p <= book.end_pos_of_line(sl["end_line"]))
        qmap = {x["id"]: x["quote"] for x in entries}
        tq = norm(d.get("title") or "")
        unassigned = []
        for eid in leftovers + [x["entry_id"] for x in d.get("extra_unassigned", [])]:
            hint = next((x["why"] for x in d.get("extra_unassigned", []) if x["entry_id"] == eid), None)
            if hint:
                unassigned.append({"entry_id": eid, "why": hint, "suggest": ""})
                continue
            q = qmap.get(eid, "")
            if tq and tq[:6] and tq[:6] in q:
                why = "文档大标题/文号行片段（标题本身不是正文条款）"
            elif re.search(r"^-\d+-$", q) or not q:
                why = "页码等页面元素片段"
            else:
                why = "该片段位于本文件页面间隙（页眉/标题行/装订分隔），无对应正文条款"
            unassigned.append({"entry_id": eid, "why": why, "suggest": ""})
        nav = sum(len(s["entry_ids"]) for s in sections)
        meta = toc_by_seq.get(d["seq"], {})
        doc = {
            "doc_id": d["doc_id"],
            "key": toc["outer"]["key"],
            "title": d.get("title") or meta.get("title", ""),
            "number": d.get("number") or meta.get("number", ""),
            "issuer": d.get("issuer") or meta.get("issuer", ""),
            "date": d.get("date") or meta.get("date", ""),
            "audience": d.get("audience", ["本科生", "研究生"]),
            "text_path": toc["outer"]["text"],
            "title_kind": d.get("title_kind", "author"),
            "parent_hb": toc["outer"]["key"],
            "partial": True,
        }
        out = {"doc": doc, "sections": sections, "unassigned": unassigned,
               "stats": {"entries_total": nav + len(unassigned), "entries_assigned": nav,
                         "entries_unassigned": len(unassigned), "sections": len(sections),
                         "by_kind": {"author": sum(1 for s in sections if s["heading_kind"] == "author"),
                                     "derived": sum(1 for s in sections if s["heading_kind"] == "derived")}}}
        fp = OUTDIR / d["file"]
        empty = [x["section_id"] + "/" + x["heading"] for x in sections if not x["entry_ids"]]
        warn = f"  ❗空节{len(empty)}: {empty[:4]}" if empty else ""
        print(f"{d['file']:<36} sections={len(sections):>2} assigned={nav:>3} unassigned={len(unassigned):>3} / total={total:>3}{warn}")
        if a.write:
            fp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
