"""小实验：结构清晰的长文档走树形导航，强制读叶子原文，最后照样逐字校验。

适用面（只在这些文档上做，新闻类不碰）：
  kb 里 kind='规章正文' 且原文 ≥8000 字、且文内确有「第X章／第X条／一、」这类章节层的文档。
  典型就是制度汇编、学生手册、新生指南——答案位置由章节标题决定，扁平检索只能撞到切片。

一条问句的做法：
  1. 候选文档：现行规则腿 top30 条目所属文档里，落在上述集合的（最多 2 份）。
  2. 章导航：只给章节目录，模型选最多 2 章；选不出就弃权。
  3. 叶子导航：给出选中章下的「条」标题＋前 50 字，模型选一条叶子。
  4. 最终校验：把叶子原文整条给模型，只有它 accept 并逐字摘出原文句子才算答上；
     引文必须是叶子原文的子串且 ≥6 字，否则按 quote_missing 丢掉。
  5. 落回条目 id：叶子覆盖了哪些条目——按该文档条目的引文文本被叶子包含的长度计分，取最高一条。

计分口径与现行尺子一致（expect 命中表）。同时报两栏：
  独立看：树这一腿自己有多少题能 accept、accept 里命中率多高；
  叠加看：只在本档基线（P6/P6b）答错或拒答的题上接管，答对的题不动。
"""
from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_review_items"))

import app  # noqa: E402

BS = chr(92)
OUT = ROOT / "_review_items" / "tree_nav_rows.jsonl"
MIN_DOC_CHARS = 8000
MIN_HEADINGS = 10
MAX_DOCS = 2
LEAF_PREVIEW = 50
LEAF_MAX_CHARS = 1400
QUOTE_MIN = 6

RE_CHAPTER = re.compile(r"^\s*(第[一二三四五六七八九十百零〇\d]+章.{0,40})$", re.M)
RE_ARTICLE = re.compile(r"^\s*(第[一二三四五六七八九十百零〇\d]+条.{0,60})$", re.M)
RE_CN_SEC = re.compile(r"^\s*([一二三四五六七八九十]{1,3}、.{0,40})$", re.M)

_lock = threading.Lock()
_tree_cache: dict[str, list[dict]] = {}
_quotes_cache: dict[str, dict[str, list[str]]] = {}
_item_doc: dict[str, str] = {}


def item_doc_map() -> dict[str, str]:
    """items.json 里没有 doc 字段，条目属于哪份原文只能从 kb 的 item 表取。

    必须整体建完再交出去：多线程各自边读边返回会拿到半截表（第一次全量跑就
    因此把 67 题可导航误判成 2 题）。
    """
    if _item_doc:
        return _item_doc
    with _lock:
        if _item_doc:
            return _item_doc
        tmp: dict[str, str] = {}
        c = kb()
        for iid, doc in c.execute("select id, doc from item"):
            tmp[str(iid)] = str(doc or "")
        c.close()
        _item_doc.update(tmp)
    return _item_doc


def clean_text(text: str) -> str:
    """与入库时的清洗一致（tools/build_vector.py:79），否则逐字校验对不上。"""
    t = (text or "").replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw in t.splitlines():
        s = raw.strip()
        if not s:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if re.fullmatch(r"[-—–\s]*\d{1,4}[-—–\s]*", s):
            continue
        if s in {"首页", "上一篇", "下一篇", "返回", "关闭"}:
            continue
        lines.append(s)
    t = "\n".join(lines)
    t = re.sub(r"[ \t　]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def kb():
    return sqlite3.connect(f"file:{ROOT / 'kb.sqlite'}?mode=ro", uri=True)


def structural_docs() -> dict[str, dict]:
    c = kb()
    out = {}
    for key, file, chars, title in c.execute(
            "select key,file,chars,title from doc where kind='规章正文' and chars>=?", (MIN_DOC_CHARS,)):
        p = ROOT / "sources" / str(file).replace(BS, "/")
        if not p.exists():
            continue
        raw = clean_text(p.read_text(encoding="utf-8", errors="ignore"))
        n = (len(RE_CHAPTER.findall(raw)) + len(RE_ARTICLE.findall(raw)) + len(RE_CN_SEC.findall(raw)))
        if n >= MIN_HEADINGS:
            out[key] = {"path": p, "chars": chars, "title": title, "heads": n, "text": raw}
    c.close()
    return out


def build_tree(key: str, docs: dict[str, dict]) -> list[dict]:
    """两级树：章（或「一、」）为节点，条（或章内段落）为叶子。"""
    if key in _tree_cache:
        return _tree_cache[key]
    text = docs[key]["text"]
    marks = []
    for m in RE_CHAPTER.finditer(text):
        marks.append((m.start(), "章", m.group(1)))
    for m in RE_CN_SEC.finditer(text):
        marks.append((m.start(), "节", m.group(1)))
    for m in RE_ARTICLE.finditer(text):
        marks.append((m.start(), "条", m.group(1)))
    marks.sort()
    chapters: list[dict] = []
    for i, (pos, kind, title) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        if kind == "条":
            if chapters and chapters[-1]["open"]:
                chapters[-1]["leaves"].append({"title": title, "start": pos, "end": end})
                chapters[-1]["end"] = end
                continue
            chapters.append({"title": title, "kind": kind, "start": pos, "end": end, "leaves": [], "open": False})
            continue
        chapters.append({"title": title, "kind": kind, "start": pos, "end": end, "leaves": [], "open": True})
    tree = [ch for ch in chapters if ch["end"] - ch["start"] >= 20]
    _tree_cache[key] = tree
    return tree


def item_quotes(key: str) -> dict[str, list[str]]:
    if key in _quotes_cache:
        return _quotes_cache[key]
    c = kb()
    out: dict[str, list[str]] = {}
    for item_id, text in c.execute(
            "select q.item_id, q.text from quote q join item i on i.id=q.item_id where i.doc=?", (key,)):
        t = (text or "").strip()
        if len(t) >= 10:
            out.setdefault(item_id, []).append(t)
    c.close()
    _quotes_cache[key] = out
    return out


def leaf_to_item(key: str, leaf: str) -> tuple[str | None, int]:
    best, score = None, 0
    for item_id, quotes in item_quotes(key).items():
        s = sum(len(q) for q in quotes if q in leaf)
        if s > score:
            best, score = item_id, s
    return best, score


def chat(prompt: str, user: str, max_tokens: int = 320) -> dict:
    raw = app.ds_chat([{"role": "system", "content": prompt},
                      {"role": "user", "content": user}], max_tokens=max_tokens, json_mode=True)
    data = json.loads(raw) or {}
    return data if isinstance(data, dict) else {}


def _bigrams(s: str) -> set[str]:
    s = "".join(str(s).split())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def pick_chapters(q: str, doc: dict, tree: list[dict]) -> list[int]:
    """导航不等于全表喂进去：先用二字重合粗筛到 40 行，再由模型定夺。"""
    qb = _bigrams(q)
    scored = sorted(
        ((len(qb & _bigrams(ch["title"])) + (1 if ch["leaves"] else 0), i)
         for i, ch in enumerate(tree)),
        reverse=True)
    keep = [i for _s, i in scored[:40]]
    menu = "\n".join(f"{j + 1}. {tree[i]['title']}" for j, i in enumerate(keep))
    prompt = (
        "用户在问校园里的一件事。下面是一份学校文件的章节目录。\n"
        "只选出最可能写着这件事答案的章节，最多 2 个；标题都对不上的就别选，宁可返回空。\n"
        "不要为了有答案而硬选。\n"
    )
    user = f"文件名：{doc['title']}\n问句：{q}\n\n目录：\n{menu}\n\n只输出 JSON：{{\"chapters\": [序号]}}"
    try:
        got = chat(prompt, user, 160).get("chapters") or []
        out = []
        for x in got:
            if str(x).strip().isdigit() and 0 < int(x) <= len(keep):
                out.append(keep[int(x) - 1])
        return out[:2]
    except Exception:  # noqa: BLE001
        return []


def pick_leaf(q: str, doc: dict, tree: list[dict], chosen: list[int]) -> tuple[int, int] | None:
    rows = []
    for ci in chosen:
        ch = tree[ci]
        leaves = ch["leaves"] or [ch]
        for li, lf in enumerate(leaves[:80]):
            body = doc["text"][lf["start"]:lf["start"] + LEAF_PREVIEW].replace("\n", " ")
            rows.append({"ci": ci, "li": li, "line": f"{ch['title']} › {lf['title']}｜{body}"})
    if not rows:
        return None
    menu = "\n".join(f"{i + 1}. {r['line']}" for i, r in enumerate(rows))
    prompt = (
        "同一份文件，下面是在已选章节里的条目清单（只有标题和开头几字）。\n"
        "选出最可能写着答案的一条，只选 1 条；都对不上就返回 null。\n"
    )
    user = f"问句：{q}\n\n清单：\n{menu}\n\n只输出 JSON：{{\"leaf\": 序号或null}}"
    try:
        n = chat(prompt, user, 120).get("leaf")
        if n is None or not str(n).strip().isdigit():
            return None
        i = int(n) - 1
        return (rows[i]["ci"], rows[i]["li"]) if 0 <= i < len(rows) else None
    except Exception:  # noqa: BLE001
        return None


def final_check(q: str, leaf_text: str) -> dict:
    prompt = (
        "下面是从学校文件里定位到的一条原文。只判断它有没有答上用户问的这件事。\n"
        "答上了就给 accept，并从这条原文里逐字摘出能回答的那句：一字不差，不许改写、不许拼接、不许加标点。\n"
        "只沾边、讲的是别的部门别的考试别的材料、或者只给了个入口网址没有做法，一律 reject。\n"
    )
    user = f"问句：{q}\n\n原文：\n{leaf_text[:LEAF_MAX_CHARS]}\n\n" + \
        '只输出 JSON：{"verdict": "accept|reject", "quote": "逐字原文", "why": "一句话理由"}'
    try:
        d = chat(prompt, user, 320)
    except Exception as e:  # noqa: BLE001
        return {"gate": "error", "why": app._llm_err_text(e)}
    verdict = str(d.get("verdict") or "").strip().lower()
    quote = str(d.get("quote") or "").strip()
    if verdict != "accept":
        return {"gate": "reject", "why": str(d.get("why") or "")[:120]}
    if len(quote) < QUOTE_MIN or quote not in leaf_text:
        return {"gate": "quote_missing", "quote": quote[:80], "why": str(d.get("why") or "")[:120]}
    return {"gate": "accept", "quote": quote, "why": str(d.get("why") or "")[:120]}


def one(q: str, expect: set[str], docs: dict[str, dict]) -> dict:
    t0 = time.time()
    calls = 0
    ranked = app.rank(q)[:30]
    id2doc = item_doc_map()
    per_doc: dict[str, int] = {}
    for it, _sc in ranked:
        key = id2doc.get(it["id"], "")
        if key in docs:
            per_doc[key] = per_doc.get(key, 0) + 1
    cand = sorted(per_doc.items(), key=lambda kv: -kv[1])[:MAX_DOCS]
    out = {"q": q, "eligible": len(cand), "cand": [k for k, _n in cand], "hit": False,
           "accepted": False, "gate": "no_struct_doc", "tries": []}
    for key, _n in cand:
        tree = build_tree(key, docs)
        with _lock:
            calls += 1
        chosen = pick_chapters(q, docs[key], tree)
        calls += 1
        if not chosen:
            out["tries"].append({"doc": key, "gate": "no_chapter"})
            continue
        pick = pick_leaf(q, docs[key], tree, chosen)
        calls += 1
        if pick is None:
            out["tries"].append({"doc": key, "gate": "no_leaf", "chapters": chosen})
            continue
        ci, li = pick
        ch = tree[ci]
        leaves = ch["leaves"] or [ch]
        lf = leaves[li]
        leaf_text = docs[key]["text"][lf["start"]:min(lf["end"], lf["start"] + LEAF_MAX_CHARS)]
        res = final_check(q, leaf_text)
        calls += 1
        got, overlap = (leaf_to_item(key, leaf_text) if res["gate"] == "accept" else (None, 0))
        out["tries"].append({"doc": key, "chapter": ch["title"][:40], "leaf": lf["title"][:40],
                             "leaf_chars": len(leaf_text), **res, "got": got, "overlap": overlap})
        if res["gate"] == "accept":
            out["accepted"] = True
            out["gate"] = "accept"
            out["got"] = got
            out["hit"] = bool(got) and got in expect
            break
    if not out["accepted"]:
        seen = [t.get("gate") for t in out["tries"]]
        for g in ("quote_missing", "reject", "no_leaf", "no_chapter"):
            if g in seen:
                out["gate"] = g
                break
    out["calls"] = calls
    out["ms"] = round((time.time() - t0) * 1000)
    return out


def main() -> int:
    import balance_probe as bp
    qs = bp.questions()
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        docs = structural_docs()
        print(f"结构清晰的长文档 {len(docs)} 份（≥{MIN_DOC_CHARS} 字且章节标题≥{MIN_HEADINGS}）")
        for k, v in sorted(docs.items(), key=lambda kv: -kv[1]["heads"])[:15]:
            print(f"  {k[:26]:<28} 字数={v['chars']:>7} 标题行={v['heads']:>5} 「{str(v['title'])[:28]}」")
        n_elig = 0
        id2doc = item_doc_map()
        for rec in qs:
            keys = {id2doc.get(it["id"], "") for it, _ in app.rank(rec["q"])[:30]} & set(docs)
            n_elig += bool(keys)
        print(f"100 题里规则腿 top30 落到这些文档的：{n_elig} 题")
        return 0

    docs = structural_docs()
    item_doc_map()   # 建表要在起线程之前，见函数里的注释
    print(f"结构文档 {len(docs)} 份，跑 {len(qs)} 题")
    rows = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = [pool.submit(one, r["q"], set(r["expect"]), docs) for r in qs]
        for i, f in enumerate(futs, 1):
            rows.append(f.result())
            if i % 20 == 0:
                print(f"   {i}/{len(qs)}")
    with io.open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    base: dict[str, dict[str, dict]] = {"P6": {}, "P6b": {}}
    for line in io.open(ROOT / "_review_items" / "balance_rows.jsonl", encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            if d["cfg"] in base:
                base[d["cfg"]][d["q"]] = d
    acc = [r for r in rows if r["accepted"]]
    good = [r for r in acc if r["hit"]]
    print(f"\n== 独立看这一腿：可导航 {sum(1 for r in rows if r['eligible'])} "
          f"| 走到 accept {len(acc)} | accept 里命中期望条目 {len(good)} "
          f"({(len(good) / len(acc) * 100) if acc else 0:.1f}%)")
    gates: dict[str, int] = {}
    for r in rows:
        gates[r["gate"]] = gates.get(r["gate"], 0) + 1
    print("   终止状态分布:", json.dumps(gates, ensure_ascii=False))
    print(f"   每题调用 中位{sorted(r['calls'] for r in rows)[len(rows) // 2]} 次，"
          f"这一腿自身中位耗时 {sorted(r['ms'] for r in rows)[len(rows) // 2] / 1000:.1f}s")

    def tier_of(d: dict) -> str:
        return "对" if d.get("hit") else ("错" if d.get("matched") else "拒")

    def new_tier(bt: str, r: dict, policy: str) -> str:
        if r["accepted"]:
            return "对" if r["hit"] else "错"
        return bt if policy == "conservative" else ("拒" if policy == "override" else bt)

    for cfg in ("P6", "P6b"):
        bmap = base[cfg]
        print(f"\n== 叠加在 {cfg} 上（{len(bmap)} 题）")
        for policy, label in (("conservative", "只在答错/拒答时接管"), ("override", "答对与否都由树裁决")):
            cnt = {"对": 0, "错": 0, "拒": 0}
            fixed: list[str] = []
            broke: list[str] = []
            for r in rows:
                bd = bmap.get(r["q"])
                if bd is None:
                    continue
                bt, nt = tier_of(bd), new_tier(tier_of(bd), r, policy)
                cnt[nt] += 1
                if bt != nt:
                    (fixed if nt == "对" else broke).append(r["q"])
            print(f"   {label}：对{cnt['对']} 错{cnt['错']} 拒{cnt['拒']} "
                  f"效用 {cnt['对'] - 3 * cnt['错']}（原 "
                  f"{sum(1 for d in bmap.values() if tier_of(d) == '对') - 3 * sum(1 for d in bmap.values() if tier_of(d) == '错')}）"
                  f" | 救回 {len(fixed)} 弄坏 {len(broke)}")
            if fixed:
                print(f"      救回：{[x[:22] for x in fixed]}")
            if broke:
                print(f"      弄坏：{[x[:22] for x in broke]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
